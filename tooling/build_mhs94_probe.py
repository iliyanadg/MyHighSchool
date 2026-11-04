"""M94 isolated Mac diagnostic release: M85 original package plus live EA job probe.

The package retains all original M85 resource payloads; only script archive
changes. It DOES NOT use the 6->16 classroom-capacity experimental overrides.
It DOES NOT activate M89/M90 invitation interception, so existing EA classroom
attendance is preserved pending evidence from the current game.
"""
import hashlib
import json
import py_compile
import sys
import tempfile
import zipfile
from pathlib import Path

from tooling.build_m58_diagnostic import SCRIPTS as M85_SCRIPTS
from tooling.build_m55_attendance_trial import package_bytes
from tooling.simdata_release_gate import inspect_bytes

ROOT=Path(__file__).resolve().parents[1]
PROBE=ROOT/'src'/'m94_runtime'/'mhs94_school_job_probe.py'
CUSTOM_UI=ROOT/'src'/'m94_runtime'/'mhs55_attendance_ui.py'
PKG='MHS_M94_FILTRI_LICEO_MAC_SOLA_LETTURA.package'
SCRIPT='MHS_M94_FILTRI_LICEO_MAC_SOLA_LETTURA.ts4script'

def script_sources():
    old=tuple(M85_SCRIPTS)
    replaced=tuple(CUSTOM_UI if p.name=='mhs55_attendance_ui.py' else p
                   for p in old)
    if len(old)!=32 or sum(1 for p in old
                          if p.name=='mhs55_attendance_ui.py')!=1:
        raise ValueError('M85 script graph unexpectedly changed')
    added=replaced+(PROBE,)
    if len(added)!=33 or len(set(p.name for p in added))!=33:
        raise ValueError('duplicate or missing modules')
    return added

def release(folder):
    if sys.version_info[:2]!=(3,7):
        raise RuntimeError('Sims 4 script bytecode requires Python 3.7')
    folder=Path(folder)
    folder.mkdir(parents=True,exist_ok=True)
    pkg=package_bytes()
    report=inspect_bytes(pkg)
    if report['status']!='STATIC_GATE_PASSED' or report['resource_count']!=63:
        raise ValueError('M85 package structural gate failed')
    (folder/PKG).write_bytes(pkg)
    with tempfile.TemporaryDirectory() as td:
        with zipfile.ZipFile(str(folder/SCRIPT),'w',zipfile.ZIP_DEFLATED) as z:
            for source in script_sources():
                compiled=Path(td)/(source.name+'c')
                py_compile.compile(str(source),cfile=str(compiled),doraise=True)
                z.write(str(compiled),arcname=source.name+'c')
    with zipfile.ZipFile(str(folder/SCRIPT)) as z:
        names=z.namelist()
        if len(names)!=33 or not all(z.read(n)[:4]==bytes((66,13,13,10))
                                   for n in names):
            raise ValueError('Python 3.7 script archive invalid')
        if not {'mhs94_school_job_probe.pyc','mhs55_attendance_ui.pyc',
                'mhs85_ui_bridge.pyc'}.issubset(names):
            raise ValueError('M94 report bridge or M85 missing')
    summary={'status':'M94_DIAGNOSTIC_ONLY_NOT_A_16_STUDENT_SOLUTION',
             'EA_guest_mutations':False,'EA_tuning_override_count':0,
             'package_resources':63,'compiled_modules':33,
             'sim_filter_observation':True,
             'game_test_required':True,
             'package_sha256':hashlib.sha256(pkg).hexdigest()}
    (folder/'MHS_M94_BUILD_REPORT.json').write_text(
        json.dumps(summary,indent=2,sort_keys=True))
    return summary

if __name__=='__main__':
    if len(sys.argv)!=2:
        raise SystemExit('Usage: python -m tooling.build_mhs94_probe dist_m94/')
    print(json.dumps(release(sys.argv[1]),indent=2))
