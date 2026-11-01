"""M58 Mac read-only probe build based on the verified M57d package graph.

Preserves the proven 63-resource package byte-for-byte; only the script
archive adds the mhs58_situation_probe module and diagnostic UI integration.
"""
import hashlib
import json
import py_compile
import sys
import tempfile
import zipfile
from pathlib import Path

from tooling.build_m55_attendance_trial import (
    package_bytes, SCRIPTS as M57_SCRIPTS)
from tooling.simdata_release_gate import inspect_bytes

ROOT=Path(__file__).resolve().parents[1]
PROBE=ROOT/'src'/'m58_selection'/'mhs58_situation_probe.py'
PACKAGE='MHS_M58_DIAGNOSTICA_SITUAZIONI_MAC_TEST.package'
SCRIPT='MHS_M58_DIAGNOSTICA_SITUAZIONI_MAC_TEST.ts4script'
M85=(ROOT/'src'/'m85_diagnostics'/'mhs85_reconcile.py',
     ROOT/'src'/'m85_diagnostics'/'mhs85_live_snapshot.py',
     ROOT/'src'/'m85_diagnostics'/'mhs85_ui_bridge.py')
SCRIPTS=tuple(M57_SCRIPTS)+(PROBE,
    ROOT/'src'/'m58_selection'/'mhs61_guest_adapter.py',
    ROOT/'src'/'m58_selection'/'mhs61_pilot_command.py')+M85


def release(folder):
    if sys.version_info[:2]!=(3,7):
        raise RuntimeError('Sims 4 script archive requires Python 3.7')
    folder=Path(folder)
    folder.mkdir(parents=True,exist_ok=True)
    blob=package_bytes()
    assert inspect_bytes(blob)['status']=='STATIC_GATE_PASSED'
    assert len(SCRIPTS)==32
    assert len(set(p.name for p in SCRIPTS))==32
    (folder/PACKAGE).write_bytes(blob)
    with tempfile.TemporaryDirectory() as temp:
        with zipfile.ZipFile(str(folder/SCRIPT),'w',zipfile.ZIP_DEFLATED) as archive:
            for source in SCRIPTS:
                target=Path(temp)/(source.name+'c')
                py_compile.compile(str(source),cfile=str(target),doraise=True)
                archive.write(str(target),arcname=source.name+'c')
    with zipfile.ZipFile(str(folder/SCRIPT)) as archive:
        names=archive.namelist()
        assert len(names)==32
        assert 'mhs58_situation_probe.pyc' in names
        assert 'mhs61_pilot_command.pyc' in names
        assert 'mhs85_ui_bridge.pyc' in names
        assert all(archive.read(n)[:4]==bytes((66,13,13,10)) for n in names)
    return {'status':'DIAGNOSTIC_ONLY_MAC_GAME_TEST_REQUIRED',
            'package_resources':63,
            'script_modules':len(SCRIPTS),
            'EA_guest_list_mutation':False,
            'auto_situation_probe_on_school_zone_load':True,
            'menu':'M55 - Consulta presenze automatiche',
            'package_sha256':hashlib.sha256(blob).hexdigest()}


if __name__=='__main__':
    if len(sys.argv)!=2:
        raise SystemExit('Usage: python -m tooling.build_m58_diagnostic <output folder>')
    print(json.dumps(release(sys.argv[1]),indent=2))
