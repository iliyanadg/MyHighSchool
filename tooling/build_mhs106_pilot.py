"""Compile EXPERIMENTAL M106 Mac school-only native filter pilot.

Contains the same verified 76-resource M98 menu and 48 Python3.7 M105
dependencies, but substitutes M106 loader and adds five M106 modules.
NOT a verified sixteen-student release: EA original Base count remains six.
Never install alongside M105; use a test save only.
"""
import hashlib
import importlib.util
import json
import py_compile
import sys
import tempfile
import zipfile
from pathlib import Path

from tooling.build_mhs105_beta import script_sources as m105_sources
from tooling.build_mhs98_roles import package_bytes
from tooling.simdata_release_gate import inspect_bytes

ROOT=Path(__file__).resolve().parents[1]
PACKAGE='MHS_M106_ROSTER_FIRST_MAC_PILOT.package'
SCRIPT='MHS_M106_ROSTER_FIRST_MAC_PILOT.ts4script'
REPORT='MHS_M106_PILOT_REPORT.json'
ZIP='MHS_M106_ROSTER_FIRST_MAC_PILOT_INSTALLAZIONE.zip'
UI=ROOT/'src'/'m106_roster_first'/'mhs55_attendance_ui.py'
MODULES=(
    'mhs106_roster_first_policy.py',
    'mhs106_bridge_arguments.py',
    'mhs106_live_preflight.py',
    'mhs106_school_session.py',
    'mhs106_game_controller.py',
)
EXPECTED_SCRIPTS=53


def script_sources():
    prior=tuple(m105_sources())
    if (len(prior)!=48
            or sum(x.name==UI.name for x in prior)!=1):
        raise RuntimeError('M105 source graph changed')
    inherited=tuple(UI if x.name==UI.name else x for x in prior)
    extra=tuple(ROOT/'src'/'m106_roster_first'/name for name in MODULES)
    paths=inherited+extra
    if (len(paths)!=EXPECTED_SCRIPTS
            or len({p.name for p in paths})!=EXPECTED_SCRIPTS
            or any(not p.is_file() for p in paths)):
        raise RuntimeError('M106 source graph incomplete')
    return paths


def release(out):
    if (sys.version_info[:2]!=(3,7)
            or importlib.util.MAGIC_NUMBER!=bytes((66,13,13,10))):
        raise RuntimeError('Mac TS4 requires verified Python 3.7 bytecode')
    out=Path(out)
    out.mkdir(parents=True,exist_ok=True)
    pkg=package_bytes()
    checked=inspect_bytes(pkg)
    if (checked['status']!='STATIC_GATE_PASSED'
            or checked['resource_count']!=76
            or checked['simdata_count']!=11):
        raise RuntimeError('M98 native role-menu resource regression')
    (out/PACKAGE).write_bytes(pkg)
    sources=script_sources()
    with tempfile.TemporaryDirectory() as work:
        with zipfile.ZipFile(str(out/SCRIPT),'w',zipfile.ZIP_DEFLATED) as archive:
            for path in sources:
                target=Path(work)/(path.name+'c')
                py_compile.compile(str(path),cfile=str(target),doraise=True)
                archive.write(str(target),arcname=path.name+'c')
    with zipfile.ZipFile(str(out/SCRIPT)) as scripts:
        names=scripts.namelist()
        if (len(names)!=EXPECTED_SCRIPTS
                or len(set(names))!=len(names)
                or any(scripts.read(n)[:4]!=bytes((66,13,13,10))
                       for n in names)):
            raise RuntimeError('M106 Mac Python3.7 scripts not verifiable')
        for essential in ('mhs106_game_controller.pyc',
                          'mhs106_school_session.pyc',
                          'mhs106_bridge_arguments.pyc',
                          'mhs106_live_preflight.pyc',
                          'mhs106_roster_first_policy.pyc',
                          'mhs55_attendance_ui.pyc'):
            if essential not in names:
                raise RuntimeError('Missing essential M106 runtime '+essential)
    notes=(
        'MY HIGH SCHOOL - M106 ROSTER FIRST - SOLO PILOT SPERIMENTALE\n'
        'NON GARANTISCE 16/16 studenti e NON corregge 8 Base EA.\n'
        'SOLO UNA COPIA DEL SALVATAGGIO. NON usare su quello principale.\n'
        'Rimuovi tutte le precedenti coppie MHS da Mods prima di provare.\n'
        'Copia un solo .package e un solo .ts4script M106 nella cartella Mods.\n'
        'Le 2 classi devono avere 8 studenti ciascuna, 3 giocabili iscritti.\n'
        'Con 5 ruoli MHS salvati, da casa prima del liceo: mhs106.arm\n'
        'Al liceo: mhs106.check; disattiva: mhs106.off\n'
        'Questo pilota sostituisce il filtro nativo per uno specifico ruolo\n'
        'Core solo con scuola/save/giorno/Bouncer verificati.\n'
        'Non cambia i tratti, il registro, i professori, le situazioni EA,\n'
        'ne il conteggio EA delle richieste Base (originalmente 6).\n'
        'Una richiesta vincolata NON prova uno studente presente o un ruolo.\n'
        'Report: Documents/Electronic Arts/The Sims 4/\n'
        'MY_HIGH_SCHOOL_M25_TEST_DATA/MHS_M106_PIANO_GIORNO.json\n')
    (out/'LEGGIMI_M106_PILOT.txt').write_text(notes,encoding='utf-8')
    report={
        'status':'EXPERIMENTAL_NATIVE_CORE_BASE_PILOT_NOT_16_ATTENDANCE',
        'package_resources':76,
        'compiled_python37_modules':len(sources),
        'read_actual_6_EA_filters':True,
        'fixed_roster_3_playable_5_core_8_base':True,
        'native_core_filter_request_bridge_opt_in':True,
        'base_student_filter_constraints_opt_in':True,
        'ea_base_schedule_count_override_enabled':False,
        'actual_ea_core_role_bindings_verified':False,
        'full_16_attendance_verified':False,
        'class_8_plus_8_routing_verified':False,
        'release_ready':False,
        'test_copy_only':True,
        'package_sha256':hashlib.sha256(pkg).hexdigest(),
        'script_sha256':hashlib.sha256((out/SCRIPT).read_bytes()).hexdigest()
    }
    (out/REPORT).write_text(json.dumps(report,sort_keys=True,indent=2))
    with zipfile.ZipFile(str(out/ZIP),'w',zipfile.ZIP_DEFLATED) as package:
        for name in (PACKAGE,SCRIPT,REPORT,'LEGGIMI_M106_PILOT.txt'):
            package.write(str(out/name),arcname=name)
    return report


if __name__=='__main__':
    if len(sys.argv)!=2:
        raise SystemExit('python -m tooling.build_mhs106_pilot OUTPUT_DIR')
    print(json.dumps(release(sys.argv[1]),indent=2))
