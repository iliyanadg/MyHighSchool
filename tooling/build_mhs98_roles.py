"""M98 Mac: native school Core Roles submenu without modifying EA attendance.

Reuses verified M55/M94 63-resource package graph and M53 Lot51 SimData
category reconstruction. New: 1 category pair + 11 native picker actions.
The installed M94 inspector remains; all original 63 resource keys/payloads
are unchanged except the SAME injector and 2 STBLs, additive changes only.
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

from tooling.build_m55_attendance_trial import package_bytes as mhs94_pkg
from tooling.build_mhs94_probe import script_sources as m94_scripts
from tooling.build_m27_removal import (TYPE_INTERACTION,TYPE_SNIPPET,
                                        TYPE_STBL,ENTRY,fnv64_highbit)
from tooling.build_m30_nested_menu import CATEGORY_IDS,category_id
from tooling.build_m41_complete_menu import (CATEGORY_TYPE,SIMDATA_TYPE,
                                               SIMDATA_GROUP)
from tooling.build_m43_matched_root import MATCHED_ROOT
from tooling.build_m53_staff_management import _fnv1_lower32
from tooling.m1_links_and_strings import parse_stbl
from tooling.simdata_release_gate import inspect_bytes,resources

ROOT=Path(__file__).resolve().parents[1]
MENU=ROOT/'src'/'m98_in_game_roles'/'mhs98_core_role_ui.py'
STORE=ROOT/'src'/'m97_core_reservations'/'mhs97_core_role_store.py'
PACKAGE='MHS_M98_RUOLI_SPECIALI_MAC_TEST.package'
SCRIPT='MHS_M98_RUOLI_SPECIALI_MAC_TEST.ts4script'
MENU_NAME='Iliyana:MHS_RoleCore' # Exactly 20 bytes, verified Lot51 layout
CAT_ID=category_id(MENU_NAME)
CAT_STBL_KEY=0x5A896080

ROLES=('cheer','chess','football','computer','mean')
LABELS={
    'cheer':('Cheerleader','Cheerleader'),
    'chess':('Scacchi','Chess'),
    'football':('Football','Football'),
    'computer':('Informatica','Computer club'),
    'mean':('Sim perfido','Mean Sim'),
}
ACTIONS=tuple((role,mode) for role in ROLES for mode in ('assign','remove'))
ACTIONS+=(('all','view'),)
ACTION_IDS=tuple(fnv64_highbit('Iliyana:MHS98_Role_'+role+'_'+mode)
                 for role,mode in ACTIONS)
ACTION_KEYS=tuple(0x5A896100+i for i in range(len(ACTIONS)))

class M98BuildError(ValueError):
    pass

def script_sources():
    sources=tuple(m94_scripts())+(STORE,MENU)
    if (len(sources)!=35 or len(set(p.name for p in sources))!=35
            or sum(p.name=='mhs55_attendance_ui.py' for p in sources)!=1):
        raise M98BuildError('M94 script graph mismatch')
    return sources

def _category(template):
    root=ET.fromstring(template)
    if (root.get('c')!='PieMenuCategory' or
            root.get('n')!='Iliyana:MHS_Class_1_'):
        raise M98BuildError('Unverified MHS nested menu category template')
    root.set('n',MENU_NAME)
    root.set('s',str(CAT_ID))
    name=root.find('./T[@n="_display_name"]')
    parent=root.find('./T[@n="_parent"]')
    if name is None or parent is None:
        raise M98BuildError('Missing menu display or parent')
    name.text='0x{:08X}'.format(CAT_STBL_KEY)
    parent.text=str(MATCHED_ROOT)
    return ET.tostring(root,encoding='utf-8')

def _simdata(template):
    original='Iliyana:MHS_Class_1_'
    if (len(MENU_NAME)!=20 or len(template)!=475 or
            template[:4]!=b'DATA' or
            template.count(original.encode('ascii'))!=1 or
            struct.unpack_from('<Q',template,0x5c)[0]!=(MATCHED_ROOT<<32)
            or _fnv1_lower32(original)!=0x7C673E56):
        raise M98BuildError('Lot51 binary category template invalid')
    out=bytearray(template)
    pos=out.find(original.encode('ascii'))
    out[pos:pos+20]=MENU_NAME.encode('ascii')
    struct.pack_into('<I',out,0x24,_fnv1_lower32(MENU_NAME))
    struct.pack_into('<I',out,0x44,CAT_STBL_KEY)
    struct.pack_into('<Q',out,0x5c,MATCHED_ROOT<<32)
    return bytes(out)

def _interaction(template,index):
    root=ET.fromstring(template)
    if root.get('c')!='MHS55TryOne':
        raise M98BuildError('M55 immediate-interaction template not found')
    role,mode=ACTIONS[index]
    root.set('c','MHS98Role'+mode.capitalize()+role.capitalize())
    root.set('m','mhs98_core_role_ui')
    root.set('n','Iliyana:MHS98_Role_'+role+'_'+mode)
    root.set('s',str(ACTION_IDS[index]))
    category=root.find('./T[@n="category"]')
    display=root.find('./T[@n="display_name"]')
    if category is None or display is None:
        raise M98BuildError('Interaction class/category/display missing')
    category.text=str(CAT_ID)
    display.text='0x{:08X}'.format(ACTION_KEYS[index])
    return ET.tostring(root,encoding='utf-8')

def _stbl(raw,lang):
    table=dict(parse_stbl(raw))
    entries={CAT_STBL_KEY:('Ruoli speciali' if lang=='it'
                            else 'Special school roles')}
    for i,(role,mode) in enumerate(ACTIONS):
        if mode=='view':
            label=('Riepilogo ruoli speciali' if lang=='it'
                   else 'View special school roles')
        else:
            prefix=('Scegli / sostituisci ' if mode=='assign'
                    else 'Rimuovi ') if lang=='it' else (
                    'Choose / replace ' if mode=='assign' else 'Remove ')
            label=prefix+LABELS[role][0 if lang=='it' else 1]
        entries[ACTION_KEYS[i]]=label
    if set(entries)&set(table):
        raise M98BuildError('M98 localization key collision')
    table.update(entries)
    data=bytearray()
    total=0
    for key,value in sorted(table.items()):
        encoded=value.encode('utf-8')
        data.extend(struct.pack('<IBH',key,0,len(encoded)))
        data.extend(encoded)
        total+=len(encoded)+1
    out=b'STBL'+struct.pack('<HBQ2sI',5,0,len(table),b'\0\0',total)+bytes(data)
    if parse_stbl(out)!=table:
        raise M98BuildError('STBL failed round-trip')
    return out

def _inject(raw):
    root=ET.fromstring(raw)
    entry=root.find('./L[@n="add_interactions_to_objects"]/U/'
                    'L[@n="_super_affordances"]')
    if entry is None:
        raise M98BuildError('Verified mailbox/PC injector missing')
    known=set(int(x.text) for x in entry.findall('T'))
    if known.intersection(ACTION_IDS):
        raise M98BuildError('Duplicate M98 action injection')
    for iid in ACTION_IDS:
        ET.SubElement(entry,'T').text=str(iid)
    return ET.tostring(root,encoding='utf-8')

def transformed_resources():
    old=resources(mhs94_pkg())
    if len(old)!=63 or len(ACTIONS)!=11 or len(set(ACTION_IDS))!=11:
        raise M98BuildError('Expected verified M94 base')
    if CAT_ID in set(CATEGORY_IDS)|{MATCHED_ROOT} or not 0<CAT_ID<2**31:
        raise M98BuildError('Role menu category key invalid')
    basecat=next((content for t,g,k,content in old
                  if t==CATEGORY_TYPE and k==CATEGORY_IDS[0]),None)
    basedata=next((content for t,g,k,content in old
                   if t==SIMDATA_TYPE and k==CATEGORY_IDS[0]
                   and g==SIMDATA_GROUP),None)
    baseinteraction=next((content for t,g,k,content in old
                          if t==TYPE_INTERACTION and
                          ET.fromstring(content).get('c')=='MHS55TryOne'),None)
    if basecat is None or basedata is None or baseinteraction is None:
        raise M98BuildError('Original tested menu templates missing')
    result=[]
    localizations=set()
    changed=0
    for typ,group,iid,data in old:
        before=data
        if typ==TYPE_STBL:
            lang={0:'en',11:'it'}.get(iid>>56)
            if lang is None:
                raise M98BuildError('Unknown locale')
            data=_stbl(data,lang)
            localizations.add(lang)
        elif typ==TYPE_SNIPPET:
            data=_inject(data)
        if data!=before:
            changed+=1
        result.append((typ,group,iid,data))
    if localizations!={'en','it'} or changed!=3:
        raise M98BuildError('Only additive injector and 2 STBL changes allowed')
    result.extend((
        (CATEGORY_TYPE,0,CAT_ID,_category(basecat)),
        (SIMDATA_TYPE,SIMDATA_GROUP,CAT_ID,_simdata(basedata)),
    ))
    for i in range(len(ACTIONS)):
        result.append((TYPE_INTERACTION,0,ACTION_IDS[i],
                       _interaction(baseinteraction,i)))
    if (len(result)!=76 or len(set(x[:3] for x in result))!=76
            or len(result[:63])!=len(old)):
        raise M98BuildError('Expected 76 unique DBPF resource keys')
    for before,after in zip(old,result[:63]):
        if before[:3]!=after[:3]:
            raise M98BuildError('Changed existing resource identity')
        if before[0] not in (TYPE_STBL,TYPE_SNIPPET) and before!=after:
            raise M98BuildError('Changed existing EA/MHS action')
    return result

def package_bytes():
    original=mhs94_pkg()
    entries=transformed_resources()
    header=bytearray(original[:96])
    payload=bytearray()
    index=bytearray(struct.pack('<I',0))
    for typ,group,iid,raw in entries:
        compressed=zlib.compress(raw,9)
        index.extend(ENTRY.pack(typ,group,iid>>32,iid&0xffffffff,
                                96+len(payload),len(compressed)|0x80000000,
                                len(raw),0x5A42,1))
        payload.extend(compressed)
    struct.pack_into('<I',header,0x24,len(entries))
    struct.pack_into('<I',header,0x2c,len(index))
    struct.pack_into('<Q',header,0x40,96+len(payload))
    blob=bytes(header+payload+index)
    if resources(blob)!=entries:
        raise M98BuildError('DBPF resource readback failed')
    check=inspect_bytes(blob)
    if (check['status']!='STATIC_GATE_PASSED' or
            check['resource_count']!=76 or
            check['category_count']!=11 or
            check['simdata_count']!=11):
        raise M98BuildError('11 linked native category/SimData pairs required')
    return blob

def release(folder):
    if sys.version_info[:2]!=(3,7) or importlib.util.MAGIC_NUMBER!=bytes((66,13,13,10)):
        raise M98BuildError('Mac The Sims 4 needs Python3.7 script bytecode')
    folder=Path(folder)
    folder.mkdir(parents=True,exist_ok=True)
    blob=package_bytes()
    (folder/PACKAGE).write_bytes(blob)
    with tempfile.TemporaryDirectory() as tmp:
        with zipfile.ZipFile(str(folder/SCRIPT),'w',zipfile.ZIP_DEFLATED) as z:
            for source in script_sources():
                compiled=Path(tmp)/(source.name+'c')
                py_compile.compile(str(source),cfile=str(compiled),doraise=True)
                z.write(str(compiled),arcname=source.name+'c')
    with zipfile.ZipFile(str(folder/SCRIPT)) as archive:
        names=archive.namelist()
        if len(names)!=35 or not all(archive.read(n)[:4]==bytes((66,13,13,10))
                                   for n in names):
            raise M98BuildError('Invalid 35-module Python 3.7 archive')
        for required in ('mhs97_core_role_store.pyc',
                         'mhs98_core_role_ui.pyc',
                         'mhs94_school_job_probe.pyc'):
            if required not in names:
                raise M98BuildError('Missing runtime role menu '+required)
    report={'status':'M98_NATIVE_MANUAL_ROLE_MENU_NOT_EA_ATTENDANCE_CONTROLLER',
            'package_resources':76,'compiled_modules':35,
            'new_menu_categories':1,'new_native_actions':11,
            'EA_situation_creation_changed':False,
            'EA_filters_modified':False,
            'manual_role_choices_per_save':True,
            'school_attendance_16_verified':False,
            'package_sha256':hashlib.sha256(blob).hexdigest()}
    (folder/'MHS_M98_BUILD_REPORT.json').write_text(
        json.dumps(report,indent=2,sort_keys=True))
    return report

if __name__=='__main__':
    if len(sys.argv)!=2:
        raise SystemExit('Usage: python -m tooling.build_mhs98_roles OUTPUT_FOLDER')
    print(json.dumps(release(sys.argv[1]),indent=2))
