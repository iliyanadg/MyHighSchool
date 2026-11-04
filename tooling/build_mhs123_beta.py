"""Build isolated M123 Mac beta: eight original EA Base and five pinned Core."""
import hashlib
import importlib.util
import json
import py_compile
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
NAME='MHS_M123_DUE_AULE_MAC_BETA.ts4script'
MAGIC=bytes((66,13,13,10))
SOURCES=(
    ROOT/'src'/'m2_registry'/'mhs_m2_roster.py',
    ROOT/'src'/'m2_registry'/'mhs_m2_store.py',
    ROOT/'src'/'m2_registry'/'mhs56_slot_identity.py',
    ROOT/'src'/'m2_registry'/'mhs_m2_game_bridge.py',
    ROOT/'src'/'m2_registry'/'mhs34_settings.py',
    ROOT/'src'/'m97_core_reservations'/'mhs97_core_role_store.py',
    ROOT/'src'/'m122_classrooms'/'mhs122_classroom_job_readback.py',
    ROOT/'src'/'m123_class_repair'/'mhs123_lesson_guest_projection.py',
    ROOT/'src'/'m123_class_repair'/'mhs123_thirteen_npc_class_trial.py',
)


def build(directory):
    if sys.version_info[:2]!=(3,7) or importlib.util.MAGIC_NUMBER!=MAGIC:
        raise RuntimeError('M123 must compile in Python 3.7 for Sims 4 Mac')
    out=Path(directory)
    out.mkdir(parents=True,exist_ok=True)
    script=out/NAME
    with tempfile.TemporaryDirectory() as temp:
        with zipfile.ZipFile(str(script),'w',zipfile.ZIP_DEFLATED) as archive:
            for source in SOURCES:
                compiled=Path(temp)/(source.stem+'.pyc')
                py_compile.compile(str(source),cfile=str(compiled),doraise=True)
                archive.write(str(compiled),arcname=compiled.name)
    with zipfile.ZipFile(str(script)) as archive:
        assert set(archive.namelist())==set(f.stem+'.pyc' for f in SOURCES)
        assert all(archive.read(n)[:4]==MAGIC for n in archive.namelist())
    report={
        'kind':'M123_THIRTEEN_NPC_PLUS_EXPERIMENTAL_TWO_CLASS_LESSON_GUESTS',
        'status':'BUILT_PYTHON37_NOT_YET_VALIDATED_INSIDE_GAME',
        'script':NAME,
        'sha256':hashlib.sha256(script.read_bytes()).hexdigest(),
        'compiled_modules':len(SOURCES),
        'real_school_lesson_job_readback_enabled':True,
        'three_playable_instance_check_enabled':True,
        'experimental_original_ea_lesson_guest_list_projection':True,
        'native_ea_job_assignment_in_2_classrooms_verified':False,
        'base_situations_proposed':8,
        'core_original_situations_proposed':1,
        'core_ids_from_manual_M97_only':True,
        'native_13_job_assignments_verified_in_game':False,
        'all_16_attending_verified':False,
        'classroom_seating_verified':False,
    }
    (out/'M123_BUILD_REPORT.json').write_text(
        json.dumps(report,sort_keys=True,indent=2),encoding='utf-8')
    (out/'LEGGIMI_M123.txt').write_text(
        'M123 13 NPC + PROVA DUE AULE - BETA SPERIMENTALE MAC.\n'
        'SOLO copia salvataggio. NON utilizzare il save principale.\n'
        'Rimuovere M122, M121, M120, M119 e beta precedenti da Mods.\n'
        'Conservare mod stabile registro MHS se gia funzionante.\n'
        'Le due classi devono contenere 8 studenti, 3 giocabili,\n'
        '5 Core scelti manualmente nel registro M97, 8 Base NPC.\n'
        'Dal lotto di casa prima della scuola: mhs123.arm\n'
        'Al liceo: mhs123.status dopo arrivo e alle 10:30.\n'
        'Alle 10:30: mhs123.classi, poi mhs123.status.\n'
        'M123 tenta di proporre 8 ID registrati in ciascuna\n'
        'lista ospiti della lezione EA, preservando personale.\n'
        'Il limite e i test EA della lezione possono bloccarli.\n'
        'Status distingue proiezioni e vero job EA.\n'
        'Facoltativo alle 09:30: mhs123.prepara (preparazione).\n'
        'La lettura classi confronta i 16 iscritti con i veri job EA.\n'
        'Non impone ancora le classi o i posti a sedere.\n'
        'Rilevare EA_base_present e EA_core_present separati.\n'
        'Core=5/5 dimostra job EA, NON banco, classe o 16 studenti.\n'
        'Al termine mhs123.stop, quindi chiudere il gioco.\n',
        encoding='utf-8')
    return report


if __name__=='__main__':
    if len(sys.argv)!=2:
        raise SystemExit('Usage python -m tooling.build_mhs122_beta OUTDIR')
    print(json.dumps(build(sys.argv[1]),indent=2))
