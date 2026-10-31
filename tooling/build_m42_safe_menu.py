"""M42: patch the M41 in-game TestResult.FALSE exception and clean option labels.

Confirmed player report (game version 1.129.39.1230):
  Exception during call to test method on
  Iliyana:MHS32_Transfer_3_to_2,
  AttributeError: type object 'TestResult' has no attribute 'FALSE'

The bundled M39 visibility script is fixed to return TestResult(False, ...)
rather than the nonexistent class constant. This release also fixes
invalid 2->3 transfer availability, cleans settings text and applies
the EA Friendly category root priority 9, keeping paired SimData aligned.

M41->M42 category parent graph remains unchanged. The user's screenshot
shows classes listed outside the MY HIGH SCHOOL category, so actual
navigation is NOT considered fixed by this offline build.
Save TEST only, remove previous MHS files. No school attendance control yet.
"""
import hashlib
import json
import struct
import sys
import xml.etree.ElementTree as ET
import zlib
from pathlib import Path

from tooling.build_m41_complete_menu import (
    package_bytes as build_m41,NEW_ROOT,CATEGORY_TYPE,SIMDATA_TYPE,
    SIMDATA_GROUP)
from tooling.build_m34_settings import KEYS
from tooling.build_m39_conditional_menu import compile_scripts
from tooling.build_m27_removal import ENTRY,TYPE_STBL
from tooling.m1_links_and_strings import parse_stbl
from tooling.simdata_release_gate import resources,inspect_bytes

PACK_NAME='MHS_M42_MENU_CORREZIONE_EXCEPTION_TEST.package'
SCRIPT_NAME='MHS_M42_MENU_CORREZIONE_EXCEPTION_TEST.ts4script'

class M42BuildError(ValueError):
    pass


def named_actions(raw,locale):
    names=parse_stbl(raw)
    words={
        'it':('Attiva MY HIGH SCHOOL','Disattiva MY HIGH SCHOOL',
              'Usa 2 classi','Abilita Classe 3'),
        'en':('Enable MY HIGH SCHOOL','Disable MY HIGH SCHOOL',
              'Use 2 classes','Enable Class 3'),
    }[locale]
    # The 2-class option disables the optional third class.
    if locale=='it':
        words=('Attiva MY HIGH SCHOOL','Disattiva MY HIGH SCHOOL',
               'Disabilita Classe 3','Abilita Classe 3')
    else:
        words=('Enable MY HIGH SCHOOL','Disable MY HIGH SCHOOL',
               'Disable Class 3','Enable Class 3')
    if not set(KEYS).issubset(names):
        raise M42BuildError('M34 action labels missing')
    names.update(zip(KEYS,words))
    out=bytearray()
    total=0
    for key,label in sorted(names.items()):
        enc=label.encode('utf-8')
        out.extend(struct.pack('<IBH',key,0,len(enc)))
        out.extend(enc)
        total+=len(enc)+1
    result=b'STBL'+struct.pack('<HBQ2sI',5,0,len(names),b'\0\0',total)+bytes(out)
    if parse_stbl(result)!=names:
        raise M42BuildError('STBL roundtrip mismatch')
    return result


def root_category_xml(raw):
    item=ET.fromstring(raw)
    if item.get('c')!='PieMenuCategory' or item.get('s')!=str(NEW_ROOT):
        raise M42BuildError('Wrong root category')
    priority=item.find('./T[@n="_display_priority"]')
    if priority is None:
        priority=ET.SubElement(item,'T',{'n':'_display_priority'})
    priority.text='9'
    return ET.tostring(item,encoding='utf-8')


def root_category_simdata(raw):
    if raw[:4]!=b'DATA' or len(raw)!=475:
        raise M42BuildError('Unexpected current EA-compatible SimData')
    content=bytearray(raw)
    struct.pack_into('<i',content,0x48,9)
    return bytes(content)


def transformed_resources():
    original=resources(build_m41())
    changed=set()
    rows=[]
    for typ,group,iid,blob in original:
        if iid==NEW_ROOT and typ==CATEGORY_TYPE:
            blob=root_category_xml(blob)
            changed.add('xml')
        elif iid==NEW_ROOT and typ==SIMDATA_TYPE and group==SIMDATA_GROUP:
            blob=root_category_simdata(blob)
            changed.add('simdata')
        elif typ==TYPE_STBL:
            loc={0:'en',11:'it'}.get(iid>>56)
            if not loc:
                raise M42BuildError('Unknown localization')
            blob=named_actions(blob,loc)
            changed.add(loc)
        rows.append((typ,group,iid,blob))
    if changed!={'xml','simdata','en','it'} or len(rows)!=35:
        raise M42BuildError('Unexpected package resource inventory')
    return rows


def package_bytes():
    old=build_m41()
    rows=transformed_resources()
    header=bytearray(old[:96])
    data=bytearray()
    index=bytearray(struct.pack('<I',0))
    for typ,group,iid,raw in rows:
        packed=zlib.compress(raw,9)
        index.extend(ENTRY.pack(typ,group,iid>>32,iid&0xffffffff,
                                96+len(data),len(packed)|0x80000000,
                                len(raw),0x5A42,1))
        data.extend(packed)
    struct.pack_into('<I',header,0x24,len(rows))
    struct.pack_into('<I',header,0x2c,len(index))
    struct.pack_into('<Q',header,0x40,96+len(data))
    package=bytes(header+data+index)
    if resources(package)!=rows:
        raise M42BuildError('Package DBPF roundtrip mismatch')
    info=inspect_bytes(package)
    if (info['status']!='STATIC_GATE_PASSED' or
            info['category_count']!=5 or info['simdata_count']!=5):
        raise M42BuildError('Category static check failed')
    return package


def release(folder):
    folder=Path(folder)
    folder.mkdir(parents=True,exist_ok=True)
    blob=package_bytes()
    (folder/PACK_NAME).write_bytes(blob)
    compile_scripts(folder/SCRIPT_NAME)
    return {
      'status':'UNVERIFIED_MAC_TEST_REQUIRED',
      'features':'M41 complete tree + fixed TestResult usage + transfer gate',
      'categories':5,
      'resources':len(resources(blob)),
      'sha256':hashlib.sha256(blob).hexdigest(),
    }


if __name__=='__main__':
    if len(sys.argv)!=2:
        raise SystemExit('Usage: python -m tooling.build_m42_safe_menu <outdir>')
    print(json.dumps(release(sys.argv[1]),indent=2))
