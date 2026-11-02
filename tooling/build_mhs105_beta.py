"""Build opt-in MY HIGH SCHOOL M105 Mac beta, not a 16/16 release.

Single package: verified M98 76-resource native roster/role menu.
Single Python 3.7 ts4script: M98 runtime plus the isolated M105 3+5+8
school selector and read-only original EA Base schedule audit.

No M96 count override, no custom late invitations, no invented students.
GitHub Actions compiles this with the game's required Python 3.7 magic.
"""
import hashlib
import importlib.util
import json
import py_compile
import sys
import tempfile
import zipfile
from pathlib import Path

from tooling.build_mhs98_roles import (package_bytes,
                                       script_sources as m98_sources)
from tooling.simdata_release_gate import inspect_bytes

ROOT=Path(__file__).resolve().parents[1]
PKG='MHS_M105_CONTROLLO_16_MAC_BETA.package'
SCRIPT='MHS_M105_CONTROLLO_16_MAC_BETA.ts4script'
REPORT='MHS_M105_BUILD_REPORT.json'
ZIP='MHS_M105_CONTROLLO_16_MAC_BETA_INSTALLAZIONE.zip'

M105_MODULES=(
    'mhs105_atomic_school_roster.py',
    'mhs105_native_core_requests.py',
    'mhs105_live_preflight.py',
    'mhs105_native_session.py',
    'mhs105_game_controller.py',
    'mhs105_role_binding_gate.py',
    'mhs105_live_core_binding.py',
    'mhs105_lesson_gate.py',
    'mhs105_schedule_audit.py',
    'mhs105_schedule_runtime.py',
)
SUPPORT=(
    ROOT/'src'/'m93_core'/'mhs93_verified_jobs.py',
    ROOT/'src'/'m101_original_slot'/'mhs101_original_slot_gate.py',
    ROOT/'src'/'m104_native'/'mhs104_native_policy.py',
)
UI=ROOT/'src'/'m105_day_controller'/'mhs55_attendance_ui.py'
EXPECTED_SCRIPTS=48


def script_sources():
    existing=tuple(m98_sources())
    if len(existing)!=35 or sum(p.name==UI.name for p in existing)!=1:
        raise ValueError('Original M98 Mac and role-menu source graph changed')
    replaced=tuple(UI if item.name==UI.name else item for item in existing)
    extra=SUPPORT+tuple(ROOT/'src'/'m105_day_controller'/name for name in M105_MODULES)
    sources=replaced+extra
    if (len(sources)!=EXPECTED_SCRIPTS
            or len(set(item.name for item in sources))!=EXPECTED_SCRIPTS
            or any(not item.is_file() for item in sources)):
        raise ValueError('M105 script graph incomplete or duplicated')
    return sources


def release(folder):
    if (sys.version_info[:2]!=(3,7)
            or importlib.util.MAGIC_NUMBER!=bytes((66,13,13,10))):
        raise RuntimeError('The Sims 4 Mac needs Python 3.7 bytecode')
    folder=Path(folder)
    folder.mkdir(parents=True,exist_ok=True)
    package=package_bytes()
    result=inspect_bytes(package)
    if (result['status']!='STATIC_GATE_PASSED'
            or result['resource_count']!=76
            or result['category_count']!=11
            or result['simdata_count']!=11):
        raise RuntimeError('M98 school menu/role package regression')
    (folder/PKG).write_bytes(package)
    sources=script_sources()
    with tempfile.TemporaryDirectory() as td:
        with zipfile.ZipFile(str(folder/SCRIPT),'w',zipfile.ZIP_DEFLATED) as z:
            for source in sources:
                target=Path(td)/(source.name+'c')
                py_compile.compile(str(source),cfile=str(target),
                                   doraise=True)
                z.write(str(target),arcname=source.name+'c')
    with zipfile.ZipFile(str(folder/SCRIPT)) as z:
        names=z.namelist()
        if (len(names)!=EXPECTED_SCRIPTS
                or set(names)!=set(p.name+'c' for p in sources)
                or not all(z.read(n)[:4]==bytes((66,13,13,10))
                           for n in names)):
            raise RuntimeError('M105 Mac Python 3.7 archive invalid')
        forbidden={'mhs104_native_school_filter.pyc',
                   'mhs101_original_slot_runtime.pyc',
                   'mhs102_bouncer_observer.pyc',
                   'mhs89_precreate_hook.pyc'}
        if forbidden.intersection(names):
            raise RuntimeError('Unsafe or obsolete EA school override included')
    notes=(
        'MY HIGH SCHOOL M105 - BETA TEST SU UNA COPIA DEL SALVATAGGIO\n\n'
        'Questa NON e una versione che garantisce 16 studenti.\n'
        'Installa un SOLO .package e un SOLO .ts4script M105 in Mods.\n'
        'Rimuovi M94, M98, M99, M101, M102, M104 e altre versioni MHS\n'
        'dalla cartella Mods prima del test. Conserva copie di sicurezza.\n'
        'La M105 include il menu dei ruoli speciali; selezionane cinque\n'
        'tra gli studenti iscritti. Richiede 8 studenti in Classe 1, 8\n'
        'in Classe 2, di cui 3 teen giocabili nella famiglia attiva.\n'
        'Da casa PRIMA di andare a scuola, usa la console mhs105.arm.\n'
        'Al liceo usa mhs105.check; per fermare usa mhs105.off.\n'
        'Consulta il file MHS_M105_PIANO_PRE_LEZIONI.json nella cartella\n'
        'Documents/Electronic Arts/The Sims 4/MY_HIGH_SCHOOL_M25_TEST_DATA.\n'
        'L\'aumento del conteggio EA M96 non e attivo. EA potrebbe non\n'
        'creare abbastanza posti, assegnare ruoli diversi o far arrivare\n'
        'NPC non iscritti. Non usare sul salvataggio principale.\n'
    )
    report={
        'status':'M105_MAC_BETA_NOT_FULL_ATTENDANCE_VERIFIED',
        'package_resources':76,
        'compiled_python37_modules':len(sources),
        'native_role_menu_present':True,
        'atomic_3_playable_5_core_8_base_planner_present':True,
        'early_native_selection_opt_in':True,
        'original_ea_base_count_audit_only':True,
        'm96_ea_count_override_enabled':False,
        'class_8_plus_8_routing_verified':False,
        'full_16_attendance_verified':False,
        'EA_random_students_excluded_proved':False,
        'in_game_validation_required':True,
        'install_only_on_save_copy':True,
        'package_sha256':hashlib.sha256(package).hexdigest(),
        'script_sha256':hashlib.sha256((folder/SCRIPT).read_bytes()).hexdigest()
    }
    (folder/REPORT).write_text(json.dumps(report,sort_keys=True,indent=2))
    (folder/'LEGGIMI_M105_BETA.txt').write_text(notes,encoding='utf-8')
    with zipfile.ZipFile(str(folder/ZIP),'w',zipfile.ZIP_DEFLATED) as z:
        for name in (PKG,SCRIPT,REPORT,'LEGGIMI_M105_BETA.txt'):
            z.write(str(folder/name),arcname=name)
    return report


if __name__=='__main__':
    if len(sys.argv)!=2:
        raise SystemExit('python -m tooling.build_mhs105_beta OUTPUT_DIR')
    print(json.dumps(release(sys.argv[1]),sort_keys=True,indent=2))
