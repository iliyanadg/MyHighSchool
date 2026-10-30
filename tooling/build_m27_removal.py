"""Build M27 test UI: M25 unchanged selection + two native removal options.

Python 3.7 is required ONLY to generate TS4 bytecode; otherwise static
Python tests can examine the 11-resource DBPF.
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

from tooling.build_m25_enrollment import build_package as build_m25
from tooling.build_m25_enrollment import SCRIPTS as M25_SCRIPTS
from tooling.m1_links_and_strings import parse_stbl
from tooling.simdata_release_gate import resources, inspect_bytes

ROOT=Path(__file__).resolve().parents[1]
CUSTOM_SCRIPT=ROOT/'src'/'m27_remove_ui'/'mhs27_remove_ui.py'
REMOVE_ENGINE=ROOT/'src'/'m26_withdrawal'/'mhs26_remove.py'
SCRIPTS=tuple(M25_SCRIPTS)+(REMOVE_ENGINE,CUSTOM_SCRIPT)
PACK_NAME='MHS_M27_RIMOZIONE_TEST.package'
SCRIPT_NAME='MHS_M27_RIMOZIONE_TEST.ts4script'
BASE_CATEGORY=14567074618947653827
TYPE_INTERACTION=0xE882D22F
TYPE_SNIPPET=0x7DF2169C
TYPE_STBL=0x220557DA
ENTRY=struct.Struct('<IIIIIIIHH')
NAMES=('Iliyana:MHS27_RemoveStudents_Class1',
       'Iliyana:MHS27_RemoveStudents_Class2')
STBL_KEY=(0x6F58CA11,0x6F58CA12)
MENU_NAME_KEY=0x3FCE8D06


class BuildError(ValueError):
    pass


def fnv64_highbit(name):
    h=0xCBF29CE484222325
    for n in name.encode('utf-8'):
        h=((h^n)*0x100000001B3)&((1<<64)-1)
    return h | (1<<63)


IDS=tuple(fnv64_highbit(name) for name in NAMES)


def new_interaction(number):
    klass=number+1
    root=ET.Element('I',{
        'c':'MHS27RemoveClass'+str(klass),
        'i':'interaction',
        'm':'mhs27_remove_ui',
        'n':NAMES[number],
        's':str(IDS[number])})
    ET.SubElement(root,'T',{'n':'category'}).text=str(BASE_CATEGORY)
    ET.SubElement(root,'T',{'n':'display_name'}).text='0x{:08X}'.format(STBL_KEY[number])
    ET.SubElement(root,'E',{'n':'target_type'}).text='OBJECT'
    ET.SubElement(root,'V',{'n':'_saveable','t':'disabled'})
    tests=ET.SubElement(root,'L',{'n':'test_globals'})
    u=ET.SubElement(ET.SubElement(tests,'V',{'t':'sim_info'}),'U',{'n':'sim_info'})
    ages=ET.SubElement(ET.SubElement(u,'V',{'n':'ages','t':'specified'}),
                       'L',{'n':'specified'})
    for name in ('TEEN','YOUNGADULT','ADULT','ELDER'):
        ET.SubElement(ages,'E').text=name
    ET.SubElement(u,'E',{'n':'who'}).text='Actor'
    return (TYPE_INTERACTION,0,IDS[number],ET.tostring(root,encoding='utf-8'))


def append_injector(data):
    root=ET.fromstring(data)
    affordances=root.find('./L[@n="add_interactions_to_objects"]/U/L[@n="_super_affordances"]')
    if affordances is None:
        raise BuildError('Original M25 mailbox injector invalid')
    existing={int((node.text or '0').strip()) for node in affordances.findall('T')}
    for iid in IDS:
        if iid in existing:
            raise BuildError('Removal interaction already inserted')
        ET.SubElement(affordances,'T').text=str(iid)
    return ET.tostring(root,encoding='utf-8')


def update_stbl(payload, locale):
    values=parse_stbl(payload)
    if MENU_NAME_KEY not in values:
        raise BuildError('Missing M25 category title')
    values[MENU_NAME_KEY]='MY HIGH SCHOOL (M27 TEST)'
    values[STBL_KEY[0]]=(
        'Rimuovi studenti - Classe 1' if locale=='it' else 'Remove students - Class 1')
    values[STBL_KEY[1]]=(
        'Rimuovi studenti - Classe 2' if locale=='it' else 'Remove students - Class 2')
    raw=bytearray()
    total=0
    for key,value in sorted(values.items()):
        b=value.encode('utf-8')
        raw.extend(struct.pack('<IBH',key,0,len(b)))
        raw.extend(b)
        total+=len(b)+1
    output=(b'STBL'+struct.pack('<HBQ2sI',5,0,len(values),bytes((0,0)),total)+bytes(raw))
    if parse_stbl(output)!=values:
        raise BuildError('STBL roundtrip mismatch')
    return output


def modify_resources(old):
    adjusted=[]
    changed=[]
    for typ,group,iid,blob in old:
        if typ==TYPE_SNIPPET:
            blob=append_injector(blob)
            changed.append('injector')
        elif typ==TYPE_STBL:
            locale={0:'en',11:'it'}.get(iid>>56)
            if not locale:
                raise BuildError('Missing locale')
            blob=update_stbl(blob,locale)
            changed.append('stbl-'+locale)
        adjusted.append((typ,group,iid,blob))
    if sorted(changed)!=['injector','stbl-en','stbl-it']:
        raise BuildError('Unexpected mutations')
    for number in (0,1):
        adjusted.append(new_interaction(number))
    if len(adjusted)!=11:
        raise BuildError('Expected M25 9 resources plus 2 removal interactions')
    return adjusted


def package_bytes():
    base=build_m25()
    original=resources(base)
    entries=modify_resources(original)
    header=bytearray(base[:96])
    if header[:4]!=b'DBPF' or struct.unpack_from('<I',header,0x3C)[0]!=3:
        raise BuildError('Invalid original DBPF header')
    body=bytearray()
    index=bytearray(struct.pack('<I',0))
    for typ,group,iid,raw in entries:
        comp=zlib.compress(raw,9)
        index.extend(ENTRY.pack(typ,group,iid>>32,iid&0xffffffff,
                                96+len(body),len(comp)|0x80000000,
                                len(raw),0x5A42,1))
        body.extend(comp)
    struct.pack_into('<I',header,0x24,len(entries))
    struct.pack_into('<I',header,0x2C,len(index))
    struct.pack_into('<Q',header,0x40,96+len(body))
    payload=bytes(header+body+index)
    if resources(payload)!=entries:
        raise BuildError('DBPF roundtrip mismatch')
    if inspect_bytes(payload)['status']!='STATIC_GATE_PASSED':
        raise BuildError('M27 SimData pair invalid')
    # Preserve the original M25 confirmation, pickers and category byte for byte.
    if entries[:2]!=original[:2]:
        raise BuildError('M25 category and binary SimData changed')
    for old,now in zip(original,entries):
        if old[:3]!=now[:3]:
            raise BuildError('A tested M25 tuning TGI was altered')
        if old[0]==TYPE_INTERACTION and old[3]!=now[3]:
            raise BuildError('M25 enrollment interactions must not change')
    return payload


def compile_scripts(output):
    if sys.version_info[:2]!=(3,7) or importlib.util.MAGIC_NUMBER!=bytes((66,13,13,10)):
        raise BuildError('TS4 scripts require Python 3.7')
    with tempfile.TemporaryDirectory() as directory:
        with zipfile.ZipFile(str(output),'w',zipfile.ZIP_DEFLATED) as archive:
            for source in SCRIPTS:
                pyc=Path(directory)/(source.name+'c')
                py_compile.compile(str(source),cfile=str(pyc),doraise=True)
                archive.write(str(pyc),arcname=source.name+'c')
    with zipfile.ZipFile(str(output)) as archive:
        if set(archive.namelist())!={source.name+'c' for source in SCRIPTS}:
            raise BuildError('Missing script in zip')


def release(folder):
    folder=Path(folder)
    folder.mkdir(parents=True,exist_ok=True)
    package=package_bytes()
    (folder/PACK_NAME).write_bytes(package)
    compile_scripts(folder/SCRIPT_NAME)
    return {'package_sha256':hashlib.sha256(package).hexdigest(),
            'package_bytes':len(package),'resources':11,'scripts':len(SCRIPTS),
            'status':'EXPERIMENTAL_MAC_GAME_TEST_REQUIRED'}


if __name__=='__main__':
    if len(sys.argv)!=2:
        raise SystemExit('Uso: python -m tooling.build_m27_removal <destination>')
    print(json.dumps(release(sys.argv[1]),indent=2))
