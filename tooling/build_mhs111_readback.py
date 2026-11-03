"""Build isolated M111 read-only Mac diagnostic from original tested modules.

Python 3.7 only. No .package, no controller hooks. Contains the existing
M54/M57 registry *readers*, never the M57 interception module.
"""
import hashlib
import importlib.util
import json
import py_compile
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NAME = 'MHS_M111_EA_JOB_READ_ONLY_MAC_TEST.ts4script'
REPORT = 'MHS_M111_BUILD_REPORT.json'
GUIDE = 'LEGGIMI_M111_RUOLI_EA.txt'
EXPECTED_MAGIC = bytes((66,13,13,10))
SOURCES = (
    ROOT/'src'/'m2_registry'/'mhs_m2_roster.py',
    ROOT/'src'/'m2_registry'/'mhs_m2_store.py',
    ROOT/'src'/'m2_registry'/'mhs56_slot_identity.py',
    ROOT/'src'/'m2_registry'/'mhs_m2_game_bridge.py',
    ROOT/'src'/'m2_registry'/'mhs34_settings.py',
    ROOT/'src'/'m53_staff'/'mhs53_staff_store.py',
    ROOT/'src'/'m57_selection'/'mhs57_school_manifest.py',
    ROOT/'src'/'m111_bouncer'/'mhs111_school_job_readback.py',
    ROOT/'src'/'m111_bouncer'/'mhs111_live_school_bridge.py',
    ROOT/'src'/'m111_bouncer'/'mhs111_game_probe.py',
)


def release(folder):
    if (sys.version_info[:2] != (3,7)
            or importlib.util.MAGIC_NUMBER != EXPECTED_MAGIC):
        raise RuntimeError('The Sims 4 M111 requires Python 3.7 bytecode')
    folder=Path(folder)
    folder.mkdir(parents=True,exist_ok=True)
    target=folder/NAME
    with tempfile.TemporaryDirectory() as work:
        with zipfile.ZipFile(str(target),'w',zipfile.ZIP_DEFLATED) as z:
            for source in SOURCES:
                compiled=Path(work)/(source.name+'c')
                py_compile.compile(str(source),cfile=str(compiled),
                                   doraise=True)
                z.write(str(compiled),arcname=compiled.name)
    expected=set(source.name+'c' for source in SOURCES)
    if len(expected)!=len(SOURCES):
        raise RuntimeError('Duplicate module filename in M111')
    with zipfile.ZipFile(str(target)) as z:
        if (set(z.namelist())!=expected or any(
                z.read(name)[:4]!=EXPECTED_MAGIC for name in expected)):
            raise RuntimeError('M111 wrong modules or Python magic')
    report={
        'kind':'M111_READ_ONLY_MAC_ARTIFACT',
        'status':'PYTHON_3_7_OFFLINE_BUILD_PASSED_NOT_GAME_VALIDATED',
        'script_file':NAME,
        'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),
        'compiled_modules':len(SOURCES),
        'contains_roster_write_command':False,
        'contains_hooks_or_automatic_classroom_control':False,
        'real_ea_bouncer_assignment_verified':False,
        'two_classroom_seating_verified':False,
    }
    (folder/REPORT).write_text(json.dumps(report,indent=2,
              sort_keys=True),encoding='utf-8')
    (folder/GUIDE).write_text(
        'M111 - DIAGNOSTICA IN SOLA LETTURA - NON MOD CONTROLLER.\n'
        'Solo su un salvataggio di prova con registro MHS M54/M57 gia\n'
        'configurato (due classi, 8 studenti per aula, attivato).\n'
        'Chiudere il gioco e togliere le altre beta sperimentali MHS.\n'
        'Mettere SOLO il .ts4script in Mods (nessun .package).\n'
        'A casa, prima della scuola: mhs111.arm\n'
        'Arrivata al liceo, durante una lezione: mhs111.check\n'
        'La sola chiamata check genera un rapporto JSON nella cartella\n'
        'Documents/Electronic Arts/The Sims 4/\n'
        'MY_HIGH_SCHOOL_M25_TEST_DATA/MHS_M111_NATIVE_SCHOOL_JOB_READBACK.json\n'
        'Nessun wrapper EA: niente start/stop, nessun nuovo Sim generato.\n'
        'I Sim ID del proprio salvataggio sono presenti nel rapporto;\n'
        'non pubblicare il file se non si desidera condividerli.\n'
        'Non prova presenza per tutta la giornata o sedute in aula.\n',
        encoding='utf-8')
    return report


if __name__=='__main__':
    if len(sys.argv)!=2:
        raise SystemExit('Usage: python -m tooling.build_mhs111_readback OUTPUT')
    print(json.dumps(release(sys.argv[1]),indent=2))
