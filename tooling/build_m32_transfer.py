"""M32 cumulative menu: 3 class categories, 6 transfer choices, safe register.

Compile .ts4script with Python 3.7 only. All game UI remains experimental.
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

from tooling.build_m30_nested_menu import (
    package_bytes as build_m30, SCRIPTS as M30_SCRIPTS,
    CATEGORY_IDS, NEW_VIEW_IDS, MAIN_MENU_KEY)
from tooling.build_m27_removal import (
    fnv64_highbit, TYPE_INTERACTION, TYPE_SNIPPET, TYPE_STBL, ENTRY)
from tooling.m1_links_and_strings import parse_stbl
from tooling.simdata_release_gate import resources, inspect_bytes

ROOT=Path(__file__).resolve().parents[1]
TRANSFER_SCRIPT=ROOT/'src'/'m32_transfer'/'mhs32_transfer_ui.py'
SCRIPTS=tuple(M30_SCRIPTS)+(TRANSFER_SCRIPT,)
PACK_NAME='MHS_M32_SOTTOMENU_TRASFERIMENTI_TEST.package'
SCRIPT_NAME='MHS_M32_SOTTOMENU_TRASFERIMENTI_TEST.ts4script'
ROUTES=tuple((a,b) for a in (1,2,3) for b in (1,2,3) if a!=b)
NAMES=tuple('Iliyana:MHS32_Transfer_{}_to_{}'.format(a,b) for a,b in ROUTES)
IDS=tuple(fnv64_highbit(name) for name in NAMES)
KEYS=tuple(0x5A892860+n for n in range(len(ROUTES)))


class M32BuildError(ValueError):
    pass


def new_actions(baseline):
    lookup={(typ,iid):blob for typ,group,iid,blob in baseline}
    result=[]
    for index,(source,destination) in enumerate(ROUTES):
        template=lookup.get((TYPE_INTERACTION,NEW_VIEW_IDS[source-1]))
        if template is None:
            raise M32BuildError('Missing source class view tuning')
        root=ET.fromstring(template)
        if root.find('./T[@n="category"]').text!=str(CATEGORY_IDS[source-1]):
            raise M32BuildError('Class source category mismatch')
        root.set('s',str(IDS[index]))
        root.set('n',NAMES[index])
        root.set('c','MHS32Transfer{}To{}'.format(source,destination))
        root.set('m','mhs32_transfer_ui')
        root.find('./T[@n="display_name"]').text='0x{:08X}'.format(KEYS[index])
        result.append((TYPE_INTERACTION,0,IDS[index],
                       ET.tostring(root,encoding='utf-8')))
    return result


def update_injector(blob):
    root=ET.fromstring(blob)
    affordances=root.find('./L[@n="add_interactions_to_objects"]/U/L[@n="_super_affordances"]')
    if affordances is None:
        raise M32BuildError('Missing injector target')
    existing={int(x.text) for x in affordances.findall('T')}
    if set(IDS).intersection(existing):
        raise M32BuildError('Interaction already injected')
    for iid in IDS:
        ET.SubElement(affordances,'T').text=str(iid)
    return ET.tostring(root,encoding='utf-8')


def update_strings(blob,locale):
    strings=parse_stbl(blob)
    if MAIN_MENU_KEY not in strings or any(key in strings for key in KEYS):
        raise M32BuildError('M32 localization collision')
    strings[MAIN_MENU_KEY]='MY HIGH SCHOOL (M32 TEST)'
    for (source,destination),key in zip(ROUTES,KEYS):
        if locale=='it':
            strings[key]='Trasferisci in Classe {}'.format(destination)
        else:
            strings[key]='Transfer to Class {}'.format(destination)
    body=bytearray()
    total=0
    for key,value in sorted(strings.items()):
        encoded=value.encode('utf-8')
        body.extend(struct.pack('<IBH',key,0,len(encoded)))
        body.extend(encoded)
        total+=len(encoded)+1
    payload=b'STBL'+struct.pack('<HBQ2sI',5,0,len(strings),bytes((0,0)),total)+bytes(body)
    if parse_stbl(payload)!=strings:
        raise M32BuildError('Localization did not roundtrip')
    return payload


def package_bytes():
    baseline=build_m30()
    original=resources(baseline)
    new_actions_list=new_actions(original)
    if set(IDS).intersection({x[2] for x in original}):
        raise M32BuildError('Resource ID already present')
    updated=[]
    modified=[]
    for typ,group,iid,blob in original:
        if typ==TYPE_SNIPPET:
            blob=update_injector(blob)
            modified.append('injector')
        elif typ==TYPE_STBL:
            locale={0:'en',11:'it'}.get(iid>>56)
            if locale is None:
                raise M32BuildError('Unsupported locale')
            blob=update_strings(blob,locale)
            modified.append(locale)
        updated.append((typ,group,iid,blob))
    if sorted(modified)!=['en','injector','it']:
        raise M32BuildError('Wrong number of mutations')
    updated.extend(new_actions_list)
    if len(updated)!=29 or len({row[:3] for row in updated})!=29:
        raise M32BuildError('Incorrect resource count or duplicated keys')
    head=bytearray(baseline[:96])
    body=bytearray()
    index=bytearray(struct.pack('<I',0))
    for typ,group,iid,blob in updated:
        zipped=zlib.compress(blob,9)
        index.extend(ENTRY.pack(typ,group,iid>>32,iid&0xffffffff,
                                96+len(body),len(zipped)|0x80000000,
                                len(blob),0x5A42,1))
        body.extend(zipped)
    struct.pack_into('<I',head,0x24,len(updated))
    struct.pack_into('<I',head,0x2C,len(index))
    struct.pack_into('<Q',head,0x40,96+len(body))
    result=bytes(head+body+index)
    if resources(result)!=updated:
        raise M32BuildError('DBPF roundtrip failure')
    report=inspect_bytes(result)
    if (report['status']!='STATIC_GATE_PASSED' or
            report['category_count']!=4 or report['simdata_count']!=4):
        raise M32BuildError('SimData structural gate failed')
    for old,new in zip(original,updated):
        if old[:3]!=new[:3] or (old[0]==TYPE_INTERACTION and old[3]!=new[3]):
            raise M32BuildError('Existing interaction changed unexpectedly')
    return result


def compile_scripts(output):
    if sys.version_info[:2]!=(3,7) or importlib.util.MAGIC_NUMBER!=bytes((66,13,13,10)):
        raise M32BuildError('The Sims 4 requires CPython 3.7 for this script build')
    with tempfile.TemporaryDirectory() as temporary:
        with zipfile.ZipFile(str(output),'w',zipfile.ZIP_DEFLATED) as z:
            for source in SCRIPTS:
                compiled=Path(temporary)/(source.name+'c')
                py_compile.compile(str(source),cfile=str(compiled),doraise=True)
                z.write(str(compiled),arcname=source.name+'c')
    with zipfile.ZipFile(str(output)) as z:
        if len(z.namelist())!=len(SCRIPTS):
            raise M32BuildError('Missing compiled script')


def release(directory):
    directory=Path(directory)
    directory.mkdir(parents=True,exist_ok=True)
    content=package_bytes()
    (directory/PACK_NAME).write_bytes(content)
    compile_scripts(directory/SCRIPT_NAME)
    return {'status':'EXPERIMENTAL_GAME_TEST_REQUIRED',
            'resources':len(resources(content)),
            'script_modules':len(SCRIPTS),
            'sha256':hashlib.sha256(content).hexdigest()}


if __name__=='__main__':
    if len(sys.argv)!=2:
        raise SystemExit('Usage: python -m tooling.build_m32_transfer <outdir>')
    print(json.dumps(release(sys.argv[1]),indent=2))
