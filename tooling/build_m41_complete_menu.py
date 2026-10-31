"""M41 complete nested MY HIGH SCHOOL menu with user-provided EA schema checks.

User inspected current EA tuning and SimData XML for sim_Friendly (root)
and sim_SubCat_Friendly_Activities (child). Both specify:
  _collapsible False in XML, 0 in SimData.
  _parent root=0, child=<numeric parent tuning ID>.
  SimData PieMenuCategory schema hash=0xE2EAA141 and contains
  always_show_disabled_interactions.

The existing root/child SimData from M39 uses the same schema hash,
but inherited _collapsible=1 from the reference category. M41 sets
_collapsible=False/0 across ALL FIVE categories:
  MY HIGH SCHOOL -> Classe 1, Classe 2, optional Classe 3, Impostazioni.
The existing M39 Python test-gated menu state and M34 persistence
remain unchanged.

Game UI result is NOT guaranteed by passing structural tests. Save test
only, single pair in Mods, known-working M35B / M34 kept as fallback.
Does not yet implement pause-time writes or native UI confirmations.
"""
import hashlib
import json
import struct
import sys
import zlib
from pathlib import Path

from tooling.build_m39_conditional_menu import (
    package_bytes as build_m39,compile_scripts as compile_m39_scripts)
from tooling.build_m40_noncollapsible_parent import (
    category_xml,category_simdata)
from tooling.build_m38_three_class_menu import SETTINGS_CATEGORY,CATEGORY_IDS
from tooling.build_m37_small_root import NEW_ROOT
from tooling.build_m27_removal import ENTRY
from tooling.simdata_release_gate import resources,inspect_bytes

SCHEMA_HASH=0xE2EAA141
CATEGORY_TYPE=0x03E9D964
SIMDATA_TYPE=0x545AC67A
SIMDATA_GROUP=0x00E9D967
CATEGORY_TREE={NEW_ROOT,*CATEGORY_IDS,SETTINGS_CATEGORY}
PACK_NAME='MHS_M41_MENU_COMPLETO_EA_SCHEMA_TEST.package'
SCRIPT_NAME='MHS_M41_MENU_COMPLETO_EA_SCHEMA_TEST.ts4script'


class M41BuildError(ValueError):
    pass


def transformed_resources():
    source=resources(build_m39())
    transformed=[]
    touched=set()
    for typ,group,iid,blob in source:
        if typ==CATEGORY_TYPE:
            if iid not in CATEGORY_TREE:
                raise M41BuildError('Unknown category ID')
            blob=category_xml(blob)
            touched.add(('xml',iid))
        elif typ==SIMDATA_TYPE:
            if iid not in CATEGORY_TREE or group!=SIMDATA_GROUP:
                raise M41BuildError('Unknown SimData TGI')
            # EA 2026 schema matches the existing binary, including
            # 'always_show_disabled_interactions'. Do not blindly patch a
            # SimData if the schema changes in a future game update.
            if (struct.pack('<I',SCHEMA_HASH) not in blob
                    or b'always_show_disabled_interactions' not in blob):
                raise M41BuildError('Unexpected outdated PieMenuCategory schema')
            blob=category_simdata(blob)
            touched.add(('simdata',iid))
        transformed.append((typ,group,iid,blob))
    expected={('xml',iid) for iid in CATEGORY_TREE}|{
        ('simdata',iid) for iid in CATEGORY_TREE}
    if touched!=expected:
        raise M41BuildError('Expected exactly five category tuning/SimData pairs')
    if len(transformed)!=35:
        raise M41BuildError('Expected 35 resource entries')
    for old,new in zip(source,transformed):
        if old[:3]!=new[:3]:
            raise M41BuildError('Changed resource key')
        if old[0] not in (CATEGORY_TYPE,SIMDATA_TYPE) and old!=new:
            raise M41BuildError('Changed unrelated action, script or localization')
    return transformed


def package_bytes():
    old=build_m39()
    rows=transformed_resources()
    header=bytearray(old[:96])
    payload=bytearray()
    index=bytearray(struct.pack('<I',0))
    for typ,group,iid,blob in rows:
        packed=zlib.compress(blob,9)
        index.extend(ENTRY.pack(typ,group,iid>>32,iid&0xffffffff,
                                96+len(payload),len(packed)|0x80000000,
                                len(blob),0x5A42,1))
        payload.extend(packed)
    struct.pack_into('<I',header,0x24,len(rows))
    struct.pack_into('<I',header,0x2c,len(index))
    struct.pack_into('<Q',header,0x40,96+len(payload))
    built=bytes(header+payload+index)
    if resources(built)!=rows:
        raise M41BuildError('DBPF resource roundtrip mismatch')
    audit=inspect_bytes(built)
    if (audit['status']!='STATIC_GATE_PASSED' or
            audit['category_count']!=5 or
            audit['simdata_count']!=5):
        raise M41BuildError('Static category gate failed')
    return built


def release(folder):
    folder=Path(folder)
    folder.mkdir(parents=True,exist_ok=True)
    blob=package_bytes()
    (folder/PACK_NAME).write_bytes(blob)
    compile_m39_scripts(folder/SCRIPT_NAME)
    return {'status':'MAC_IN_GAME_TEST_REQUIRED',
            'categories':5,
            'simdata_schema':'0xE2EAA141',
            'resource_count':len(resources(blob)),
            'sha256':hashlib.sha256(blob).hexdigest()}


if __name__=='__main__':
    if len(sys.argv)!=2:
        raise SystemExit('Usage: python -m tooling.build_m41_complete_menu <outdir>')
    print(json.dumps(release(sys.argv[1]),indent=2))
