"""Verified M141 Mac 3.7 executable archive builder."""
import hashlib
import importlib.util
import json
import py_compile
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
NAME='MHS_M141B_MONITOR_ATTIVO_LICEO_MENSA_MAC.ts4script'
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
'src/m141_day_trace/mhs141_day_trace.py',
'src/m141_day_trace/mhs141_classroom_controller.py',
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
        'real_m141_commands_packaged':True, 'missed_prep_bootstrap_fixed':True,'seat_routing_fix_verified':False, 'lunch_fix_verified':False}
    (out/'M141B_BUILD_REPORT.json').write_text(
        json.dumps(details,indent=2),encoding='utf-8')
    (out/'LEGGIMI_M141B.txt').write_text(
        'M141b Mac diagnostic beta: use only a TEST COPY of your save.\n'
        'Remove M141, M140, M139 and any other experimental controller from Mods.\n'
        'Before traveling to school: mhs141.arm at home.\n'
        'At school (even if past 09:30): mhs141.monitor.\n'
        'M141b starts observation automatically on arrival, native EA situations,\n'
        'or through the monitor command if the scheduled observation was missed.\n'
        'Expected: M141b MONITOR scuola=True timer=True campioni>=1.\n'
        'During school it records actions and positions every 3 Sim minutes.\n'
        'After lunch or at the end of the school day: mhs141.log to flush.\n'
        'Upload MY_HIGH_SCHOOL_M25_TEST_DATA/MHS_M141_GIORNATA_LEZIONI_MENSA.json.\n'
        'If timer remains False, send its error value rather than playing all day.\n'
        'Finish: mhs141.stop. Observation only: no lunch or lesson correction yet.\n',
        encoding='utf-8')
    return details


if __name__=='__main__':
    if len(sys.argv)!=2:
        raise SystemExit('Usage: python -m tooling.build_mhs141_verified OUTDIR')
    print(json.dumps(build(sys.argv[1]),indent=2))
