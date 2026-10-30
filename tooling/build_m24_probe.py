"""Build M24 diagnostic DBPF: M1 UI + ONLY confirmation class substitution.

Requires existing verified Lot51 binary category from project.
No save-state writes. Do not claim that this has been tested in-game.
"""
import collections
import hashlib
from pathlib import Path
import struct
import xml.etree.ElementTree as ET
import zlib

from tooling.build_m1_offline import build_m1_bytes
from tooling.simdata_release_gate import resources, inspect_bytes

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'src' / 'm24_probe' / 'mhs24_diagnostic.py'
TYPE_INTERACTION = 0xE882D22F
REPLACEMENTS = {13813934116852558422: 'MHS24ProbeConfirmClass1',
                13813933017340930211: 'MHS24ProbeConfirmClass2'}
ENTRY = struct.Struct('<IIIIIIIHH')
OUTPUT_PACKAGE = 'MHS_M24_PICKEDSIM_SOLO_LETTURA.package'
OUTPUT_SCRIPT = 'MHS_M24_PICKEDSIM_SOLO_LETTURA.ts4script'


class DiagnosticBuildError(ValueError):
    pass


def replace_confirms(entries):
    changed = []
    result = []
    for typ, group, instance, payload in entries:
        if typ == TYPE_INTERACTION and instance in REPLACEMENTS:
            root = ET.fromstring(payload)
            if root.get('c') != 'ImmediateSuperInteraction' or root.get('m') != 'interactions.base.immediate_interaction':
                raise DiagnosticBuildError('Confirmation source class not as expected')
            root.set('c', REPLACEMENTS[instance])
            root.set('m', 'mhs24_diagnostic')
            payload = ET.tostring(root, encoding='utf-8', xml_declaration=True)
            changed.append(instance)
        result.append((typ, group, instance, payload))
    if set(changed) != set(REPLACEMENTS):
        raise DiagnosticBuildError('Missing one or both confirmations')
    return result


def build_package():
    orig = build_m1_bytes()
    entries = replace_confirms(resources(orig))
    header = bytearray(orig[:96])
    if (header[:4] != b'DBPF' or struct.unpack_from('<I', header, 0x3C)[0] != 3):
        raise DiagnosticBuildError('Invalid base DBPF header')
    data = bytearray()
    idx = bytearray(struct.pack('<I', 0))
    for typ, group, instance, payload in entries:
        compressed = zlib.compress(payload, 9)
        offset = 96 + len(data)
        data.extend(compressed)
        idx.extend(ENTRY.pack(typ, group, instance >> 32, instance & 0xFFFFFFFF,
                              offset, len(compressed) | 0x80000000,
                              len(payload), 0x5A42, 1))
    at = 96 + len(data)
    struct.pack_into('<I', header, 0x24, len(entries))
    struct.pack_into('<I', header, 0x2C, len(idx))
    struct.pack_into('<Q', header, 0x40, at)
    candidate = bytes(header + data + idx)
    if resources(candidate) != entries:
        raise DiagnosticBuildError('Roundtrip of M24 DBPF failed')
    if inspect_bytes(candidate)['status'] != 'STATIC_GATE_PASSED':
        raise DiagnosticBuildError('Category + SimData gate failed')
    return candidate


def verify_only_two_tuning_changes():
    before = resources(build_m1_bytes())
    after = resources(build_package())
    changed = []
    for old, new in zip(before, after):
        if old[:3] != new[:3]:
            raise DiagnosticBuildError('Resource TGI changed unexpectedly')
        if old[3] != new[3]:
            changed.append(new[2])
    if set(changed) != set(REPLACEMENTS):
        raise DiagnosticBuildError('Unexpected payloads changed')
    return True


def compile_script(output):
    """Must be executed under real CPython 3.7, not modern Python."""
    import importlib.util
    import py_compile
    import sys
    import tempfile
    import zipfile
    if sys.version_info[:2] != (3, 7) or importlib.util.MAGIC_NUMBER != bytes((0x42, 0x0D, 0x0D, 0x0A)):
        raise DiagnosticBuildError('Serve Python 3.7 per compilare ts4script')
    with tempfile.TemporaryDirectory() as temp:
        pyc = Path(temp) / 'mhs24_diagnostic.pyc'
        py_compile.compile(str(SOURCE), cfile=str(pyc), doraise=True)
        if pyc.read_bytes()[:4] != importlib.util.MAGIC_NUMBER:
            raise DiagnosticBuildError('PYC compilato con magic errato')
        with zipfile.ZipFile(str(output), 'w', zipfile.ZIP_DEFLATED) as archive:
            archive.write(str(pyc), arcname='mhs24_diagnostic.pyc')
    with zipfile.ZipFile(str(output)) as archive:
        if archive.namelist() != ['mhs24_diagnostic.pyc']:
            raise DiagnosticBuildError('Unexpected ts4script inventory')


def release(directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    if not verify_only_two_tuning_changes():
        raise DiagnosticBuildError('Verification failed')
    binary = build_package()
    (directory / OUTPUT_PACKAGE).write_bytes(binary)
    compile_script(directory / OUTPUT_SCRIPT)
    return {'package_sha256': hashlib.sha256(binary).hexdigest(),
            'package_bytes': len(binary),
            'changed_resources': list(REPLACEMENTS),
            'status': 'DIAGNOSTIC_NEEDS_GAME_TEST'}


if __name__ == '__main__':
    import json
    import sys
    if len(sys.argv) != 2:
        raise SystemExit('Uso: python -m tooling.build_m24_probe <cartella_destinazione>')
    print(json.dumps(release(sys.argv[1]), indent=2))
