"""M36: link the working two-entry Class 1 category under MY HIGH SCHOOL.

Game-tested M35B proved that a single standalone category with TWO
interactions creates a real submenu and the mailbox does not freeze.
M36 changes ONLY this category's parent field, in both XML and SimData.

This is a *single-parent* in-game safety probe. The earlier M30/M32
multi-parent attempts broke the mailbox with an invalid category ID.
No new scripts or roster writes. Preserve M34 as the recovery version.
"""
import hashlib
import json
import struct
import sys
from pathlib import Path
import xml.etree.ElementTree as ET
import zlib

from tooling.build_m35b_two_actions import (
    package_bytes as build_m35b, CATEGORY_ID, BASE_CATEGORY)
from tooling.build_m35_category_smoke import (
    TYPE_CATEGORY, TYPE_SIMDATA, SIMDATA_GROUP)
from tooling.build_m27_removal import ENTRY
from tooling.build_m34_settings import compile_scripts as compile_m34_scripts
from tooling.simdata_release_gate import resources, inspect_bytes

PACK_NAME='MHS_M36_CLASSE1_SOTTO_MENU_TEST.package'
SCRIPT_NAME='MHS_M36_CLASSE1_SOTTO_MENU_TEST.ts4script'


class M36Error(ValueError):
    pass


def set_parent_xml(raw):
    root=ET.fromstring(raw)
    if root.attrib.get('s')!=str(CATEGORY_ID):
        raise M36Error('Category mismatch')
    if root.find('./T[@n="_parent"]') is not None:
        raise M36Error('Parent already defined in baseline')
    ET.SubElement(root,'T',{'n':'_parent'}).text=str(BASE_CATEGORY)
    return ET.tostring(root,encoding='utf-8')


def set_parent_simdata(raw):
    if (raw[:4]!=b'DATA' or len(raw)!=475 or
            struct.unpack_from('<Q',raw,0x5c)[0]!=0):
        raise M36Error('Unexpected tested M35B SimData structure')
    data=bytearray(raw)
    struct.pack_into('<Q',data,0x5c,BASE_CATEGORY)
    return bytes(data)


def package_bytes():
    baseline=build_m35b()
    previous=resources(baseline)
    records=[]
    changed=[]
    for typ,group,instance,raw in previous:
        if instance==CATEGORY_ID and typ==TYPE_CATEGORY:
            raw=set_parent_xml(raw)
            changed.append('xml')
        elif (instance==CATEGORY_ID and typ==TYPE_SIMDATA
                and group==SIMDATA_GROUP):
            raw=set_parent_simdata(raw)
            changed.append('simdata')
        records.append((typ,group,instance,raw))
    if sorted(changed)!=['simdata','xml']:
        raise M36Error('No matching category or SimData pair')
    head=bytearray(baseline[:96])
    body=bytearray()
    index=bytearray(struct.pack('<I',0))
    for typ,group,iid,raw in records:
        comp=zlib.compress(raw,9)
        index.extend(ENTRY.pack(typ,group,iid>>32,iid&0xffffffff,
                                96+len(body),len(comp)|0x80000000,
                                len(raw),0x5A42,1))
        body.extend(comp)
    struct.pack_into('<I',head,0x24,len(records))
    struct.pack_into('<I',head,0x2c,len(index))
    struct.pack_into('<Q',head,0x40,96+len(body))
    output=bytes(head+body+index)
    if resources(output)!=records:
        raise M36Error('DBPF roundtrip mismatch')
    report=inspect_bytes(output)
    if (report['status']!='STATIC_GATE_PASSED' or
            report['category_count']!=2 or report['simdata_count']!=2):
        raise M36Error('Category/SimData static audit failed')
    return output


def release(folder):
    folder=Path(folder)
    folder.mkdir(parents=True,exist_ok=True)
    blob=package_bytes()
    (folder/PACK_NAME).write_bytes(blob)
    compile_m34_scripts(folder/SCRIPT_NAME)
    return {'status':'GAME_UI_PARENT_TEST_REQUIRED',
            'resources':len(resources(blob)),
            'sha256':hashlib.sha256(blob).hexdigest()}


if __name__=='__main__':
    if len(sys.argv)!=2:
        raise SystemExit('Usage: python -m tooling.build_m36_nested_class1 <outdir>')
    print(json.dumps(release(sys.argv[1]),indent=2))
