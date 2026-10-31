"""M37: fix reproducible M36 broken menu by shrinking parent category ID.

M35B works in game with one standalone 31-bit category containing two
Class 1 items. M36 linked that category's _parent to the M34 root category
whose original tuning ID is 14567074618947653827 (> 2^31).
The result was an 'invalid category ID' UI exception and no mailbox menu.

M37 remaps root menu category to a new 31-bit ID, reassigns all interactions
formerly targeting the old root, and points the child _parent at the new
root. Other interaction tuning is unchanged, registry Python is unchanged.
Does NOT implement final conditional menu or pause-time actions.
"""
import hashlib
import json
import struct
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
import zlib

from tooling.build_m36_parent_link import package_bytes as m36_bad
from tooling.build_m35_category_smoke import (
    CATEGORY_ID, BASE_CATEGORY, TYPE_CATEGORY, TYPE_SIMDATA,
    SIMDATA_GROUP, TYPE_INTERACTION)
from tooling.build_m30_nested_menu import category_id
from tooling.build_m34_settings import compile_scripts as compile_m34_scripts
from tooling.build_m27_removal import ENTRY, TYPE_STBL
from tooling.m1_links_and_strings import parse_stbl
from tooling.simdata_release_gate import resources, inspect_bytes

ROOT_NAME='Iliyana:MHS_MainMenu'
NEW_ROOT=category_id('Iliyana:MHS_Root_Small_v37')
PACK_NAME='MHS_M37_ROOT_31BIT_NESTED_TEST.package'
SCRIPT_NAME='MHS_M37_ROOT_31BIT_NESTED_TEST.ts4script'
MAIN_LABEL=0x3FCE8D06


class M37BuildError(ValueError):
    pass


def replace_root_tuning(blob):
    root=ET.fromstring(blob)
    if root.get('c')!='PieMenuCategory' or root.get('s')!=str(BASE_CATEGORY):
        raise M37BuildError('Wrong root tuning')
    root.set('s',str(NEW_ROOT))
    return ET.tostring(root,encoding='utf-8')


def replace_child_parent(blob):
    root=ET.fromstring(blob)
    item=root.find('./T[@n="_parent"]')
    if root.get('s')!=str(CATEGORY_ID) or item is None or item.text!=str(BASE_CATEGORY):
        raise M37BuildError('Wrong nested child tuning')
    item.text=str(NEW_ROOT)
    return ET.tostring(root,encoding='utf-8')


def replace_child_simdata(blob):
    if blob[:4]!=b'DATA' or len(blob)!=475 or struct.unpack_from('<Q',blob,0x5c)[0]!=BASE_CATEGORY:
        raise M37BuildError('Wrong nested child SimData')
    data=bytearray(blob)
    struct.pack_into('<Q',data,0x5c,NEW_ROOT)
    return bytes(data)


def replace_interaction_root(blob):
    root=ET.fromstring(blob)
    ref=root.find('./T[@n="category"]')
    if ref is None or ref.text!=str(BASE_CATEGORY):
        raise M37BuildError('Wrong interaction root category')
    ref.text=str(NEW_ROOT)
    return ET.tostring(root,encoding='utf-8')


def replace_stbl_label(blob):
    strings=parse_stbl(blob)
    if MAIN_LABEL not in strings:
        raise M37BuildError('Missing root label')
    strings[MAIN_LABEL]='MY HIGH SCHOOL (M37 TEST)'
    output=bytearray()
    size=0
    for key,text in sorted(strings.items()):
        data=text.encode('utf-8')
        output.extend(struct.pack('<IBH',key,0,len(data)))
        output.extend(data)
        size+=len(data)+1
    result=b'STBL'+struct.pack('<HBQ2sI',5,0,len(strings),b'\x00\x00',size)+bytes(output)
    if parse_stbl(result)!=strings:
        raise M37BuildError('STBL mismatch')
    return result


