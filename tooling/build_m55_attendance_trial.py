"""M55 Mac trial: add ONE explicitly triggered attendance affordance.

Keep all 62 M54 resources identical except the injector snippet and the two
localization tables; append one interaction under the already working Class 1
Lot51 category. No override of EA school attendance and no additional SimData.
"""
import hashlib
import importlib.util
import json
import py_compile
import struct
import sys
import tempfile
import xml.etree.ElementTree as ET
import zipfile
import zlib
from pathlib import Path

from tooling.build_m53_staff_management import (
    package_bytes as build_m54_package, SCRIPTS as M54_SCRIPTS)
from tooling.build_m27_removal import TYPE_INTERACTION, TYPE_SNIPPET, TYPE_STBL, ENTRY, fnv64_highbit
from tooling.build_m30_nested_menu import CATEGORY_IDS
from tooling.m1_links_and_strings import parse_stbl
from tooling.simdata_release_gate import inspect_bytes, resources

ROOT = Path(__file__).resolve().parents[1]
SLOT = ROOT/'src'/'m2_registry'/'mhs56_slot_identity.py'
CORE = ROOT/'src'/'m55_attendance'/'mhs55_attendance_core.py'
AUTO = ROOT/'src'/'m55_attendance'/'mhs55_attendance_auto.py'
UI = ROOT/'src'/'m55_attendance'/'mhs55_attendance_ui.py'
MANIFEST = ROOT/'src'/'m57_selection'/'mhs57_school_manifest.py'
POLICY = ROOT/'src'/'m57_selection'/'mhs57_filter_policy.py'
FILTER_RUNTIME = ROOT/'src'/'m57_selection'/'mhs57_filter_runtime.py'
SCRIPTS = tuple(M54_SCRIPTS) + (SLOT, MANIFEST, POLICY, FILTER_RUNTIME, CORE, AUTO, UI)
ACTION = 'Iliyana:MHS55_Attendance_One'
ACTION_ID = fnv64_highbit(ACTION)
LABEL_ID = 0x5A895200
PACKAGE = 'MHS_M57B_FILTRO_SCUOLA_FIX_CONFLITTI_MAC_TEST.package'
SCRIPT = 'MHS_M57B_FILTRO_SCUOLA_FIX_CONFLITTI_MAC_TEST.ts4script'


class M55BuildError(ValueError):
    pass


def _stbl(raw, locale):
    old = parse_stbl(raw)
    if LABEL_ID in old:
        raise M55BuildError('STBL key already exists')
    value = ('M55 - Consulta presenze automatiche' if locale == 'it'
             else 'M55 - View automatic school attendance')
    table = dict(old)
    table[LABEL_ID] = value
    body = bytearray()
    byte_count = 0
    for key, string in sorted(table.items()):
        encoded = string.encode('utf-8')
        body.extend(struct.pack('<IBH', key, 0, len(encoded)))
        body.extend(encoded)
        byte_count += len(encoded)+1
    out = (b'STBL' + struct.pack('<HBQ2sI', 5, 0, len(table), b'\0\0', byte_count)
           + bytes(body))
    if parse_stbl(out) != table:
        raise M55BuildError('STBL roundtrip failed')
    return out


def _inject(raw):
    root = ET.fromstring(raw)
    matches = root.find('./L[@n="add_interactions_to_objects"]/U/L[@n="_super_affordances"]')
    if matches is None:
        raise M55BuildError('Verified M54 injector not found')
    existing = {int(e.text) for e in matches.findall('T')}
    if ACTION_ID in existing:
        raise M55BuildError('Duplicate M55 interaction')
    ET.SubElement(matches, 'T').text = str(ACTION_ID)
    return ET.tostring(root, encoding='utf-8')


def _interaction(template):
    root = ET.fromstring(template)
    if root.get('c') != 'MHS39_MHS27RemoveClass1':
        raise M55BuildError('Wrong original immediate tuning class')
    root.set('m', 'mhs55_attendance_ui')
    root.set('c', 'MHS55TryOne')
    root.set('n', ACTION)
    root.set('s', str(ACTION_ID))
    category = root.find('./T[@n="category"]')
    title = root.find('./T[@n="display_name"]')
    if category is None or title is None:
        raise M55BuildError('Missing action label or category')
    category.text = str(CATEGORY_IDS[0])
    title.text = '0x{:08X}'.format(LABEL_ID)
    return ET.tostring(root, encoding='utf-8')


