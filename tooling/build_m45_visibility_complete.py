"""M45: preserve proven M44 Lot51 nested menu; gate 3 missed SimPickers.

The M44 Mac screenshots show the hierarchy is correct and settings persist,
but all three "Prepara iscrizione Classe N" SimPickerInteraction actions
are excluded from M39's 19 gated affordances. That kept category N visible
while MY HIGH SCHOOL was disabled or Class 3 was off.

This builder REPRODUCES the four original Lot51 SimData resource bytes
found to fix the hierarchy (from M43 + verified 12-byte differences),
then changes ONLY the 'm'/'c' fields of the three SimPicker interactions.
Every class's picker runs the same existing visibility mixin as all other
actions, retaining its original SimPickerInteraction behavior.

NO roster, Sim data, labels, menu categories, parent references,
save files or school attendance tuning are modified.
"""
import hashlib
import json
import struct
import sys
from pathlib import Path
import xml.etree.ElementTree as ET
import zlib

from tooling.build_m43_matched_root import package_bytes as build_m43,MATCHED_ROOT
from tooling.build_m30_nested_menu import ENROLL_IDS,CATEGORY_IDS
from tooling.build_m38_three_class_menu import SETTINGS_CATEGORY
from tooling.build_m39_conditional_menu import compile_scripts
from tooling.build_m27_removal import ENTRY,TYPE_INTERACTION
from tooling.build_m41_complete_menu import CATEGORY_TYPE,SIMDATA_TYPE,SIMDATA_GROUP
from tooling.simdata_release_gate import resources,inspect_bytes

PACK_NAME='MHS_M45_MENU_VISIBILITA_CORRETTA_TEST.package'
SCRIPT_NAME='MHS_M45_MENU_VISIBILITA_CORRETTA_TEST.ts4script'

# Verified byte-for-byte differences from 31 Oct 2026 Lot51 exports:
# class 1 header 56 3e 67 7c, class 2 0f 39 67 79,
# class 3 bc 3a 67 7a, Settings 9e 7b 59 1e.
LOT51_HEADERS={
    CATEGORY_IDS[0]:bytes.fromhex('563e677c'),
    CATEGORY_IDS[1]:bytes.fromhex('0f396779'),
    CATEGORY_IDS[2]:bytes.fromhex('bc3a677a'),
    SETTINGS_CATEGORY:bytes.fromhex('9e7b591e'),
}
PICKERS={inst:i+1 for i,inst in enumerate(ENROLL_IDS)}


class M45BuildError(ValueError):
    pass


def transformed_resources():
    old=resources(build_m43())
    rows=[]
    changed_picker=set()
    changed_simdata=set()
    for typ,group,iid,raw in old:
        if typ==SIMDATA_TYPE and group==SIMDATA_GROUP and iid in LOT51_HEADERS:
            if (len(raw)!=475 or raw[:4]!=b'DATA' or
                    raw[0x24:0x28]!=bytes.fromhex('03e22780') or
                    struct.unpack_from('<Q',raw,0x5c)[0]!=MATCHED_ROOT):
                raise M45BuildError('M43 SimData base does not match known template')
            new=bytearray(raw)
            new[0x24:0x28]=LOT51_HEADERS[iid]
            struct.pack_into('<Q',new,0x5c,MATCHED_ROOT<<32)
            raw=bytes(new)
            changed_simdata.add(iid)
        elif typ==TYPE_INTERACTION and iid in PICKERS:
            node=ET.fromstring(raw)
            if (node.get('m')!='interactions.base.picker_interaction' or
                    node.get('c')!='SimPickerInteraction'):
                raise M45BuildError('Old enrollment picker no longer matches tuning')
            target=node.find('./T[@n="category"]')
            if target is None or target.text!=str(CATEGORY_IDS[PICKERS[iid]-1]):
                raise M45BuildError('Enrollment picker no longer points to its class')
            node.set('m','mhs39_visibility_ui')
            node.set('c','MHS45ChooseClass{}'.format(PICKERS[iid]))
            raw=ET.tostring(node,encoding='utf-8')
            changed_picker.add(iid)
        rows.append((typ,group,iid,raw))
    if (changed_picker!=set(PICKERS) or
            changed_simdata!=set(LOT51_HEADERS) or len(rows)!=35):
        raise M45BuildError('Unexpected action / SimData inventory')
    if len({row[:3] for row in rows})!=35:
        raise M45BuildError('Duplicate DBPF TGI')
    for typ,g,iid,raw in rows:
        if typ==TYPE_INTERACTION:
            node=ET.fromstring(raw)
            cat=node.find('./T[@n="category"]')
            # 3 backstage confirm tunings have no category and are not
            # rendered directly in the mailbox. Every visible action must
            # now use the visibility mixin.
            if cat is not None and cat.text in tuple(map(str,CATEGORY_IDS))+(str(MATCHED_ROOT),str(SETTINGS_CATEGORY)):
                if node.get('m')!='mhs39_visibility_ui':
                    raise M45BuildError('Unguarded mailbox affordance: '+str(node.get('n')))
    return rows


def package_bytes():
    old=build_m43()
    rows=transformed_resources()
    header=bytearray(old[:96])
    payload=bytearray()
    index=bytearray(struct.pack('<I',0))
    for typ,group,iid,data in rows:
        packed=zlib.compress(data,9)
        index.extend(ENTRY.pack(typ,group,iid>>32,iid&0xffffffff,
                                96+len(payload),len(packed)|0x80000000,
                                len(data),0x5A42,1))
        payload.extend(packed)
    struct.pack_into('<I',header,0x24,len(rows))
    struct.pack_into('<I',header,0x2c,len(index))
    struct.pack_into('<Q',header,0x40,96+len(payload))
    blob=bytes(header+payload+index)
    if resources(blob)!=rows:
        raise M45BuildError('DBPF archive failed roundtrip')
    audit=inspect_bytes(blob)
    if (audit['status']!='STATIC_GATE_PASSED' or
            audit['category_count']!=5 or audit['simdata_count']!=5):
        raise M45BuildError('Five category/SimData pairs not preserved')
    return blob


def release(folder):
    folder=Path(folder)
    folder.mkdir(parents=True,exist_ok=True)
    blob=package_bytes()
    (folder/PACK_NAME).write_bytes(blob)
    compile_scripts(folder/SCRIPT_NAME)
    return {
        'status':'MAC_GAME_TEST_REQUIRED',
        'package_sha256':hashlib.sha256(blob).hexdigest(),
        'resources':35,
        'Lot51_SimData_pairs':5,
        'guarded_visible_affordances':19,
        'guarded_enrollment_pickers':3,
        'scripts':15,
    }


if __name__=='__main__':
    if len(sys.argv)!=2:
        raise SystemExit('Usage: python -m tooling.build_m45_visibility_complete <outdir>')
    print(json.dumps(release(sys.argv[1]),indent=2))