def transformed_resources():
    if (not 0<NEW_ROOT<2**31 or not 0<CATEGORY_ID<2**31
            or NEW_ROOT==CATEGORY_ID or BASE_CATEGORY<2**31):
        raise M37BuildError('Invalid root/child category identifiers')
    old=resources(m36_bad())
    new=[]
    touched={'root_tuning':0,'root_simdata':0,'child_tuning':0,
             'child_simdata':0,'root_interactions':0,'stbl':0}
    for typ,g,iid,blob in old:
        if typ==TYPE_CATEGORY and iid==BASE_CATEGORY:
            iid=NEW_ROOT
            blob=replace_root_tuning(blob)
            touched['root_tuning']+=1
        elif typ==TYPE_SIMDATA and g==SIMDATA_GROUP and iid==BASE_CATEGORY:
            iid=NEW_ROOT
            touched['root_simdata']+=1
        elif typ==TYPE_CATEGORY and iid==CATEGORY_ID:
            blob=replace_child_parent(blob)
            touched['child_tuning']+=1
        elif typ==TYPE_SIMDATA and g==SIMDATA_GROUP and iid==CATEGORY_ID:
            blob=replace_child_simdata(blob)
            touched['child_simdata']+=1
        elif typ==TYPE_INTERACTION:
            ref=ET.fromstring(blob).find('./T[@n="category"]')
            if ref is not None and ref.text==str(BASE_CATEGORY):
                blob=replace_interaction_root(blob)
                touched['root_interactions']+=1
        elif typ==TYPE_STBL:
            blob=replace_stbl_label(blob)
            touched['stbl']+=1
        new.append((typ,g,iid,blob))
    if any(touched[key]!=1 for key in ('root_tuning','root_simdata',
                                      'child_tuning','child_simdata')):
        raise M37BuildError('Missing single category tuning/SimData pair')
    if touched['root_interactions']<10 or touched['stbl']!=2:
        raise M37BuildError('Unexpected interaction/string table count {}'.format(touched))
    if len(set(row[:3] for row in new))!=len(new) or len(new)!=29:
        raise M37BuildError('Duplicate IDs or wrong resource inventory')
    ids={i for t,g,i,blob in new if t==TYPE_CATEGORY}
    if ids!={NEW_ROOT,CATEGORY_ID}:
        raise M37BuildError('Unexpected category mapping')
    # No remaining old root refs in XML categories or interactions.
    for typ,g,iid,blob in new:
        if typ in (TYPE_CATEGORY,TYPE_INTERACTION):
            node=ET.fromstring(blob)
            if node.get('s')==str(BASE_CATEGORY):
                raise M37BuildError('Stale original root tuning')
            for name in ('_parent','category'):
                field=node.find('./T[@n="{}"]'.format(name))
                if field is not None and field.text==str(BASE_CATEGORY):
                    raise M37BuildError('Stale old root reference')
    return new


def package_bytes():
    original=m36_bad()
    data=transformed_resources()
    header=bytearray(original[:96])
    payload=bytearray()
    index=bytearray(struct.pack('<I',0))
    for typ,g,iid,blob in data:
        comp=zlib.compress(blob,9)
        index.extend(ENTRY.pack(typ,g,iid>>32,iid&0xffffffff,
                                96+len(payload),len(comp)|0x80000000,
                                len(blob),0x5A42,1))
        payload.extend(comp)
    struct.pack_into('<I',header,0x24,len(data))
    struct.pack_into('<I',header,0x2c,len(index))
    struct.pack_into('<Q',header,0x40,96+len(payload))
    output=bytes(header+payload+index)
    if resources(output)!=data:
        raise M37BuildError('Invalid DBPF roundtrip')
    audit=inspect_bytes(output)
    if (audit['status']!='STATIC_GATE_PASSED' or
            audit['category_count']!=2 or audit['simdata_count']!=2):
        raise M37BuildError('Invalid pair schema/structure')
    return output


def release(folder):
    folder=Path(folder)
    folder.mkdir(parents=True,exist_ok=True)
    blob=package_bytes()
    (folder/PACK_NAME).write_bytes(blob)
    compile_m34_scripts(folder/SCRIPT_NAME)
    return {
      'status':'REQUIRES_MAC_GAME_VALIDATION',
      'new_root':NEW_ROOT,
      'child':CATEGORY_ID,
      'resources':len(resources(blob)),
      'sha256':hashlib.sha256(blob).hexdigest(),
    }


if __name__=='__main__':
    if len(sys.argv)!=2:
        raise SystemExit('Usage: python -m tooling.build_m37_small_root <outdir>')
    print(json.dumps(release(sys.argv[1]),indent=2))
