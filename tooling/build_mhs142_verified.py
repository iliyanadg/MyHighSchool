"""Verified M142 Mac 3.7 executable archive builder."""
import hashlib
import importlib.util
import json
import py_compile
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
NAME='MHS_M142_LEZIONI_DOPPIO_TURNO_E_MENSA_MAC_BETA.ts4script'
MAGIC=bytes((66,13,13,10))
SOURCES=tuple(ROOT/path for path in (
'src/m2_registry/mhs_m2_roster.py',
'src/m2_registry/mhs_m2_store.py',
'src/m2_registry/mhs56_slot_identity.py',
'src/m2_registry/mhs_m2_game_bridge.py',
'src/m2_registry/mhs34_settings.py',
'src/m97_core_reservations/mhs97_core_role_store.py',
'src/m122_classrooms/mhs122_classroom_job_readback.py',
'src/m123_class_repair/mhs123_lesson_guest_projection.py',
'src/m124_behavior/mhs124_lesson_action_readback.py',
'src/m125_recovery/mhs125_safe_recovery.py',
'src/m126_early/mhs126_early_preparation_projection.py',
'src/m127_timing/mhs127_school_timing_readback.py',
'src/m128_alignment/mhs128_ea_class_trait_alignment.py',
'src/m128_alignment/mhs128_board_posture_audit.py',
'src/m130_physical/mhs130_physical_seat_audit.py',
'src/m131_playable/mhs131_native_playable_class.py',
'src/m132_player_diagnosis/mhs132_native_player_test_audit.py',
'src/m134_jobs/mhs134_native_player_job_audit.py',
'src/m136_player_tests/mhs136_player_test_hierarchy.py',
'src/m139_general_whiteboards/mhs139_ea_zerbu_adapter.py',
'src/m140_auto_lesson/mhs140_native_lesson_entry.py',
'src/m142_two_periods/mhs142_day_trace.py',
'src/m142_two_periods/mhs142_school_policy.py',
'src/m142_two_periods/mhs142_classroom_controller.py',
))


def build(folder):
    if sys.version_info[:2]!=(3,7) or importlib.util.MAGIC_NUMBER!=MAGIC:
        raise RuntimeError('Requires Python 3.7 Sims 4 compatible compile')
    out=Path(folder)
    out.mkdir(parents=True,exist_ok=True)
    result=out/NAME
    with tempfile.TemporaryDirectory() as temp:
        with zipfile.ZipFile(str(result),'w',zipfile.ZIP_DEFLATED) as z:
            for src in SOURCES:
                if not src.exists():
                    raise FileNotFoundError(str(src))
                dest=Path(temp)/(src.stem+'.pyc')
                py_compile.compile(str(src),cfile=str(dest),doraise=True)
                z.write(str(dest),src.stem+'.pyc')
    details={'name':NAME,'sha256':hashlib.sha256(result.read_bytes()).hexdigest(),
        'python':'3.7','module_count':len(SOURCES),
        'real_m142_commands_packaged':True, 'two_separate_ea_periods_rearmed':True, 'one_retry_per_playable_per_period':True,'seat_routing_fix_verified':False, 'lunch_fix_verified':False}
    (out/'M142_BUILD_REPORT.json').write_text(
        json.dumps(details,indent=2),encoding='utf-8')
    (out/'LEGGIMI_M142.txt').write_text(
        'M142 Mac beta — usare una copia del salvataggio. NON testata in gioco.\n'
        'Togliere M141/M141b/M140 e qualsiasi altro controller beta da Mods.\n'
        'Da casa: mhs142.arm. Al liceo: mhs142.monitor per il timer.\n'
        '09:30 preparazione; alle 10:00 lezione EA originale. Se un giocabile\n'
        'non inizia e ha ruolo EA idoneo, un solo tentativo ulteriore 10:04-10:15.\n'
        'Alle 13:25 la M142 riapre UNA VOLTA la preparazione e le lezioni EA\n'
        'per il secondo turno delle 14:00. Alle 14:04-14:15 si puo tentare\n'
        'un solo recupero per giocabile con il suo job di lezione confermato.\n'
        'Durante il pranzo NESSUNA azione imposta ai Sim giocabili.\n'
        'La mensa NPC NON viene modificata: registriamo solo i tempi d’attesa.\n'
        'Verso le 15:05: mhs142.log e mhs142.mensa e mhs142.periodi.\n'
        'Condividere MHS_M142_GIORNATA_LEZIONI_MENSA.json e\n'
        'MHS_M142_MENSA_NPC_ATTESE.json dalla cartella MY_HIGH_SCHOOL_M25_TEST_DATA.\n'
        'La M142 non garantisce fisicamente la seduta: occorre prova sul Mac.\n',
        encoding='utf-8')
    return details


if __name__=='__main__':
    if len(sys.argv)!=2:
        raise SystemExit('Usage: python -m tooling.build_mhs142_verified OUTDIR')
    print(json.dumps(build(sys.argv[1]),indent=2))
