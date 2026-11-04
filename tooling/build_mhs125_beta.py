"""Build isolated M125 Mac beta: eight original EA Base and five pinned Core."""
import hashlib
import importlib.util
import json
import py_compile
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
NAME='MHS_M125_RECUPERO_AULA_MAC_BETA.ts4script'
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
    ROOT/'src'/'m124_behavior'/'mhs124_lesson_action_readback.py',
    ROOT/'src'/'m125_recovery'/'mhs125_safe_recovery.py',
    ROOT/'src'/'m125_recovery'/'mhs125_thirteen_npc_plus_recovery.py',
)


def build(directory):
    if sys.version_info[:2]!=(3,7) or importlib.util.MAGIC_NUMBER!=MAGIC:
        raise RuntimeError('M125 must compile in Python 3.7 for Sims 4 Mac')
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
        'kind':'M125_THIRTEEN_NPC_CLASSROOM_MANUAL_ONE_SHOT_MIRROR_RECOVERY',
        'status':'BUILT_PYTHON37_NOT_YET_VALIDATED_INSIDE_GAME',
        'script':NAME,
        'sha256':hashlib.sha256(script.read_bytes()).hexdigest(),
        'compiled_modules':len(SOURCES),
        'real_school_lesson_job_readback_enabled':True,
        'three_playable_instance_check_enabled':True,
        'experimental_original_ea_lesson_guest_list_projection':True,
        'native_ea_job_assignment_in_2_classrooms_verified':False,
        'ea_role_state_and_running_interaction_observer':True,
        'physical_seating_automatically_detected':False,
        'manual_one_shot_known_mirror_interaction_cancel':True,
        'ea_original_attend_class_requeued':False,
        'base_situations_proposed':8,
        'core_original_situations_proposed':1,
        'core_ids_from_manual_M97_only':True,
        'native_13_job_assignments_verified_in_game':False,
        'all_16_attending_verified':False,
        'classroom_seating_verified':False,
    }
    (out/'M125_BUILD_REPORT.json').write_text(
        json.dumps(report,sort_keys=True,indent=2),encoding='utf-8')
    (out/'LEGGIMI_M125.txt').write_text(
        'M125 RECUPERO MIRATO - BETA SPERIMENTALE MAC.\n'
        'SOLO copia salvataggio. NON utilizzare il save principale.\n'
        'Rimuovere M124, M123, M122 e beta precedenti da Mods.\n'
        'Conservare mod stabile registro MHS se gia funzionante.\n'
        'Le due classi devono contenere 8 studenti, 3 giocabili,\n'
        '5 Core scelti manualmente nel registro M97, 8 Base NPC.\n'
        'Dal lotto di casa prima della scuola: mhs125.arm\n'
        'Al liceo: mhs125.status dopo arrivo e alle 10:30.\n'
        'Durante la prima lezione: mhs125.classi, mhs125.azioni.\n'
        'Usa mhs125.candidati per controllare i soli NPC\n'
        'con interazione allo specchio concorrente.\n'
        'mhs125.rientro cancella UNA VOLTA quella interazione\n'
        'per NPC con job lezione EA corretto. Non teletrasporta,\n'
        'non forza la seduta, non tocca i giocabili o i bagni.\n'
        'Controllare dopo due minuti mhs125.azioni e visivamente.\n'
        'mhs125.dettagli salva JSON con i 16 role states EA\n'
        'e le interazioni in corso/coda per ogni Sim.\n'
        'File: MY_HIGH_SCHOOL_M25_TEST_DATA/\n'
        'MHS_M125_LEZIONI_RUOLI_AZIONI.json\n'
        'Inviami il file JSON; non serve rifare la giornata.\n'
        'M125 tenta di proporre 8 ID registrati in ciascuna\n'
        'lista ospiti della lezione EA, preservando personale.\n'
        'Il limite e i test EA della lezione possono bloccarli.\n'
        'Status distingue proiezioni e vero job EA.\n'
        'Facoltativo alle 09:30: mhs125.prepara (preparazione).\n'
        'La lettura classi confronta i 16 iscritti con i veri job EA.\n'
        'Non impone ancora le classi o i posti a sedere.\n'
        'Rilevare EA_base_present e EA_core_present separati.\n'
        'Core=5/5 dimostra job EA, NON banco, classe o 16 studenti.\n'
        'Al termine mhs125.stop, quindi chiudere il gioco.\n',
        encoding='utf-8')
    return report


if __name__=='__main__':
    if len(sys.argv)!=2:
        raise SystemExit('Usage python -m tooling.build_mhs124_beta OUTDIR')
    print(json.dumps(build(sys.argv[1]),indent=2))
