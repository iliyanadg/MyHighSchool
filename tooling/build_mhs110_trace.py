"""Build isolated M110 opt-in Mac callback diagnostic (Python 3.7 only)."""
import hashlib
import importlib.util
import json
import py_compile
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NAME = 'MHS_M110_EA_CALLBACK_TRACE_MAC_TEST.ts4script'
REPORT = 'MHS_M110_BUILD_REPORT.json'
GUIDE = 'LEGGIMI_M110_TRACCIA_EA.txt'
SOURCES = (
    ROOT / 'src' / 'm110_trace' / 'mhs110_call_trace_core.py',
    ROOT / 'src' / 'm110_trace' / 'mhs110_game_trace.py',
)
EXPECTED_MAGIC = bytes((66, 13, 13, 10))


def release(output):
    if (sys.version_info[:2] != (3, 7)
            or importlib.util.MAGIC_NUMBER != EXPECTED_MAGIC):
        raise RuntimeError('M110 requires Python 3.7 Sims 4 bytecode')
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    archive_path = output / NAME
    with tempfile.TemporaryDirectory() as directory:
        with zipfile.ZipFile(str(archive_path), 'w', zipfile.ZIP_DEFLATED) as z:
            for source in SOURCES:
                compiled = Path(directory) / (source.name + 'c')
                py_compile.compile(str(source), cfile=str(compiled),
                                   doraise=True)
                z.write(str(compiled), arcname=compiled.name)
    with zipfile.ZipFile(str(archive_path)) as z:
        names = set(z.namelist())
        expected = {source.name + 'c' for source in SOURCES}
        if (names != expected or
                any(z.read(name)[:4] != EXPECTED_MAGIC for name in names)):
            raise RuntimeError('M110 archive content / Python 3.7 mismatch')
    report = {
        'status': 'M110_OPT_IN_CALLBACK_TRACE_OFFLINE_TEST_ONLY',
        'compiled_modules': 2,
        'python': '3.7',
        'script_file': NAME,
        'sha256': hashlib.sha256(archive_path.read_bytes()).hexdigest(),
        'temporarily_wraps_original_ea_methods': True,
        'auto_install_on_import': False,
        'contains_gameplay_controller': False,
        'proves_16_student_attendance': False,
        'mac_game_test_required': True,
    }
    (output / REPORT).write_text(json.dumps(report, indent=2,
                        sort_keys=True), encoding='utf-8')
    (output / GUIDE).write_text(
        'M110 - DIAGNOSTICA SPERIMENTALE. NON E LA MOD SCOLASTICA.\n'
        'Usare SOLO su una COPIA del salvataggio, senza altre beta MHS.\n'
        'A DIFFERENZA di M109, M110 applica wrapper TEMPORANEI\n'
        'ai metodi Python EA in memoria. Non altera roster o tuning,\n'
        'ma puo essere incompatibile con altre script mod.\n'
        'Mettere SOLO il file .ts4script in Mods.\n'
        'A casa, prima del successivo giorno di scuola, aprire la console:\n'
        'mhs110.start\n'
        'Poi andare a scuola normalmente e dopo le lezioni digitare:\n'
        'mhs110.stop\n'
        'Se necessario: mhs110.status\n'
        'Il comando stop ripristina i metodi EA se non sono stati\n'
        'nel frattempo sostituiti da altre mod.\n'
        'Rapporto: Documents/Electronic Arts/The Sims 4/\n'
        'MY_HIGH_SCHOOL_M25_TEST_DATA/MHS_M110_NATIVE_EA_CALL_TRACE.json\n'
        'Il rapporto NON contiene nomi o identificativi dei Sim.\n'
        'Traccia fino a 1024 eventi, inclusi stato risultato e situation GUID.\n'
        'Non prova che 16 studenti siano presenti o seduti.\n',
        encoding='utf-8')
    return report


if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise SystemExit('Usage: python -m tooling.build_mhs110_trace OUT_DIR')
    print(json.dumps(release(sys.argv[1]), indent=2))
