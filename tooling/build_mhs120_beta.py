"""Build isolated M120 Mac Python3.7 beta with ONLY 8 Base EA trial."""
import hashlib
import importlib.util
import json
import py_compile
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
NAME='MHS_M120_OTTO_BASE_MAC_BETA.ts4script'
MAGIC=bytes((66,13,13,10))
SOURCES=(
    ROOT/'src'/'m2_registry'/'mhs_m2_roster.py',
    ROOT/'src'/'m2_registry'/'mhs_m2_store.py',
    ROOT/'src'/'m2_registry'/'mhs56_slot_identity.py',
    ROOT/'src'/'m2_registry'/'mhs_m2_game_bridge.py',
    ROOT/'src'/'m2_registry'/'mhs34_settings.py',
    ROOT/'src'/'m97_core_reservations'/'mhs97_core_role_store.py',
    ROOT/'src'/'m120_base'/'mhs120_eight_base_live_trial.py',
)


def build(directory):
    if sys.version_info[:2]!=(3,7) or importlib.util.MAGIC_NUMBER!=MAGIC:
        raise RuntimeError('M120 needs original The Sims 4 Python 3.7')
    folder=Path(directory)
    folder.mkdir(parents=True,exist_ok=True)
    target=folder/NAME
    with tempfile.TemporaryDirectory() as temp:
        with zipfile.ZipFile(str(target),'w',zipfile.ZIP_DEFLATED) as archive:
            for source in SOURCES:
                cfile=Path(temp)/(source.stem+'.pyc')
                py_compile.compile(str(source),cfile=str(cfile),doraise=True)
                archive.write(str(cfile),arcname=cfile.name)
    with zipfile.ZipFile(str(target)) as z:
        assert set(z.namelist())==set(f.stem+'.pyc' for f in SOURCES)
        assert all(z.read(name)[:4]==MAGIC for name in z.namelist())
    report={
        'kind':'M120_EIGHT_BASE_EXPERIMENTAL_MAC_GAMEPLAY',
        'status':'PYTHON_3_7_BUILT_NOT_LIVE_VALIDATED',
        'script':NAME,
        'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),
        'compiled_modules':len(SOURCES),
        'school_base_situation_count_proposal':8,
        'original_ea_base_count_expected':(3,3),
        'requires_five_manual_Core_role_appointments':True,
        'native_eight_students_assigned_verified_in_game':False,
        'classroom_lessons_and_seating_verified':False,
        'gameplay_runtime_hooks_installed_only_on_command':True,
        'modifies_own_mhs_save_registry':False,
    }
    (folder/'M120_BUILD_REPORT.json').write_text(
        json.dumps(report,sort_keys=True,indent=2),encoding='utf-8')
    (folder/'LEGGIMI_M120.txt').write_text(
        'M120 OTTO NPC BASE - BETA SPERIMENTALE MAC.\n'
        'Usare SOLO copia del salvataggio. Rimuovere M119/M111.\n'
        'Le due classi MHS devono essere attive e avere 8 iscritti\n'
        'ciascuna; devono esserci 3 teen giocabili iscritti.\n'
        'Nel registro M97 devono essere gia scelti manualmente\n'
        'i cinque ruoli speciali Core su 5 NPC iscritti diversi.\n'
        'Mettere il solo M120 .ts4script in Mods (M54 menu puo restare).\n'
        'A casa prima di andare a scuola: mhs120.arm\n'
        'Al liceo, dopo arrivo: mhs120.status\n'
        'Durante prima lezione, ore 10:30: mhs120.status\n'
        'Controllare EA_base_created, EA_base_present,\n'
        'count_override, native_count e missing.\n'
        'Conta ruoli Base EA, NON posti a sedere ne lezioni.\n'
        'A fine test: mhs120.stop; poi chiudere il gioco.\n'
        'Non usare su salvataggio principale.\n',
        encoding='utf-8')
    return report


if __name__=='__main__':
    if len(sys.argv)!=2:
        raise SystemExit('Usage python -m tooling.build_mhs120_beta OUTPUT')
    print(json.dumps(build(sys.argv[1]),indent=2))
