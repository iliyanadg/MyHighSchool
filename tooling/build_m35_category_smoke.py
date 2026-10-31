"""M35 isolated one-category smoke test, based on game-tested M34.

DO NOT confuse this with the final M35 nested menu. This deliberately
tests exactly ONE new PieMenuCategory (a standalone 'Classe 1 - M35 PROVA'
rather than a child) to isolate resource registration from parent linkage.
The M30/M32 child-category prototype froze the mailbox pie menu. Only
the view-only Class 1 interaction is moved here; all other M34
interactions and all roster/setting scripts are unchanged.

If UI errors, remove the M35 pair and restore tested M34.
"""
import hashlib
import json
import struct
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
import zlib

from tooling.build_m34_settings import (
    package_bytes as build_m34, compile_scripts as compile_m34_scripts)
from tooling.build_m30_nested_menu import (
    CATEGORY_IDS, NEW_KEYS, BASE_CATEGORY, OLD_INSTANCE_NAME,
    CATEGORY_NAMES, NEW_VIEW_IDS, MAIN_MENU_KEY,
    TYPE_CATEGORY, TYPE_SIMDATA, SIMDATA_GROUP)
from tooling.build_m27_removal import TYPE_INTERACTION, TYPE_STBL, ENTRY
from tooling.m1_links_and_strings import parse_stbl
from tooling.simdata_release_gate import resources, inspect_bytes

CATEGORY_ID=CATEGORY_IDS[0]
CATEGORY_NAME=CATEGORY_NAMES[0]
CATEGORY_KEY=NEW_KEYS[0]
VIEW_ONLY_INTERACTION=NEW_VIEW_IDS[0]
PACK_NAME='MHS_M35_SMOKE_CATEGORIA1_TEST.package'
SCRIPT_NAME='MHS_M35_SMOKE_CATEGORIA1_TEST.ts4script'


class M35SmokeError(ValueError):
    pass


def make_test_category_xml(original):
    root=ET.fromstring(original)
    if (root.get('s')!=str(BASE_CATEGORY)
            or root.get('c')!='PieMenuCategory'
            or root.find('./T[@n="_parent"]') is not None):
        raise M35SmokeError('Wrong baseline category tuning')
    root.set('s',str(CATEGORY_ID))
    root.set('n',CATEGORY_NAME)
    label=root.find('./T[@n="_display_name"]')
    if label is None or label.text!='0x{:08X}'.format(MAIN_MENU_KEY):
        raise M35SmokeError('Wrong baseline localization')
    label.text='0x{:08X}'.format(CATEGORY_KEY)
    # NO _parent here. This isolates whether a new category can be
    # registered before testing parent linkage to MY HIGH SCHOOL.
    return ET.tostring(root,encoding='utf-8')


def make_test_category_simdata(original):
    """Clone checked EA-compatible schema with zero parent, new display key."""
    name=CATEGORY_NAME.encode('ascii')
    if (len(name)!=20 or len(OLD_INSTANCE_NAME)!=20
            or len(original)!=475 or original[:4]!=b'DATA'
            or struct.unpack_from('<I',original,0x44)[0]!=MAIN_MENU_KEY
            or struct.unpack_from('<Q',original,0x5c)[0]!=0
            or original.count(OLD_INSTANCE_NAME)!=1):
        raise M35SmokeError('Refusing unexpected base SimData layout')
    output=bytearray(original)
    struct.pack_into('<I',output,0x44,CATEGORY_KEY)
    loc=output.find(OLD_INSTANCE_NAME)
    output[loc:loc+20]=name
    assert len(output)==len(original)
    # Parent remains ZERO, unlike M30/M32.
    assert struct.unpack_from('<Q',output,0x5c)[0]==0
    return bytes(output)


def set_category_on_view_only(xml):
    root=ET.fromstring(xml)
    ref=root.find('./T[@n="category"]')
    if ref is None or ref.text!=str(BASE_CATEGORY):
        raise M35SmokeError('Wrong Class 1 view interaction baseline')
    ref.text=str(CATEGORY_ID)
    return ET.tostring(root,encoding='utf-8')


