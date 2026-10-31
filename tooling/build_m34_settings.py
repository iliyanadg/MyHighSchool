"""M34 safe cumulative Mac test build: 2/3 classes and per-save activation.

Uses the single verified flat menu category from M33, avoiding the
invalid-category-ID bug of M30/M32. Runtime support for pause is
NOT implemented in this release. Does not change real EA attendance.
"""
import hashlib
import importlib.util
import json
import py_compile
import struct
import sys
import tempfile
from pathlib import Path
import xml.etree.ElementTree as ET
import zipfile
import zlib

from tooling.build_m33_flat_recovery import (
    package_bytes as build_m33, SCRIPTS as M33_SCRIPTS,
    NEW_VIEW_IDS, BASE_CATEGORY, MAIN_MENU_KEY)
from tooling.build_m27_removal import (
    fnv64_highbit,TYPE_INTERACTION,TYPE_SNIPPET,TYPE_STBL,ENTRY)
from tooling.m1_links_and_strings import parse_stbl
from tooling.simdata_release_gate import resources,inspect_bytes

ROOT=Path(__file__).resolve().parents[1]
SETTINGS=ROOT/'src'/'m2_registry'/'mhs34_settings.py'
GATE=ROOT/'src'/'m34_settings'/'mhs34_runtime_gate.py'
UI=ROOT/'src'/'m34_settings'/'mhs34_settings_ui.py'
SCRIPTS=tuple(M33_SCRIPTS)+(SETTINGS,GATE,UI)
PACK_NAME='MHS_M34_IMPOSTAZIONI_REGISTRO_TEST.package'
SCRIPT_NAME='MHS_M34_IMPOSTAZIONI_REGISTRO_TEST.ts4script'
NAMES=('Iliyana:MHS34_Enable','Iliyana:MHS34_Disable',
       'Iliyana:MHS34_TwoClasses','Iliyana:MHS34_ThreeClasses')
CLASSES=('MHS34Enable','MHS34Disable','MHS34TwoClasses','MHS34ThreeClasses')
IDS=tuple(fnv64_highbit(name) for name in NAMES)
KEYS=tuple(0x5A892880+i for i in range(4))


class M34BuildError(ValueError):
    pass


def new_actions(rows):
    lookup={(t,i):blob for t,g,i,blob in rows}
    template=lookup.get((TYPE_INTERACTION,NEW_VIEW_IDS[0]))
    if template is None:
        raise M34BuildError('Verified M33 view interaction not found')
    new=[]
    for i in range(4):
        root=ET.fromstring(template)
        if root.find('./T[@n="category"]').text!=str(BASE_CATEGORY):
            raise M34BuildError('Unexpected baseline category')
        root.set('s',str(IDS[i]))
        root.set('n',NAMES[i])
        root.set('c',CLASSES[i])
        root.set('m','mhs34_settings_ui')
        root.find('./T[@n="display_name"]').text='0x{:08X}'.format(KEYS[i])
        new.append((TYPE_INTERACTION,0,IDS[i],ET.tostring(root,encoding='utf-8')))
    return new


def extend_injector(raw):
    root=ET.fromstring(raw)
    target=root.find('./L[@n="add_interactions_to_objects"]/U/L[@n="_super_affordances"]')
    if target is None:
        raise M34BuildError('Verified injector category not found')
    current={int(t.text) for t in target.findall('T')}
    if current.intersection(IDS):
        raise M34BuildError('Duplicate menu interactions')
    for iid in IDS:
        ET.SubElement(target,'T').text=str(iid)
    return ET.tostring(root,encoding='utf-8')


