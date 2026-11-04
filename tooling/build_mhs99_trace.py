"""M99 Mac diagnostic: one opted-in school student invitation lifecycle.

M94-compatible 63-resource DBPF is retained byte-for-byte.
M99 overrides only M61 pilot Python code and adds its pure trace helper.
Do not install this package together with M94/M98.
No additional automated EA invitations or situation filters are installed.
"""
import hashlib
import importlib.util
import json
import py_compile
import sys
import tempfile
import zipfile
from pathlib import Path

from tooling.build_mhs94_probe import script_sources as m94_scripts
from tooling.build_m55_attendance_trial import package_bytes
from tooling.simdata_release_gate import inspect_bytes

ROOT=Path(__file__).resolve().parents[1]
PILOT=ROOT/'src'/'m99_trace'/'mhs61_pilot_command.py'
TRACE=ROOT/'src'/'m99_trace'/'mhs99_situation_trace.py'
PKG='MHS_M99_TRACCIA_INVITO_MAC_TEST.package'
SCRIPT='MHS_M99_TRACCIA_INVITO_MAC_TEST.ts4script'

def script_sources():
    old=tuple(m94_scripts())
    if len(old)!=33 or sum(p.name=='mhs61_pilot_command.py' for p in old)!=1:
        raise ValueError('M94 source script graph changed')
    replaced=tuple(PILOT if p.name=='mhs61_pilot_command.py' else p
                   for p in old)
    sources=replaced+(TRACE,)
    if len(sources)!=34 or len(set(p.name for p in sources))!=34:
        raise ValueError('M99 Python module names collide')
    return sources

def release(folder):
    if (sys.version_info[:2]!=(3,7)
            or importlib.util.MAGIC_NUMBER!=bytes((66,13,13,10))):
        raise RuntimeError('Mac The Sims 4 requires Python 3.7 bytecode')
    folder=Path(folder)
    folder.mkdir(parents=True,exist_ok=True)
    blob=package_bytes()
    check=inspect_bytes(blob)
    if (check['status']!='STATIC_GATE_PASSED'
            or (check['resource_count'],check['category_count'],
                check['simdata_count'])!=(63,10,10)):
        raise ValueError('M94 DBPF legacy menu unexpectedly modified')
    (folder/PKG).write_bytes(blob)
    with tempfile.TemporaryDirectory() as temp:
        with zipfile.ZipFile(str(folder/SCRIPT),'w',zipfile.ZIP_DEFLATED) as z:
            for source in script_sources():
                compiled=Path(temp)/(source.name+'c')
                py_compile.compile(str(source),cfile=str(compiled),doraise=True)
                z.write(str(compiled),arcname=source.name+'c')
    with zipfile.ZipFile(str(folder/SCRIPT)) as z:
        names=z.namelist()
        if len(names)!=34 or not all(z.read(n)[:4]==bytes((66,13,13,10))
                                   for n in names):
            raise ValueError('M99 Python 3.7 bytecode graph invalid')
        if not {'mhs61_pilot_command.pyc',
                'mhs99_situation_trace.pyc',
                'mhs94_school_job_probe.pyc',
                'mhs55_attendance_ui.pyc'}.issubset(names):
            raise ValueError('M99 pilot, read-only report or original menu missing')
    result={'status':'M99_ONE_STUDENT_LIFECYCLE_DIAGNOSTIC_ONLY',
            'package_resources':63,'compiled_modules':34,
            'base_package_matches_M94':True,
            'new_automated_invites':0,
            'ea_filters_modified':False,
            'reported_fields':[
                'created_situation_id','situation_lookup',
                'situation_member_ids','on_lot','in_school_situation'],
            'report':'MHS_M99_INVITO_STUDENTE_TRACE.json',
            'game_test_required':True,
            'package_sha256':hashlib.sha256(blob).hexdigest()}
    (folder/'MHS_M99_BUILD_REPORT.json').write_text(
        json.dumps(result,indent=2,sort_keys=True))
    return result

if __name__=='__main__':
    if len(sys.argv)!=2:
        raise SystemExit('Usage: python -m tooling.build_mhs99_trace OUTPUT')
    print(json.dumps(release(sys.argv[1]),indent=2))
