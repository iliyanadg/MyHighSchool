"""M104: one native EA Bouncer SimFilter candidate constraint Mac TEST.

Original M94 63-resource package unchanged. Original M57 hook is
observation-only unless explicitly armed, then only ONE EA Base matching
request is altered. No SituationGuestList changes, no extra situations.
"""
import hashlib
import importlib.util
import json
import py_compile
import sys
import tempfile
import zipfile
from pathlib import Path
from tooling.build_mhs94_probe import script_sources as base_scripts
from tooling.build_m55_attendance_trial import package_bytes
from tooling.simdata_release_gate import inspect_bytes
ROOT=Path(__file__).resolve().parents[1]
UI=ROOT/'src'/'m104_native'/'mhs55_attendance_ui.py'
POLICY=ROOT/'src'/'m104_native'/'mhs104_native_policy.py'
RUNTIME=ROOT/'src'/'m104_native'/'mhs104_native_school_filter.py'
PKG='MHS_M104_NATIVE_EA_FILTER_MAC_TEST.package'
SCRIPT='MHS_M104_NATIVE_EA_FILTER_MAC_TEST.ts4script'

def script_sources():
    sources=tuple(base_scripts())
    if len(sources)!=33:
        raise ValueError('Original M94 source graph changed')
    sources=tuple(UI if p.name=='mhs55_attendance_ui.py' else p
                  for p in sources)+(POLICY,RUNTIME)
    if len(sources)!=35 or len(set(p.name for p in sources))!=35:
        raise ValueError('M104 nonunique script names')
    return sources

def release(folder):
    if (sys.version_info[:2]!=(3,7)
            or importlib.util.MAGIC_NUMBER!=bytes((66,13,13,10))):
        raise RuntimeError('Mac The Sims 4 requires Python 3.7 bytecode')
    folder=Path(folder)
    folder.mkdir(parents=True,exist_ok=True)
    pkg=package_bytes()
    report=inspect_bytes(pkg)
    if report['status']!='STATIC_GATE_PASSED' or report['resource_count']!=63:
        raise ValueError('Legacy DBPF package must be unchanged')
    (folder/PKG).write_bytes(pkg)
    with tempfile.TemporaryDirectory() as tmp:
        with zipfile.ZipFile(str(folder/SCRIPT),'w',zipfile.ZIP_DEFLATED) as z:
            for src in script_sources():
                out=Path(tmp)/(src.name+'c')
                py_compile.compile(str(src),cfile=str(out),doraise=True)
                z.write(str(out),arcname=src.name+'c')
    with zipfile.ZipFile(str(folder/SCRIPT)) as z:
        names=z.namelist()
        if len(names)!=35 or not all(z.read(name)[:4]==bytes((66,13,13,10))
                                  for name in names):
            raise RuntimeError('Invalid Mac Python 3.7 scripts')
        if not {'mhs104_native_policy.pyc',
                'mhs104_native_school_filter.pyc',
                'mhs57_filter_runtime.pyc',
                'mhs85_ui_bridge.pyc'}.issubset(names):
            raise RuntimeError('Missing native filter support files')
        if {'mhs89_precreate_hook.pyc','mhs101_original_slot_runtime.pyc',
            'mhs102_bouncer_observer.pyc'} & set(names):
            raise RuntimeError('M104 MUST NOT include old guest override hooks')
    result={'status':'M104_ONE_NATIVE_EA_FILTER_TEST_NOT_FULL_ROSTER',
            'compiled_modules':35,'package_resources':63,
            'one_EA_matching_filter_request_only':True,
            'EA_original_guest_lists_modified':False,
            'EA_new_situations_created':False,
            'staff_and_core_filters_unchanged':True,
            'does_not_prove_school_attendance':True,
            'game_test_required':True,
            'package_sha256':hashlib.sha256(pkg).hexdigest(),
            'report':'MHS_M104_NATIVO_FILTRO_EA.json'}
    (folder/'MHS_M104_BUILD_REPORT.json').write_text(
        json.dumps(result,indent=2,sort_keys=True))
    return result

if __name__=='__main__':
    if len(sys.argv)!=2:
        raise SystemExit('python -m tooling.build_mhs104_native_filter OUTPUT')
    print(json.dumps(release(sys.argv[1]),indent=2))
