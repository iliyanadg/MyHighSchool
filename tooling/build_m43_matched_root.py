"""M43 isolated category identity-coherence fix on top of M42.

M41 user screenshot: parent MY HIGH SCHOOL appears separately from all
children even though both XML+SimData carry _parent IDs. M37 changed the
root instance ID to the 31-bit hash of 'Iliyana:MHS_Root_Small_v37'
but LEFT its XML n= and SimData instance name as 'Iliyana:MHS_MainMenu'.

M43 uses a single 31-bit ID generated from the ACTUAL root instance name
'Iliyana:MHS_MainMenu' and rewrites every reference consistently:
root tuning+SimData TGI, category root XML s, child XML+SimData _parent,
and any root interaction category links. Other actions unchanged.

This is a precise hypothesis, NOT a proven runtime fix for nested categories.
Contains prior M42 TestResult(FALSE) fix and two/three-class transfer gate.
"""
import hashlib
import json
import struct
import sys
import xml.etree.ElementTree as ET
import zlib
from pathlib import Path

from tooling.build_m42_safe_menu import (
    package_bytes as build_m42,NEW_ROOT,CATEGORY_TYPE,SIMDATA_TYPE,
    SIMDATA_GROUP,TYPE_STBL)
from tooling.build_m37_small_root import ROOT_NAME
from tooling.build_m30_nested_menu import category_id
from tooling.build_m27_removal import ENTRY,TYPE_INTERACTION
from tooling.build_m39_conditional_menu import compile_scripts
from tooling.simdata_release_gate import resources,inspect_bytes

MATCHED_ROOT=category_id(ROOT_NAME)
PACK_NAME='MHS_M43_MENU_GERARCHIA_E_FIX_TEST.package'
SCRIPT_NAME='MHS_M43_MENU_GERARCHIA_E_FIX_TEST.ts4script'

class M43BuildError(ValueError):
    pass


def transform():
    original=resources(build_m42())
    category_ids={i for t,g,i,v in original if t==CATEGORY_TYPE}
    if not(0<MATCHED_ROOT<2**31 and MATCHED_ROOT!=NEW_ROOT
           and MATCHED_ROOT not in category_ids
           and len(category_ids)==5):
        raise M43BuildError('Root replacement has an ID collision')
    rows=[]
    changed={'root_tuning':0,'root_simdata':0,
             'child_xml':0,'child_simdata':0,'root_actions':0}
    for typ,group,iid,data in original:
        if typ==CATEGORY_TYPE:
            node=ET.fromstring(data)
            if iid==NEW_ROOT:
                if (node.get('s')!=str(NEW_ROOT)
                        or node.get('n')!=ROOT_NAME
                        or node.find('./T[@n="_parent"]') is not None):
                    raise M43BuildError('Unexpected existing root XML')
                node.set('s',str(MATCHED_ROOT))
                iid=MATCHED_ROOT
                changed['root_tuning']+=1
            else:
                parent=node.find('./T[@n="_parent"]')
                if parent is None or parent.text!=str(NEW_ROOT):
                    raise M43BuildError('Unexpected child parent')
                parent.text=str(MATCHED_ROOT)
                changed['child_xml']+=1
            data=ET.tostring(node,encoding='utf-8')
        elif typ==SIMDATA_TYPE:
            if group!=SIMDATA_GROUP or len(data)!=475 or data[:4]!=b'DATA':
                raise M43BuildError('Unexpected SimData format')
            if iid==NEW_ROOT:
                if (struct.unpack_from('<Q',data,0x5c)[0]!=0 or
                        ROOT_NAME.encode('ascii') not in data):
                    raise M43BuildError('Root SimData does not match its name')
                iid=MATCHED_ROOT
                changed['root_simdata']+=1
            else:
                if struct.unpack_from('<Q',data,0x5c)[0]!=NEW_ROOT:
                    raise M43BuildError('Child SimData parent did not match old root')
                new=bytearray(data)
                struct.pack_into('<Q',new,0x5c,MATCHED_ROOT)
                data=bytes(new)
                changed['child_simdata']+=1
        elif typ==TYPE_INTERACTION:
            node=ET.fromstring(data)
            category=node.find('./T[@n="category"]')
            if category is not None and category.text==str(NEW_ROOT):
                category.text=str(MATCHED_ROOT)
                data=ET.tostring(node,encoding='utf-8')
                changed['root_actions']+=1
        rows.append((typ,group,iid,data))
    if (len(rows)!=35 or len(set(z[:3] for z in rows))!=35
            or changed['root_tuning']!=1
            or changed['root_simdata']!=1
            or changed['child_xml']!=4
            or changed['child_simdata']!=4
            or changed['root_actions']<2):
        raise M43BuildError('Unexpected resource changes: {}'.format(changed))
    for typ,group,iid,data in rows:
        if typ in (CATEGORY_TYPE,TYPE_INTERACTION):
            node=ET.fromstring(data)
            for key in ('category','_parent'):
                ref=node.find('./T[@n="{}"]'.format(key))
                if ref is not None and ref.text==str(NEW_ROOT):
                    raise M43BuildError('Old root ID leaked in XML')
    return rows


def package_bytes():
    source=build_m42()
    rows=transform()
    header=bytearray(source[:96])
    payload=bytearray()
    index=bytearray(struct.pack('<I',0))
    for t,g,i,data in rows:
        z=zlib.compress(data,9)
        index.extend(ENTRY.pack(t,g,i>>32,i&0xffffffff,
                                96+len(payload),len(z)|0x80000000,
                                len(data),0x5A42,1))
        payload.extend(z)
    struct.pack_into('<I',header,0x24,len(rows))
    struct.pack_into('<I',header,0x2c,len(index))
    struct.pack_into('<Q',header,0x40,96+len(payload))
    package=bytes(header+payload+index)
    if resources(package)!=rows:
        raise M43BuildError('DBPF roundtrip failed')
    check=inspect_bytes(package)
    if (check['status']!='STATIC_GATE_PASSED' or
            check['category_count']!=5 or check['simdata_count']!=5):
        raise M43BuildError('Invalid package category resources')
    return package


def release(folder):
    folder=Path(folder)
    folder.mkdir(parents=True,exist_ok=True)
    data=package_bytes()
    (folder/PACK_NAME).write_bytes(data)
    compile_scripts(folder/SCRIPT_NAME)
    return {'status':'GAME_VALIDATION_REQUIRED',
            'old_root':NEW_ROOT,'name_coherent_root':MATCHED_ROOT,
            'resource_count':len(resources(data)),
            'sha256':hashlib.sha256(data).hexdigest()}


if __name__=='__main__':
    if len(sys.argv)!=2:
        raise SystemExit('Usage: python -m tooling.build_m43_matched_root <outdir>')
    print(json.dumps(release(sys.argv[1]),indent=2))