def add_label(raw,locale):
    values=parse_stbl(raw)
    if CATEGORY_KEY in values:
        raise M35SmokeError('Conflicting label key')
    values[CATEGORY_KEY]=(
        'Classe 1 - M35 PROVA' if locale=='it' else 'Class 1 - M35 TEST'
    )
    # Distinguishable in-game from M34 while retaining original hierarchy.
    values[MAIN_MENU_KEY]='MY HIGH SCHOOL (M35 SMOKE TEST)'
    out=bytearray()
    n_bytes=0
    for key,text in sorted(values.items()):
        encoded=text.encode('utf-8')
        out.extend(struct.pack('<IBH',key,0,len(encoded)))
        out.extend(encoded)
        n_bytes+=len(encoded)+1
    result=b'STBL'+struct.pack('<HBQ2sI',
                              5,0,len(values),b'\x00\x00',n_bytes)+bytes(out)
    if parse_stbl(result)!=values:
        raise M35SmokeError('Localization roundtrip error')
    return result


def transformed_resources(original):
    category_xml=next((raw for t,g,i,raw in original
                       if t==TYPE_CATEGORY and i==BASE_CATEGORY),None)
    category_simdata=next((raw for t,g,i,raw in original
                           if t==TYPE_SIMDATA and g==SIMDATA_GROUP
                           and i==BASE_CATEGORY),None)
    if category_xml is None or category_simdata is None:
        raise M35SmokeError('Missing verified M34 category pair')
    rows=[]
    touched=[]
    for t,g,i,raw in original:
        if t==TYPE_INTERACTION and i==VIEW_ONLY_INTERACTION:
            raw=set_category_on_view_only(raw)
            touched.append('view')
        elif t==TYPE_STBL:
            locale={0:'en',11:'it'}.get(i>>56)
            if locale not in ('en','it'):
                raise M35SmokeError('Unrecognized localization')
            raw=add_label(raw,locale)
            touched.append(locale)
        rows.append((t,g,i,raw))
    if sorted(touched)!=['en','it','view']:
        raise M35SmokeError('Missing or duplicate modified resources')
    rows.append((TYPE_CATEGORY,0,CATEGORY_ID,
                 make_test_category_xml(category_xml)))
    rows.append((TYPE_SIMDATA,SIMDATA_GROUP,CATEGORY_ID,
                 make_test_category_simdata(category_simdata)))
    if (len(rows)!=29
            or len(set((t,g,i) for t,g,i,raw in rows))!=len(rows)):
        raise M35SmokeError('Duplicated resource keys')
    return rows


def package_bytes():
    base=build_m34()
    old=resources(base)
    rows=transformed_resources(old)
    header=bytearray(base[:96])
    body=bytearray()
    index=bytearray(struct.pack('<I',0))
    for t,g,i,raw in rows:
        zipped=zlib.compress(raw,9)
        index.extend(ENTRY.pack(t,g,i>>32,i&0xffffffff,
                                96+len(body),len(zipped)|0x80000000,
                                len(raw),0x5A42,1))
        body.extend(zipped)
    struct.pack_into('<I',header,0x24,len(rows))
    struct.pack_into('<I',header,0x2C,len(index))
    struct.pack_into('<Q',header,0x40,96+len(body))
    result=bytes(header+body+index)
    if resources(result)!=rows:
        raise M35SmokeError('DBPF mismatch')
    report=inspect_bytes(result)
    if (report['status']!='STATIC_GATE_PASSED'
            or report['category_count']!=2 or report['simdata_count']!=2):
        raise M35SmokeError('New category/SimData failed static checks')
    # Preserve every non-view interaction in M34 byte-for-byte.
    for (ot,og,oi,ob),(nt,ng,ni,nb) in zip(old,rows):
        if (ot,og,oi)!=(nt,ng,ni):
            raise M35SmokeError('Accidental resource reordering')
        if ot==TYPE_INTERACTION and oi!=VIEW_ONLY_INTERACTION and ob!=nb:
            raise M35SmokeError('An existing action has unexpectedly changed')
    return result


def release(folder):
    folder=Path(folder)
    folder.mkdir(parents=True,exist_ok=True)
    blob=package_bytes()
    (folder/PACK_NAME).write_bytes(blob)
    # Reuse the tested M34 Python 3.7 scripts unchanged.
    compile_m34_scripts(folder/SCRIPT_NAME)
    return {'status':'ONE_CATEGORY_GAME_SMOKE_TEST_REQUIRED',
            'resources':len(resources(blob)),
            'package_sha256':hashlib.sha256(blob).hexdigest()}


if __name__=='__main__':
    if len(sys.argv)!=2:
        raise SystemExit('Usage: python -m tooling.build_m35_category_smoke <outdir>')
    print(json.dumps(release(sys.argv[1]),indent=2))
