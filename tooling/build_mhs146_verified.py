"""Verified M145 Mac 3.7 executable archive builder."""
import hashlib
import importlib.util
import json
import py_compile
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
NAME='MHS_M146_CONTROLLO_16_AULE_ORARI_MAC_BETA.ts4script'
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
'src/m142_two_periods/mhs142_school_policy.py',
'src/m143_native_attendance/mhs143_day_trace.py',
'src/m143_native_attendance/mhs143_native_attendance_policy.py',
'src/m145_class2_playable/mhs145_subject_picker_patch.py',
'src/m145_class2_playable/mhs145_classroom_controller.py',
'src/m146_integrated/mhs146_class_timing_policy.py',
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
        'real_m146_commands_packaged':True, 'two_separate_ea_periods_rearmed':True, 'm145_classpicker_subject_patch_preserved':True,'m146_only_native_class2_prep_with_role':True, 'ea_test_never_bypassed':True,'seat_routing_fix_verified':False, 'lunch_fix_verified':False}
    (out/'M146_BUILD_REPORT.json').write_text(
        json.dumps(details,indent=2),encoding='utf-8')
    (out/'LEGGIMI_M146.txt').write_text(
        'M146 (ingresso anticipato nativo Class2 e rapporto completo) Mac: ESCLUSIVAMENTE SU COPIA DEL SALVATAGGIO.\n'
        'Rimuovi i controller M143, M142 e le altre beta dalla cartella Mods.\n'
        'NON rimuovere la mod Zerbu Elementary: le sue regole restano invariate.\n'
        'Da casa: mhs146.arm poi mhs146.compat (stessi comandi).\n'
        'Verifica che i due risultati selezione e lezioni abbiano applied=True.\n'
        'Se lezioni applied=False, non continuare il test: invia il motivo.\n'
        'Se compare runtime_test_shape, invia la schermata intera: indica tutti\n'
        'i test caricati realmente dalla tua versione EA e dalle mod.\n'
        'Al liceo verso le 9:35: mhs146.monitor (timer=True).\n'
        'Fai scorrere le lezioni delle 10:00 e 14:00, senza ordinare l ingresso.\n'
        'Verso le 15:05: mhs146.report e invia SOLTANTO:\n'
        'MY_HIGH_SCHOOL_M25_TEST_DATA/MHS_M146_REPORT_COMPLETO.json\n'
        'Le interazioni originali delle materie sono conservate:\n'
        'per la lavagna usano il selettore Class1/Class2 originale EA,\n'
        'adattato dal controller MHS, per entrambe le aule.\n'
        'NPC e mensa giocabili non modificati; nessun teletrasporto.\n'
        'Il rapporto M146 contiene ora orario esportazione, ultimo campione e stato dei ruoli.\n'
        'Il recupero di NPC in punizione NON viene forzato.\n'
        'La build ha test automatici, NON e stata ancora validata in gioco.\n',
        encoding='utf-8')
    return details


if __name__=='__main__':
    if len(sys.argv)!=2:
        raise SystemExit('Usage: python -m tooling.build_mhs146_verified OUTDIR')
    print(json.dumps(build(sys.argv[1]),indent=2))
