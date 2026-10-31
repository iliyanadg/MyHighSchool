"""M53 native in-game staff management atop M52 Mac-confirmed school menu.

Adds the five nested category+SimData pairs created from a verified M45
Lot51-exported binary. Staff root -> Principal / Teachers / Cafeteria /
Custodians. Every new child SimData requires:
 - FNV1-32 *lowercase category TDesc name* at 0x24 (Lot51 header);
 - _display_name localization key at 0x44;
 - _parent TableSetReference with parent category ID in HIGH 32 bits at 0x5c;
 - one ASCII 20-character category instance name replacement.
Do NOT use raw XML-only categories or old low-32-bit parent references;
both were confirmed to break the hierarchy in early M43 tests.

The ORIGINAL 35 M52 resources remain strictly equal: existing menu, all
registration, withdrawal, transfer & settings code unchanged.
New staff UI is 17 native actions on the staff menu, only existing adults.
No staffing of EA High School Years services until separate integration.
"""
import hashlib
import importlib.util
import json
import py_compile
import struct
import sys
import tempfile
import xml.etree.ElementTree as ET
import zipfile
import zlib
from pathlib import Path

from tooling.build_m52_removal_and_settings import package_bytes as build_m52
from tooling.build_m48_single_checkmark import SCRIPTS as M52_SCRIPTS
from tooling.build_m27_removal import (
    TYPE_INTERACTION,TYPE_SNIPPET,TYPE_STBL,ENTRY,fnv64_highbit)
from tooling.build_m30_nested_menu import CATEGORY_IDS,category_id
from tooling.build_m41_complete_menu import CATEGORY_TYPE,SIMDATA_TYPE,SIMDATA_GROUP
from tooling.build_m43_matched_root import MATCHED_ROOT
from tooling.m1_links_and_strings import parse_stbl
from tooling.simdata_release_gate import inspect_bytes,resources
from tooling.build_m38_three_class_menu import SETTINGS_CATEGORY

ROOT=Path(__file__).resolve().parents[1]
STAFF_STORE=ROOT/'src'/'m53_staff'/'mhs53_staff_store.py'
STAFF_UI=ROOT/'src'/'m53_staff'/'mhs53_staff_ui.py'
SCRIPTS=tuple(M52_SCRIPTS)+(STAFF_STORE,STAFF_UI)
PACKAGE='MHS_M53_PERSONALE_SCOLASTICO_TEST.package'
SCRIPT='MHS_M53_PERSONALE_SCOLASTICO_TEST.ts4script'

# Exactly 20 bytes, matching the verified Lot51 child SimData template.
NAMES=('Iliyana:MHS_Staff___',
       'Iliyana:MHS_Director',
       'Iliyana:MHS_Teachers',
       'Iliyana:MHS_Canteen_',
       'Iliyana:MHS_Janitor_')
CAT_IDS=tuple(category_id(name) for name in NAMES)
CAT_LABELS=tuple(0x5A895000+i for i in range(5))
TEMPLATE_NAME='Iliyana:MHS_Class_1_'
ACTIONS=(
    # command, category, Italian text, English text, exposed class
    ('PrincipalChoose',1,'Scegli / sostituisci preside','Choose / replace principal',1),
    ('PrincipalRemove',1,'Rimuovi preside','Remove principal',1),
    ('PrincipalView',1,'Consulta preside','View principal',1),
    ('Teacher1Choose',2,'Assegna / sostituisci prof. Classe 1','Assign / replace Class 1 teacher',1),
    ('Teacher1Remove',2,'Rimuovi prof. Classe 1','Remove Class 1 teacher',1),
    ('Teacher2Choose',2,'Assegna / sostituisci prof. Classe 2','Assign / replace Class 2 teacher',2),
    ('Teacher2Remove',2,'Rimuovi prof. Classe 2','Remove Class 2 teacher',2),
    ('Teacher3Choose',2,'Assegna / sostituisci prof. Classe 3','Assign / replace Class 3 teacher',3),
    ('Teacher3Remove',2,'Rimuovi prof. Classe 3','Remove Class 3 teacher',3),
    ('TeachersView',2,'Consulta professori','View teachers',1),
    ('CafeteriaChoose',3,'Aggiungi addetti mensa (max 3)','Add cafeteria staff (max 3)',1),
    ('CafeteriaRemove',3,'Rimuovi addetti mensa','Remove cafeteria staff',1),
    ('CafeteriaView',3,'Consulta mensa','View cafeteria staff',1),
    ('CustodiansChoose',4,'Aggiungi bidelli (max 2)','Add custodians (max 2)',1),
    ('CustodiansRemove',4,'Rimuovi bidelli','Remove custodians',1),
    ('CustodiansView',4,'Consulta bidelli','View custodians',1),
    ('StaffViewAll',0,'Riepilogo personale scolastico','School staff overview',1),
)
ACTION_IDS=tuple(fnv64_highbit('Iliyana:MHS53_Staff_'+token) for token,*_ in ACTIONS)
ACTION_KEYS=tuple(0x5A895100+i for i in range(len(ACTIONS)))


