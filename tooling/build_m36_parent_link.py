"""M36 ONE parent link smoke test: nest already working M35B class menu.

Game evidence 2026-10-31: M35B new category renders with TWO actions
'Consulta iscritti - Classe 1' and 'Rimuovi studenti - Classe 1'.
Neither operation writes without separate confirmation.

Change from M35B exactly:
 * child PieMenuCategory XML add _parent pointing to known root
 * child PieMenuCategory SimData set _parent TableSetReference
No new tuning or script actions, no rewrites to enrollment, registrations
or settings.  NOT a finished 3-class or dynamic menu.
"""
import hashlib
import json
import struct
import sys
from pathlib import Path
import xml.etree.ElementTree as ET
import zlib

from tooling.build_m35b_two_actions import package_bytes as build_m35b
from tooling.build_m35_category_smoke import (
    CATEGORY_ID, BASE_CATEGORY, TYPE_CATEGORY, TYPE_SIMDATA, SIMDATA_GROUP)
from tooling.build_m34_settings import compile_scripts as compile_m34_scripts
from tooling.build_m27_removal import ENTRY
from tooling.simdata_release_gate import resources, inspect_bytes

PACK_NAME='MHS_M36_PARENT_SOTTOMENU_CLASSE1_TEST.package'
SCRIPT_NAME='MHS_M36_PARENT_SOTTOMENU_CLASSE1_TEST.ts4script'


class M36BuildError(ValueError):
    pass


def link_child_xml(blob):
    root=ET.fromstring(blob)
    if (root.get('s')!=str(CATEGORY_ID)
            or root.get('c')!='PieMenuCategory'
            or root.find('./T[@n="_parent"]') is not None):
        raise M36BuildError('Unexpected working M35B category')
    ET.SubElement(root,'T',{'n':'_parent'}).text=str(BASE_CATEGORY)
    return ET.tostring(root,encoding='utf-8')


def link_child_simdata(blob):
    if (len(blob)!=475 or blob[:4]!=b'DATA'
            or struct.unpack_from('<Q',blob,0x5c)[0]!=0):
        raise M36BuildError('Unexpected M35B category SimData')
    new=bytearray(blob)
    struct.pack_into('<Q',new,0x5c,BASE_CATEGORY)
    return bytes(new)


def transformed_resources():
    baseline=resources(build_m35b())
    new=[]
    touched=[]
    for typ,group,iid,raw in baseline:
        if typ==TYPE_CATEGORY and iid==CATEGORY_ID:
            if group!=0:
                raise M36BuildError('Unexpected category group')
            raw=link_child_xml(raw)
            touched.append('xml')
        elif typ==TYPE_SIMDATA and iid==CATEGORY_ID:
            if group!=SIMDATA_GROUP:
                raise M36BuildError('Unexpected SimData group')
            raw=link_child_simdata(raw)
            touched.append('simdata')
        new.append((typ,group,iid,raw))
    if sorted(touched)!=['simdata','xml']:
        raise M36BuildError('Exactly one category pair should be linked')
    if len(new)!=len(baseline):
        raise M36BuildError('Number of resources changed')
    for before,after in zip(baseline,new):
        if before[:3]!=after[:3]:
            raise M36BuildError('Changed TGI')
        if before[2]!=CATEGORY_ID and before!=after:
            raise M36BuildError('Unexpected unrelated resource mutation')
    return new


def package_bytes():
    baseline=build_m35b()
    data=transformed_resources()
    header=bytearray(baseline[:96])
    body=bytearray()
    index=bytearray(struct.pack('<I',0))
    for typ,group,iid,raw in data:
        compressed=zlib.compress(raw,9)
        index.extend(ENTRY.pack(
            typ,group,iid>>32,iid&0xffffffff,
            96+len(body),len(compressed)|0x80000000,
            len(raw),0x5A42,1))
        body.extend(compressed)
    struct.pack_into('<I',header,0x24,len(data))
    struct.pack_into('<I',header,0x2c,len(index))
    struct.pack_into('<Q',header,0x40,96+len(body))
    output=bytes(header+body+index)
    if resources(output)!=data:
        raise M36BuildError('DBPF roundtrip failed')
    report=inspect_bytes(output)
    if (report['status']!='STATIC_GATE_PASSED' or
            report['category_count']!=2 or
            report['simdata_count']!=2):
        raise M36BuildError('Paired category structural gate failed')
    return output


def release(folder):
    folder=Path(folder)
    folder.mkdir(parents=True,exist_ok=True)
    blob=package_bytes()
    (folder/PACK_NAME).write_bytes(blob)
    compile_m34_scripts(folder/SCRIPT_NAME)
    return {
        'status':'UNVERIFIED_MAC_GAME_SMOKE_TEST',
        'resources':len(resources(blob)),
        'category_pairs':2,
        'change':'Single _parent relationship added to tested M35B class category',
        'sha256':hashlib.sha256(blob).hexdigest()
    }


if __name__=='__main__':
    if len(sys.argv)!=2:
        raise SystemExit('Usage: python -m tooling.build_m36_parent_link <outdir>')
    print(json.dumps(release(sys.argv[1]),indent=2))