def extend_strings(raw,locale):
    texts=parse_stbl(raw)
    if MAIN_MENU_KEY not in texts or any(k in texts for k in KEYS):
        raise M34BuildError('Unexpected STBL baseline')
    texts[MAIN_MENU_KEY]='MY HIGH SCHOOL (M34 TEST)'
    values=(('Attiva MY HIGH SCHOOL (registro TEST)',
             'Disattiva MY HIGH SCHOOL (registro TEST)',
             'Impostazioni: usa 2 classi',
             'Impostazioni: usa 3 classi') if locale=='it' else
            ('Enable MY HIGH SCHOOL test register',
             'Disable MY HIGH SCHOOL test register',
             'Settings: use 2 classes',
             'Settings: use 3 classes'))
    for key,value in zip(KEYS,values):
        texts[key]=value
    body=bytearray()
    total=0
    for key,value in sorted(texts.items()):
        data=value.encode('utf-8')
        body.extend(struct.pack('<IBH',key,0,len(data)))
        body.extend(data)
        total+=len(data)+1
    compiled=b'STBL'+struct.pack('<HBQ2sI',5,0,len(texts),b'\x00\x00',total)+bytes(body)
    if parse_stbl(compiled)!=texts:
        raise M34BuildError('STBL mismatch')
    return compiled


def package_bytes():
    baseline=build_m33()
    old=resources(baseline)
    additions=new_actions(old)
    if set(IDS).intersection({row[2] for row in old}):
        raise M34BuildError('New IDs collide with existing resources')
    rows=[]
    changed=[]
    for typ,grp,iid,raw in old:
        if typ==TYPE_SNIPPET:
            raw=extend_injector(raw)
            changed.append('injector')
        elif typ==TYPE_STBL:
            locale={0:'en',11:'it'}.get(iid>>56)
            if locale is None:
                raise M34BuildError('Unexpected localization')
            raw=extend_strings(raw,locale)
            changed.append(locale)
        rows.append((typ,grp,iid,raw))
    if sorted(changed)!=['en','injector','it']:
        raise M34BuildError('Unexpected baseline modification')
    rows.extend(additions)
    if len(rows)!=27 or len(set(row[:3] for row in rows))!=27:
        raise M34BuildError('Incorrect resource count')
    head=bytearray(baseline[:96])
    body=bytearray()
    index=bytearray(struct.pack('<I',0))
    for typ,grp,iid,data in rows:
        packed=zlib.compress(data,9)
        index.extend(ENTRY.pack(typ,grp,iid>>32,iid&0xffffffff,
                                96+len(body),len(packed)|0x80000000,
                                len(data),0x5A42,1))
        body.extend(packed)
    struct.pack_into('<I',head,0x24,len(rows))
    struct.pack_into('<I',head,0x2C,len(index))
    struct.pack_into('<Q',head,0x40,96+len(body))
    result=bytes(head+body+index)
    if resources(result)!=rows:
        raise M34BuildError('DBPF roundtrip mismatch')
    info=inspect_bytes(result)
    if (info['status']!='STATIC_GATE_PASSED' or
            info['category_count']!=1 or info['simdata_count']!=1):
        raise M34BuildError('Flat verified menu was changed')
    return result


def compile_scripts(dest):
    if sys.version_info[:2]!=(3,7) or importlib.util.MAGIC_NUMBER!=bytes((66,13,13,10)):
        raise M34BuildError('Requires CPython 3.7 for The Sims 4')
    with tempfile.TemporaryDirectory() as folder:
        with zipfile.ZipFile(str(dest),'w',zipfile.ZIP_DEFLATED) as archive:
            for source in SCRIPTS:
                compiled=Path(folder)/(source.name+'c')
                py_compile.compile(str(source),cfile=str(compiled),doraise=True)
                archive.write(str(compiled),arcname=source.name+'c')


def release(folder):
    folder=Path(folder)
    folder.mkdir(parents=True,exist_ok=True)
    result=package_bytes()
    (folder/PACK_NAME).write_bytes(result)
    compile_scripts(folder/SCRIPT_NAME)
    return {'status':'GAME_TEST_REQUIRED',
            'resources':len(resources(result)),
            'scripts':len(SCRIPTS),
            'sha256':hashlib.sha256(result).hexdigest()}


if __name__=='__main__':
    if len(sys.argv)!=2:
        raise SystemExit('Usage: python -m tooling.build_m34_settings <folder>')
    print(json.dumps(release(sys.argv[1]),indent=2))