class M53BuildError(ValueError):
    pass


def _fnv1_lower32(value):
    # Confirmed against known Lot51:
    # Iliyana:MHS_Class_1_ -> 0x7C673E56
    # Iliyana:MHS_Class_2_ -> 0x7967390F
    # Iliyana:MHS_Settings -> 0x1E597B9E
    current=0x811c9dc5
    for item in value.lower().encode('utf-8'):
        current=((current*0x01000193)&0xffffffff)^item
    return current


def _category(tpl,number):
    name=NAMES[number]
    iid=CAT_IDS[number]
    base=ET.fromstring(tpl)
    if base.get('c')!='PieMenuCategory' or base.get('n')!=TEMPLATE_NAME:
        raise M53BuildError('Unexpected M52 source category')
    base.set('n',name)
    base.set('s',str(iid))
    base.find('./T[@n="_display_name"]').text='0x{:08X}'.format(CAT_LABELS[number])
    parent=base.find('./T[@n="_parent"]')
    if parent is None:
        raise M53BuildError('Source category not nested')
    parent.text=str(MATCHED_ROOT if number==0 else CAT_IDS[0])
    return ET.tostring(base,encoding='utf-8')


def _simdata(tpl,number):
    name=NAMES[number]
    iid=CAT_IDS[number]
    if (len(name)!=20 or len(tpl)!=475
            or tpl[:4]!=b'DATA'
            or tpl.count(TEMPLATE_NAME.encode('ascii'))!=1
            or struct.unpack_from('<Q',tpl,0x5c)[0]!=(MATCHED_ROOT<<32)
            or _fnv1_lower32(TEMPLATE_NAME)!=0x7c673e56):
        raise M53BuildError('Lot51 original template mismatch')
    output=bytearray(tpl)
    offset=output.find(TEMPLATE_NAME.encode('ascii'))
    output[offset:offset+20]=name.encode('ascii')
    struct.pack_into('<I',output,0x24,_fnv1_lower32(name))
    struct.pack_into('<I',output,0x44,CAT_LABELS[number])
    struct.pack_into('<Q',output,0x5c,
                     (MATCHED_ROOT if number==0 else CAT_IDS[0])<<32)
    return bytes(output)


def _interaction(tpl,number):
    token,cat,_,_,_klass=ACTIONS[number]
    base=ET.fromstring(tpl)
    if (base.get('c')!='MHS39_MHS27RemoveClass1' or
            base.get('m')!='mhs39_visibility_ui'):
        raise M53BuildError('Expected verified M52 immediate action template')
    base.set('m','mhs39_visibility_ui')
    base.set('c','MHS39_MHS53'+token)
    base.set('n','Iliyana:MHS53_Staff_'+token)
    base.set('s',str(ACTION_IDS[number]))
    base.find('./T[@n="category"]').text=str(CAT_IDS[cat])
    base.find('./T[@n="display_name"]').text='0x{:08X}'.format(
        ACTION_KEYS[number])
    return ET.tostring(base,encoding='utf-8')


def _stbl(raw,locale):
    strings=parse_stbl(raw)
    for idx,key in enumerate(CAT_LABELS):
        value=('Personale scolastico','Preside','Professori',
               'Personale mensa','Bidelli') if locale=='it' else (
                   'School staff','Principal','Teachers',
                   'Cafeteria staff','Custodians')
        if key in strings:
            raise M53BuildError('Category STBL key reused')
        strings[key]=value[idx]
    for idx,(_token,cat,it,en,_klass) in enumerate(ACTIONS):
        key=ACTION_KEYS[idx]
        if key in strings:
            raise M53BuildError('Staff action STBL key reused')
        strings[key]=it if locale=='it' else en
    body=bytearray()
    total=0
    for key,value in sorted(strings.items()):
        encoded=value.encode('utf-8')
        if len(encoded)>65535:
            raise M53BuildError('Localization too long')
        body.extend(struct.pack('<IBH',key,0,len(encoded)))
        body.extend(encoded)
        total+=len(encoded)+1
    result=(b'STBL'+struct.pack('<HBQ2sI',5,0,len(strings),b'\0\0',total)
            +bytes(body))
    if parse_stbl(result)!=strings:
        raise M53BuildError('Staff localization roundtrip failed')
    return result


def _inject(tpl):
    root=ET.fromstring(tpl)
    afford=root.find('./L[@n="add_interactions_to_objects"]/U/L[@n="_super_affordances"]')
    if afford is None:
        raise M53BuildError('Existing mailbox injector missing')
    old={int(value.text) for value in afford.findall('T')}
    if any(iid in old for iid in ACTION_IDS):
        raise M53BuildError('Injected staff action already exists')
    for iid in ACTION_IDS:
        ET.SubElement(afford,'T').text=str(iid)
    return ET.tostring(root,encoding='utf-8')


