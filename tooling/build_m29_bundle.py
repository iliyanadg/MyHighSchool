"""Build M29 cumulative test package. Does not prove game runtime compatibility."""
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

from tooling.build_m28_bundle import (
    package_bytes as build_m28, SCRIPTS as M28_SCRIPTS)
from tooling.build_m27_removal import (
    fnv64_highbit, BASE_CATEGORY, TYPE_INTERACTION, TYPE_SNIPPET,
    TYPE_STBL, ENTRY)
from tooling.m1_links_and_strings import parse_stbl
from tooling.simdata_release_gate import resources, inspect_bytes

ROOT=Path(__file__).resolve().parents[1]
CONTROLS=ROOT/'src'/'m29_registry'/'mhs29_controls.py'
SCRIPTS=tuple(M28_SCRIPTS)+(CONTROLS,)
PACK_NAME='MHS_M29_REGISTRO_SICURO_TEST.package'
SCRIPT_NAME='MHS_M29_REGISTRO_SICURO_TEST.ts4script'
MENU_KEY=0x3FCE8D06
NAMES=tuple('Iliyana:MHS29_ViewClass{}'.format(x) for x in (1,2,3))
IDS=tuple(fnv64_highbit(name) for name in NAMES)
STBL_KEYS=(0x5A892839,0x5A89283A,0x5A89283B)


class M29BuildError(ValueError):
    pass


def new_interaction(klass):
    idx=klass-1
    root=ET.Element('I',{'c':'MHS29ViewClass{}'.format(klass),
                           'i':'interaction',
                           'm':'mhs29_controls',
                           'n':NAMES[idx],
                           's':str(IDS[idx])})
    ET.SubElement(root,'T',{'n':'category'}).text=str(BASE_CATEGORY)
    ET.SubElement(root,'T',{'n':'display_name'}).text='0x{:08X}'.format(STBL_KEYS[idx])
    ET.SubElement(root,'E',{'n':'target_type'}).text='OBJECT'
    ET.SubElement(root,'V',{'n':'_saveable','t':'disabled'})
    tests=ET.SubElement(root,'L',{'n':'test_globals'})
    u=ET.SubElement(ET.SubElement(tests,'V',{'t':'sim_info'}),'U',{'n':'sim_info'})
    ages=ET.SubElement(ET.SubElement(u,'V',{'n':'ages','t':'specified'}),
                       'L',{'n':'specified'})
    for age in ('TEEN','YOUNGADULT','ADULT','ELDER'):
        ET.SubElement(ages,'E').text=age
    ET.SubElement(u,'E',{'n':'who'}).text='Actor'
    return TYPE_INTERACTION,0,IDS[idx],ET.tostring(root,encoding='utf-8')


def extend_injector(blob):
    root=ET.fromstring(blob)
    target=root.find('./L[@n="add_interactions_to_objects"]/U/L[@n="_super_affordances"]')
    if target is None:
        raise M29BuildError('Missing mailbox injector')
    existing={int(item.text) for item in target.findall('T')}
    if set(IDS).intersection(existing):
        raise M29BuildError('Duplicate view menu interaction')
    for iid in IDS:
        ET.SubElement(target,'T').text=str(iid)
    return ET.tostring(root,encoding='utf-8')


def extend_strings(blob,locale):
    values=parse_stbl(blob)
    if MENU_KEY not in values or set(STBL_KEYS).intersection(values):
        raise M29BuildError('Unexpected localization baseline')
    values[MENU_KEY]='MY HIGH SCHOOL (M29 TEST)'
    for i,key in enumerate(STBL_KEYS):
        if locale=='it':
            values[key]='Consulta iscritti - Classe {}'.format(i+1)
        else:
            values[key]='View enrolled students - Class {}'.format(i+1)
    raw=bytearray()
    size=0
    for key,value in sorted(values.items()):
        b=value.encode('utf-8')
        raw.extend(struct.pack('<IBH',key,0,len(b)))
        raw.extend(b)
        size+=len(b)+1
    payload=b'STBL'+struct.pack('<HBQ2sI',5,0,len(values),bytes((0,0)),size)+bytes(raw)
    if parse_stbl(payload)!=values:
        raise M29BuildError('STBL did not roundtrip')
    return payload


def package_bytes():
    original=build_m28()
    entries=resources(original)
    changed=[]
    output_rows=[]
    for typ,group,iid,blob in entries:
        if typ==TYPE_SNIPPET:
            blob=extend_injector(blob)
            changed.append('injector')
        elif typ==TYPE_STBL:
            locale={0:'en',11:'it'}.get(iid>>56)
            if locale is None:
                raise M29BuildError('Unexpected language')
            blob=extend_strings(blob,locale)
            changed.append(locale)
        output_rows.append((typ,group,iid,blob))
    if sorted(changed)!=['en','injector','it']:
        raise M29BuildError('Unexpected resource mutations')
    output_rows.extend(new_interaction(n) for n in (1,2,3))
    if len(output_rows)!=17:
        raise M29BuildError('Expected 17 package resources')
    if len({(a,b,c) for a,b,c,d in output_rows})!=17:
        raise M29BuildError('Duplicate resource IDs')

    head=bytearray(original[:96])
    body=bytearray()
    index=bytearray(struct.pack('<I',0))
    for typ,group,iid,blob in output_rows:
        compressed=zlib.compress(blob,9)
        index.extend(ENTRY.pack(typ,group,iid>>32,iid&0xFFFFFFFF,
                                96+len(body),len(compressed)|0x80000000,
                                len(blob),0x5A42,1))
        body.extend(compressed)
    struct.pack_into('<I',head,0x24,len(output_rows))
    struct.pack_into('<I',head,0x2C,len(index))
    struct.pack_into('<Q',head,0x40,96+len(body))
    payload=bytes(head+body+index)
    if resources(payload)!=output_rows:
        raise M29BuildError('DBPF resource verification failed')
    if inspect_bytes(payload)['status']!='STATIC_GATE_PASSED':
        raise M29BuildError('SIMDATA baseline failed')
    for a,b in zip(entries,output_rows):
        if a[:3]!=b[:3] or (a[0]==TYPE_INTERACTION and a[3]!=b[3]):
            raise M29BuildError('Previously built interaction changed')
    return payload


def compile_scripts(dest):
    if sys.version_info[:2]!=(3,7) or importlib.util.MAGIC_NUMBER!=bytes((66,13,13,10)):
        raise M29BuildError('Requires Python 3.7 bytecode')
    with tempfile.TemporaryDirectory() as temporary:
        with zipfile.ZipFile(str(dest),'w',zipfile.ZIP_DEFLATED) as result:
            for path in SCRIPTS:
                pyc=Path(temporary)/(path.name+'c')
                py_compile.compile(str(path),cfile=str(pyc),doraise=True)
                result.write(str(pyc),arcname=path.name+'c')


def release(folder):
    folder=Path(folder)
    folder.mkdir(parents=True,exist_ok=True)
    payload=package_bytes()
    (folder/PACK_NAME).write_bytes(payload)
    compile_scripts(folder/SCRIPT_NAME)
    return {'status':'REQUIRES_MAC_GAME_TEST',
            'resources':len(resources(payload)),
            'scripts':len(SCRIPTS),
            'sha256':hashlib.sha256(payload).hexdigest()}


if __name__=='__main__':
    if len(sys.argv)!=2:
        raise SystemExit('Usage: python -m tooling.build_m29_bundle <folder>')
    print(json.dumps(release(sys.argv[1]),indent=2))
