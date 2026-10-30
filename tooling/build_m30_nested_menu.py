"""M30: group existing M29 mailbox actions into three nested class categories.

Prototype requiring in-game validation. The source category's Tuning XML
and compiled SimData come from the exact tested Lot51 user export bundled
in the repository. We clone its fixed-width fields without changing its
schema or its string-table offsets.

The external student register and Python modules remain unchanged.
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

from tooling.build_m29_bundle import (
    package_bytes as build_m29, SCRIPTS as M29_SCRIPTS, IDS as VIEW_IDS)
from tooling.build_m27_removal import (
    IDS as REMOVE_IDS, TYPE_INTERACTION, TYPE_STBL, ENTRY)
from tooling.build_m28_bundle import PICKER_3, REMOVE_3
from tooling.m1_links_and_strings import parse_stbl
from tooling.simdata_release_gate import resources, inspect_bytes

ROOT=Path(__file__).resolve().parents[1]
SCRIPTS=tuple(M29_SCRIPTS)
PACK_NAME='MHS_M30_MENU_CLASSI_TEST.package'
SCRIPT_NAME='MHS_M30_MENU_CLASSI_TEST.ts4script'
TYPE_CATEGORY=0x03E9D964
TYPE_SIMDATA=0x545AC67A
SIMDATA_GROUP=0x00E9D967
BASE_CATEGORY=14567074618947653827
OLD_INSTANCE_NAME=b'Iliyana:MHS_MainMenu'
CATEGORY_NAMES=tuple('Iliyana:MHS_Class_{}_'.format(n) for n in (1,2,3))
NEW_KEYS=(0x5A892841,0x5A892842,0x5A892843)
MAIN_MENU_KEY=0x3FCE8D06
OLD_PICKERS=(10604127343160706865, 10604124044625822232)
ENROLL_IDS=OLD_PICKERS+(PICKER_3,)
REMOVE_CLASS_IDS=tuple(REMOVE_IDS)+(REMOVE_3,)
NEW_VIEW_IDS=tuple(VIEW_IDS)


class M30BuildError(ValueError):
    pass


def category_id(name):
    """31-bit instance IDs to avoid tuning-reference 64-bit UI issues."""
    hash64=0xcbf29ce484222325
    for byte in name.encode('utf-8'):
        hash64=((hash64 ^ byte)*0x100000001b3)&((1<<64)-1)
    return (hash64 & 0x7fffffff) or 1


CATEGORY_IDS=tuple(category_id(name) for name in CATEGORY_NAMES)


def create_child_xml(base, number):
    root=ET.fromstring(base)
    if (root.attrib.get('c')!='PieMenuCategory' or
            root.attrib.get('s')!=str(BASE_CATEGORY)):
        raise M30BuildError('Unexpected original category XML')
    root.set('s',str(CATEGORY_IDS[number]))
    root.set('n',CATEGORY_NAMES[number])
    display=root.find('./T[@n="_display_name"]')
    if display is None:
        raise M30BuildError('Missing category display name')
    display.text='0x{:08X}'.format(NEW_KEYS[number])
    if root.find('./T[@n="_parent"]') is not None:
        raise M30BuildError('Unexpected parent in top-level baseline')
    ET.SubElement(root,'T',{'n':'_parent'}).text=str(BASE_CATEGORY)
    return ET.tostring(root,encoding='utf-8')


def create_child_simdata(base, number):
    """Patch fields of a known, byte-identical client SimData fixture.

    Instance struct has _display_name at 0x44 (uint32) and _parent at
    0x5c (uint64). All other structure/offsets remain untouched;
    names are deliberately exactly 20 ASCII bytes.
    """
    name=CATEGORY_NAMES[number].encode('ascii')
    if len(OLD_INSTANCE_NAME)!=20 or len(name)!=20:
        raise M30BuildError('Changing instance-name length would shift binary offsets')
    if not (len(base)==475 and base[:4]==b'DATA' and
            struct.unpack_from('<I',base,0x44)[0]==MAIN_MENU_KEY and
            struct.unpack_from('<Q',base,0x5c)[0]==0 and
            base.count(OLD_INSTANCE_NAME)==1 and
            base.endswith(OLD_INSTANCE_NAME+b'\x00')):
        raise M30BuildError('SimData no longer matches verified Lot51 layout')
    output=bytearray(base)
    struct.pack_into('<I',output,0x44,NEW_KEYS[number])
    struct.pack_into('<Q',output,0x5c,BASE_CATEGORY)
    offset=output.find(OLD_INSTANCE_NAME)
    output[offset:offset+20]=name
    if len(output)!=len(base) or output[:4]!=b'DATA':
        raise M30BuildError('SimData corruption')
    return bytes(output)


def remap_interaction(blob, category):
    root=ET.fromstring(blob)
    target=root.find('./T[@n="category"]')
    if target is None or target.text!=str(BASE_CATEGORY):
        raise M30BuildError('Original interaction category unexpectedly changed')
    target.text=str(category)
    return ET.tostring(root,encoding='utf-8')


def update_strings(blob,locale):
    entries=parse_stbl(blob)
    if MAIN_MENU_KEY not in entries:
        raise M30BuildError('Missing parent label')
    entries[MAIN_MENU_KEY]='MY HIGH SCHOOL (M30 TEST)'
    if set(NEW_KEYS).intersection(entries):
        raise M30BuildError('Localization key collision')
    for number,key in enumerate(NEW_KEYS):
        entries[key]='Classe {}'.format(number+1) if locale=='it' else 'Class {}'.format(number+1)
    payload=bytearray()
    total=0
    for key,value in sorted(entries.items()):
        encoded=value.encode('utf-8')
        payload.extend(struct.pack('<IBH',key,0,len(encoded)))
        payload.extend(encoded)
        total+=len(encoded)+1
    result=b'STBL'+struct.pack('<HBQ2sI',5,0,len(entries),bytes((0,0)),total)+bytes(payload)
    if parse_stbl(result)!=entries:
        raise M30BuildError('STBL roundtrip failed')
    return result


def transformed_resources(old):
    target_ids={}
    for class_number in range(3):
        for instance in (ENROLL_IDS[class_number],
                         REMOVE_CLASS_IDS[class_number],
                         NEW_VIEW_IDS[class_number]):
            if instance in target_ids:
                raise M30BuildError('An interaction belongs to two classes')
            target_ids[instance]=CATEGORY_IDS[class_number]
    if not (len(target_ids)==9 and len(set(CATEGORY_IDS))==3 and
            BASE_CATEGORY not in CATEGORY_IDS):
        raise M30BuildError('Duplicate or invalid category identifiers')
    parent_xml=next((data for typ,grp,inst,data in old
                     if typ==TYPE_CATEGORY and inst==BASE_CATEGORY),None)
    parent_simdata=next((data for typ,grp,inst,data in old
                         if typ==TYPE_SIMDATA and inst==BASE_CATEGORY and grp==SIMDATA_GROUP),None)
    if parent_xml is None or parent_simdata is None:
        raise M30BuildError('Root menu tuning/SimData pair missing')
    found=set()
    changed_locales=set()
    new=[]
    for typ,group,iid,raw in old:
        if typ==TYPE_INTERACTION and iid in target_ids:
            raw=remap_interaction(raw,target_ids[iid])
            found.add(iid)
        elif typ==TYPE_STBL:
            locale={0:'en',11:'it'}.get(iid>>56)
            if locale not in ('en','it'):
                raise M30BuildError('Unsupported STBL locale')
            raw=update_strings(raw,locale)
            changed_locales.add(locale)
        new.append((typ,group,iid,raw))
    if found!=set(target_ids) or changed_locales!={'en','it'}:
        raise M30BuildError('Cannot group every menu action')
    for n in range(3):
        new.append((TYPE_CATEGORY,0,CATEGORY_IDS[n],
                    create_child_xml(parent_xml,n)))
        new.append((TYPE_SIMDATA,SIMDATA_GROUP,CATEGORY_IDS[n],
                    create_child_simdata(parent_simdata,n)))
    keys=[row[:3] for row in new]
    if len(keys)!=len(set(keys)) or len(new)!=23:
        raise M30BuildError('Duplicate resource keys or wrong resource count')
    return new


def package_bytes():
    baseline=build_m29()
    original=resources(baseline)
    updated=transformed_resources(original)
    head=bytearray(baseline[:96])
    payload=bytearray()
    index=bytearray(struct.pack('<I',0))
    for typ,group,iid,data in updated:
        comp=zlib.compress(data,9)
        index.extend(ENTRY.pack(typ,group,iid>>32,iid&0xffffffff,
                                96+len(payload),len(comp)|0x80000000,
                                len(data),0x5A42,1))
        payload.extend(comp)
    struct.pack_into('<I',head,0x24,len(updated))
    struct.pack_into('<I',head,0x2C,len(index))
    struct.pack_into('<Q',head,0x40,96+len(payload))
    result=bytes(head+payload+index)
    if resources(result)!=updated:
        raise M30BuildError('DBPF roundtrip failure')
    info=inspect_bytes(result)
    if (info['status']!='STATIC_GATE_PASSED' or
            info['category_count']!=4 or info['simdata_count']!=4):
        raise M30BuildError('Nested category SimData structural audit failed')
    return result


def compile_scripts(dest):
    if sys.version_info[:2]!=(3,7) or importlib.util.MAGIC_NUMBER!=bytes((66,13,13,10)):
        raise M30BuildError('Requires Python 3.7 for The Sims 4 scripts')
    with tempfile.TemporaryDirectory() as directory:
        with zipfile.ZipFile(str(dest),'w',zipfile.ZIP_DEFLATED) as archive:
            for source in SCRIPTS:
                compiled=Path(directory)/(source.name+'c')
                py_compile.compile(str(source),cfile=str(compiled),doraise=True)
                archive.write(str(compiled),arcname=source.name+'c')


def release(folder):
    folder=Path(folder)
    folder.mkdir(parents=True,exist_ok=True)
    bundle=package_bytes()
    (folder/PACK_NAME).write_bytes(bundle)
    compile_scripts(folder/SCRIPT_NAME)
    return {'status':'GAME_TEST_REQUIRED',
            'resources':len(resources(bundle)),
            'modules':len(SCRIPTS),
            'package_sha256':hashlib.sha256(bundle).hexdigest()}


if __name__=='__main__':
    if len(sys.argv)!=2:
        raise SystemExit('Usage: python -m tooling.build_m30_nested_menu <folder>')
    print(json.dumps(release(sys.argv[1]),indent=2))