def transformed_resources():
    existing=resources(build_m52())
    if (len(NAMES)!=5 or len(set(CAT_IDS))!=5 or
            any(len(n)!=20 for n in NAMES) or
            any(not 0<iid<2**31 for iid in CAT_IDS) or
            set(CAT_IDS).intersection({MATCHED_ROOT,SETTINGS_CATEGORY,*CATEGORY_IDS})):
        raise M53BuildError('Invalid staff category ID/20 byte names')
    t_cat=next(raw for typ,g,iid,raw in existing
               if typ==CATEGORY_TYPE and iid==CATEGORY_IDS[0])
    t_sim=next(raw for typ,g,iid,raw in existing
               if typ==SIMDATA_TYPE and iid==CATEGORY_IDS[0] and g==SIMDATA_GROUP)
    t_action=next(raw for typ,g,iid,raw in existing
                  if typ==TYPE_INTERACTION and
                  ET.fromstring(raw).get('c')=='MHS39_MHS27RemoveClass1')
    rows=[]
    locales=set()
    injected=0
    for typ,g,iid,raw in existing:
        if typ==TYPE_STBL:
            locale={0:'en',11:'it'}.get(iid>>56)
            if not locale:
                raise M53BuildError('Unexpected STBL language')
            raw=_stbl(raw,locale)
            locales.add(locale)
        elif typ==TYPE_SNIPPET:
            raw=_inject(raw)
            injected+=1
        rows.append((typ,g,iid,raw))
    if locales!={'en','it'} or injected!=1:
        raise M53BuildError('M52 STBL or injector mismatch')
    for j in range(5):
        rows.append((CATEGORY_TYPE,0,CAT_IDS[j],_category(t_cat,j)))
        rows.append((SIMDATA_TYPE,SIMDATA_GROUP,CAT_IDS[j],_simdata(t_sim,j)))
    for j in range(len(ACTIONS)):
        rows.append((TYPE_INTERACTION,0,ACTION_IDS[j],_interaction(t_action,j)))
    if len(rows)!=35+10+len(ACTIONS) or len(set(record[:3] for record in rows))!=len(rows):
        raise M53BuildError('Resource count or IDs collide')
    # The 35 previous resources cannot change, except injector and two STBLs.
    for old,new in zip(existing,rows[:35]):
        if old[:3]!=new[:3] or (
                old[0] not in (TYPE_STBL,TYPE_SNIPPET) and old!=new):
            raise M53BuildError('Regression in M52 menu')
    return rows


def package_bytes():
    original=build_m52()
    entries=transformed_resources()
    head=bytearray(original[:96])
    payload=bytearray()
    index=bytearray(struct.pack('<I',0))
    for typ,g,iid,raw in entries:
        compressed=zlib.compress(raw,9)
        index.extend(ENTRY.pack(typ,g,iid>>32,iid&0xffffffff,
                                96+len(payload),len(compressed)|0x80000000,
                                len(raw),0x5A42,1))
        payload.extend(compressed)
    struct.pack_into('<I',head,0x24,len(entries))
    struct.pack_into('<I',head,0x2c,len(index))
    struct.pack_into('<Q',head,0x40,96+len(payload))
    blob=bytes(head+payload+index)
    if resources(blob)!=entries:
        raise M53BuildError('DBPF resource roundtrip failed')
    gate=inspect_bytes(blob)
    if gate['status']!='STATIC_GATE_PASSED' or (
            gate['category_count']!=10 or gate['simdata_count']!=10):
        raise M53BuildError('10 Lot51-compatible category pairs required')
    return blob


def compile_scripts(dest):
    if sys.version_info[:2]!=(3,7) or importlib.util.MAGIC_NUMBER!=bytes((66,13,13,10)):
        raise M53BuildError('The Sims 4 requires Python 3.7')
    if len(SCRIPTS)!=19 or len({f.name for f in SCRIPTS})!=19:
        raise M53BuildError('Expected 19 unique Python scripts')
    with tempfile.TemporaryDirectory() as tmp:
        with zipfile.ZipFile(str(dest),'w',zipfile.ZIP_DEFLATED) as z:
            for src in SCRIPTS:
                output=Path(tmp)/(src.name+'c')
                py_compile.compile(str(src),cfile=str(output),doraise=True)
                z.write(str(output),arcname=src.name+'c')


def release(folder):
    folder=Path(folder)
    folder.mkdir(parents=True,exist_ok=True)
    blob=package_bytes()
    (folder/PACKAGE).write_bytes(blob)
    compile_scripts(folder/SCRIPT)
    return {
        'status':'MAC_GAME_TEST_REQUIRED',
        'resources':len(resources(blob)),
        'categories':10,
        'staff_actions':len(ACTIONS),
        'compiled_modules':19,
        'package_sha256':hashlib.sha256(blob).hexdigest(),
        'EA_staff_roles_implemented':False,
    }


if __name__=='__main__':
    if len(sys.argv)!=2:
        raise SystemExit('Usage: python -m tooling.build_m53_staff_management <directory>')
    print(json.dumps(release(sys.argv[1]),indent=2))
