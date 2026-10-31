"""M40: controlled second hypothesis for proper nested MY HIGH SCHOOL menu.

M37 game screenshots show both MY HIGH SCHOOL and Class 1 standalone;
it no longer breaks the mailbox. The parent refs are paired and compact,
but class 1 does not nest.

S4S/ModTheSims reports custom nested categories sometimes need explicit
_collapsible=False in XML and 0 in matching SimData. Unlike M35B/M37,
the cloned Lot51 category sets SimData _collapsible=1 and omits the
parameter in XML.

This test changes ONLY that flag on both root and child menu categories
while preserving registration, scripts, interactions, and student data.
Do not treat in-game behavior as proved until Mac test.
"""
import hashlib
import json
import struct
import sys
from pathlib import Path
import xml.etree.ElementTree as ET
import zlib

from tooling.build_m37_small_root import (
    package_bytes as build_m37,NEW_ROOT,CATEGORY_ID,
    TYPE_CATEGORY,TYPE_SIMDATA,SIMDATA_GROUP)
from tooling.build_m34_settings import compile_scripts
from tooling.build_m27_removal import ENTRY
from tooling.simdata_release_gate import resources,inspect_bytes

PACK_NAME='MHS_M40_MENU_GERARCHICO_COLLAPSIBLE_FALSE_TEST.package'
SCRIPT_NAME='MHS_M40_MENU_GERARCHICO_COLLAPSIBLE_FALSE_TEST.ts4script'


class M40BuildError(ValueError):
    pass


def category_xml(blob):
    root=ET.fromstring(blob)
    if root.get('c')!='PieMenuCategory':
        raise M40BuildError('Unexpected category tuning')
    if root.find('./T[@n="_collapsible"]') is not None:
        raise M40BuildError('Flag already present, cannot isolate test')
    # TDesc Builder + ModTheSims recommend explicitly writing the same
    # false value to XML and the companion SimData for nested categories.
    ET.SubElement(root,'T',{'n':'_collapsible'}).text='False'
    return ET.tostring(root,encoding='utf-8')


def category_simdata(blob):
    if len(blob)!=475 or blob[:4]!=b'DATA' or blob[0x40]!=1:
        raise M40BuildError('Unexpected boolean at SimData 0x40')
    out=bytearray(blob)
    out[0x40]=0
    return bytes(out)


def transformed_resources():
    baseline=resources(build_m37())
    ids={NEW_ROOT,CATEGORY_ID}
    if NEW_ROOT==CATEGORY_ID:
        raise M40BuildError('Root and child collide')
    changed=set()
    rows=[]
    for typ,grp,iid,raw in baseline:
        if iid in ids and typ==TYPE_CATEGORY:
            raw=category_xml(raw)
            changed.add(('xml',iid))
        elif iid in ids and typ==TYPE_SIMDATA and grp==SIMDATA_GROUP:
            raw=category_simdata(raw)
            changed.add(('simdata',iid))
        rows.append((typ,grp,iid,raw))
    if changed!={('xml',n) for n in ids}|{('simdata',n) for n in ids}:
        raise M40BuildError('Changed unexpected resource count')
    if len(rows)!=len(baseline):
        raise M40BuildError('Unexpected total resources')
    for before,after in zip(baseline,rows):
        if before[:3]!=after[:3]:
            raise M40BuildError('Changed TGI')
        if before[2] not in ids and before!=after:
            raise M40BuildError('Modified unrelated resources')
    return rows


def package_bytes():
    old=build_m37()
    rows=transformed_resources()
    head=bytearray(old[:96])
    data=bytearray()
    index=bytearray(struct.pack('<I',0))
    for typ,grp,iid,raw in rows:
        compressed=zlib.compress(raw,9)
        index.extend(ENTRY.pack(typ,grp,iid>>32,iid&0xffffffff,
                                96+len(data),len(compressed)|0x80000000,
                                len(raw),0x5A42,1))
        data.extend(compressed)
    struct.pack_into('<I',head,0x24,len(rows))
    struct.pack_into('<I',head,0x2c,len(index))
    struct.pack_into('<Q',head,0x40,96+len(data))
    package=bytes(head+data+index)
    if resources(package)!=rows:
        raise M40BuildError('DBPF roundtrip failed')
    info=inspect_bytes(package)
    if (info['status']!='STATIC_GATE_PASSED' or
        info['category_count']!=2 or info['simdata_count']!=2):
        raise M40BuildError('Category schema validation failed')
    return package


def release(folder):
    folder=Path(folder)
    folder.mkdir(parents=True,exist_ok=True)
    pack=package_bytes()
    (folder/PACK_NAME).write_bytes(pack)
    compile_scripts(folder/SCRIPT_NAME)
    return {
        'status':'MAC_IN_GAME_TEST_REQUIRED',
        'change':'Set root+child _collapsible=False in both XML and SimData',
        'sha256':hashlib.sha256(pack).hexdigest(),
        'resource_count':len(resources(pack)),
    }


if __name__=='__main__':
    if len(sys.argv)!=2:
        raise SystemExit('Usage: python -m tooling.build_m40_noncollapsible_parent <outdir>')
    print(json.dumps(release(sys.argv[1]),indent=2))
