"""M101 opt-in one original EA school slot Mac test.

The original M99 63 DBPF resources are identical; 6 pure/controller
modules added + UI import overlay. No automatic arm, no extra creation.
A user must arm it at home before the day's first EA school situation.
"""
import hashlib
import importlib.util
import json
import py_compile
import sys
import tempfile
import zipfile
from pathlib import Path

from tooling.build_mhs99_trace import script_sources as m99_scripts
from tooling.build_m55_attendance_trial import package_bytes
from tooling.simdata_release_gate import inspect_bytes

ROOT=Path(__file__).resolve().parents[1]
UI=ROOT/'src'/'m101_original_slot'/'mhs55_attendance_ui.py'
ADDED=(
    ROOT/'src'/'m58_selection'/'mhs58_guest_policy.py',
    ROOT/'src'/'m88_selection'/'mhs88_replace_guest.py',
    ROOT/'src'/'m89_selection'/'mhs89_precreate_hook.py',
    ROOT/'src'/'m100_precreate'/'mhs100_one_slot_policy.py',
    ROOT/'src'/'m101_original_slot'/'mhs101_original_slot_gate.py',
    ROOT/'src'/'m101_original_slot'/'mhs101_original_slot_runtime.py',
)
PKG='MHS_M101B_FILTRO_EA_DIAGNOSTICA_MAC_TEST.package'
SCRIPT='MHS_M101B_FILTRO_EA_DIAGNOSTICA_MAC_TEST.ts4script'
COUNT=40

def script_sources():
    original=tuple(m99_scripts())
    if len(original)!=34 or sum(p.name=='mhs55_attendance_ui.py'
                               for p in original)!=1:
        raise RuntimeError('M99 original script graph changed')
    replaced=tuple(UI if p.name=='mhs55_attendance_ui.py' else p
                   for p in original)
    all_sources=replaced+ADDED
    if len(all_sources)!=COUNT or len(set(p.name for p in all_sources))!=COUNT:
        raise RuntimeError('M101 duplicate or missing script')
    return all_sources

def release(folder):
    if (sys.version_info[:2]!=(3,7) or
            importlib.util.MAGIC_NUMBER!=bytes((66,13,13,10))):
        raise RuntimeError('Mac The Sims 4 requires Python 3.7 bytecode')
    root=Path(folder)
    root.mkdir(parents=True,exist_ok=True)
    package=package_bytes()
    report=inspect_bytes(package)
    if report['status']!='STATIC_GATE_PASSED' or report['resource_count']!=63:
        raise RuntimeError('M99 original 63 DBPF resources changed')
    (root/PKG).write_bytes(package)
    with tempfile.TemporaryDirectory() as td:
        with zipfile.ZipFile(str(root/SCRIPT),'w',zipfile.ZIP_DEFLATED) as z:
            for source in script_sources():
                compiled=Path(td)/(source.name+'c')
                py_compile.compile(str(source),cfile=str(compiled),doraise=True)
                z.write(str(compiled),arcname=source.name+'c')
    with zipfile.ZipFile(str(root/SCRIPT)) as z:
        files=z.namelist()
        if len(files)!=COUNT or not all(z.read(name)[:4]==bytes((66,13,13,10))
                                   for name in files):
            raise RuntimeError('Invalid Mac Python 3.7 script archive')
        for mandatory in ('mhs101_original_slot_runtime.pyc',
                          'mhs101_original_slot_gate.pyc',
                          'mhs100_one_slot_policy.pyc',
                          'mhs99_situation_trace.pyc',
                          'mhs55_attendance_ui.pyc'):
            if mandatory not in files:
                raise RuntimeError('Missing one-slot Mac module: '+mandatory)
    summary={
        'status':'M101B_OPT_IN_ORIGINAL_EA_SLOT_FILTER_DIAGNOSTIC_ONLY',
        'package_resources':63,'compiled_modules':COUNT,
        'EA_tuning_replaced':False,
        'armed_on_start':False,
        'extra_EA_situations_created':0,
        'same_day_single_slot_limit':1,
        'requires_real_EA_Base_SimFilter_results':True,
        'requires_EA_weekly_schedule_origin_and_spinup':True,
        'game_test_required':True,
        'package_sha256':hashlib.sha256(package).hexdigest(),
        'game_report':'MHS_M101_UNO_SLOT_EA.json'
    }
    (root/'MHS_M101B_BUILD_REPORT.json').write_text(
        json.dumps(summary,indent=2,sort_keys=True))
    return summary

if __name__=='__main__':
    if len(sys.argv)!=2:
        raise SystemExit('python -m tooling.build_mhs101_one_slot <folder>')
    print(json.dumps(release(sys.argv[1]),indent=2))