def transformed_resources():
    existing = resources(build_m54_package())
    if len(existing) != 62 or len(SCRIPTS) != 26:
        raise M55BuildError('Unexpected M54 baseline')
    source = next((raw for typ, group, iid, raw in existing
                   if typ == TYPE_INTERACTION and
                   ET.fromstring(raw).get('c') == 'MHS39_MHS27RemoveClass1'), None)
    if source is None:
        raise M55BuildError('Known-good Class 1 interaction not found')
    altered = []
    changed = []
    locales = set()
    for typ, group, iid, raw in existing:
        if typ == TYPE_SNIPPET:
            raw = _inject(raw)
            changed.append((typ, group, iid))
        elif typ == TYPE_STBL:
            locale = {0:'en', 11:'it'}.get(iid >> 56)
            if locale is None:
                raise M55BuildError('Unsupported STBL language')
            raw = _stbl(raw, locale)
            locales.add(locale)
            changed.append((typ, group, iid))
        altered.append((typ, group, iid, raw))
    altered.append((TYPE_INTERACTION, 0, ACTION_ID, _interaction(source)))
    if (len(changed) != 3 or locales != {'en', 'it'} or
            len(altered) != 63 or
            len({line[:3] for line in altered}) != len(altered)):
        raise M55BuildError('M55 resource graph incorrect')
    for old, new in zip(existing, altered[:62]):
        if old[:3] != new[:3]:
            raise M55BuildError('Changed existing resource key')
        if old[:3] not in changed and old != new:
            raise M55BuildError('Unexpected M54 resource mutation')
    return altered


def package_bytes():
    original = build_m54_package()
    entries = transformed_resources()
    header = bytearray(original[:96])
    payload = bytearray()
    index = bytearray(struct.pack('<I', 0))
    for typ, group, iid, raw in entries:
        compressed = zlib.compress(raw, 9)
        index.extend(ENTRY.pack(typ, group, iid >> 32, iid & 0xffffffff,
                                96+len(payload), len(compressed)|0x80000000,
                                len(raw), 0x5A42, 1))
        payload.extend(compressed)
    struct.pack_into('<I', header, 0x24, len(entries))
    struct.pack_into('<I', header, 0x2c, len(index))
    struct.pack_into('<Q', header, 0x40, 96+len(payload))
    blob = bytes(header+payload+index)
    if resources(blob) != entries:
        raise M55BuildError('DBPF failed readback')
    gate = inspect_bytes(blob)
    if (gate['status'] != 'STATIC_GATE_PASSED' or
            gate['category_count'] != 10 or gate['simdata_count'] != 10 or
            gate['resource_count'] != 63):
        raise M55BuildError('M54 Lot51 category graph regressed')
    return blob


def compile_scripts(dest):
    if sys.version_info[:2] != (3, 7) or importlib.util.MAGIC_NUMBER != bytes((66,13,13,10)):
        raise M55BuildError('Python 3.7 bytecode required by The Sims 4')
    with tempfile.TemporaryDirectory() as tmp:
        with zipfile.ZipFile(str(dest), 'w', zipfile.ZIP_DEFLATED) as z:
            for src in SCRIPTS:
                compiled = Path(tmp)/(src.name+'c')
                py_compile.compile(str(src), cfile=str(compiled), doraise=True)
                z.write(str(compiled), arcname=src.name+'c')


def release(directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    blob = package_bytes()
    (directory/PACKAGE).write_bytes(blob)
    compile_scripts(directory/SCRIPT)
    return {'status':'MAC_GAME_TEST_REQUIRED',
            'M54_original_resources_preserved':59,
            'existing_resources_with_only_new_localization_or_injector':3,
            'new_interactions':1,'resource_count':63,
            'script_modules':len(SCRIPTS),
            'automatic_full_roster_dispatch':True,
            'school_gate_diagnostic':True,
            'stable_save_guid_travel_guard':True,
            'pre_spawn_EA_filter_constraints':True,
            'legacy_additional_invites_disabled':True,
            'read_only_active_teens_roster_count':True,
            'batch_size_per_five_sim_minutes':3,
            'max_roster_students':24,
            'EA_attendance_requires_in_game_validation':True,
            'package_sha256':hashlib.sha256(blob).hexdigest()}


if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise SystemExit('Usage: python -m tooling.build_m55_attendance_trial <output_dir>')
    print(json.dumps(release(sys.argv[1]), indent=2))
