"""Build a SMALL M109 read-only method diagnostic for Sims 4 on Mac.

Not the M109 classroom mod. This script does not contain M108 hooks,
no .package, no school menu edits, and no gameplay code. A Python 3.7
runtime is REQUIRED to compile .ts4script compatible bytecode.
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
NAME = 'MHS_M109_NATIVE_METHODS_READ_ONLY.ts4script'
REPORT = 'MHS_M109_READONLY_BUILD_REPORT.json'
SOURCES = (
    ROOT / 'src' / 'm109_activation' / 'mhs109_readonly_ea_probe.py',
    ROOT / 'src' / 'm109_activation' / 'mhs109_game_probe.py',
)
EXPECTED_MAGIC = bytes((66,13,13,10))


def script_sources():
    if (len(SOURCES) != 2 or any(not source.is_file()
                                 for source in SOURCES)
            or len(set(path.name for path in SOURCES)) != len(SOURCES)):
        raise RuntimeError('Missing or duplicate diagnostic-only script')
    return SOURCES


def release(out_folder):
    if (sys.version_info[:2] != (3, 7)
            or importlib.util.MAGIC_NUMBER != EXPECTED_MAGIC):
        raise RuntimeError(
            'Build must run under Python 3.7 matching Sims 4 Mac bytecode')
    out_folder = Path(out_folder)
    out_folder.mkdir(parents=True, exist_ok=True)
    target = out_folder / NAME
    sources = script_sources()
    with tempfile.TemporaryDirectory() as temporary:
        with zipfile.ZipFile(str(target), 'w', zipfile.ZIP_DEFLATED) as archive:
            for source in sources:
                compiled = Path(temporary) / (source.name + 'c')
                py_compile.compile(
                    str(source), cfile=str(compiled), doraise=True)
                archive.write(str(compiled), arcname=source.name+'c')
    with zipfile.ZipFile(str(target)) as archive:
        actual = archive.namelist()
        if (set(actual) != set(source.name + 'c' for source in sources)
                or any(archive.read(name)[:4] != EXPECTED_MAGIC
                       for name in actual)):
            raise RuntimeError('The Sims 4 Python 3.7 archive is invalid')

    report = {
        'status': 'M109_READ_ONLY_METHOD_PROBE_NOT_GAMEPLAY_BETA',
        'py37_script_modules': len(sources),
        'contains_school_controller_hooks': False,
        'modifies_EA_tuning_or_Sims': False,
        'verifies_16_students_in_game': False,
        'hook_targets_verified_in_game': False,
        'hook_target_count_expected': 6,
        'requires_live_game_proof': True,
        'script_file': NAME,
        'sha256': hashlib.sha256(target.read_bytes()).hexdigest(),
    }
    (out_folder / REPORT).write_text(
        json.dumps(report, indent=2, sort_keys=True), encoding='utf-8')
    (out_folder / 'LEGGIMI_M109_DIAGNOSTICA.txt').write_text(
        'M109: SOLA LETTURA, NON LA MOD LICEO COMPLETA.\n'
        'NON verificata finche GitHub Actions non completa il build.\n'
        'Se e quando validata, usare solo su una copia del salvataggio.\n'
        'Non installare altre vecchie coppie sperimentali MHS insieme.\n'
        'Mettere SOLO il file .ts4script nella cartella Mods.\n'
        'Aprire la console e scrivere: mhs109.probe\n'
        'Il JSON mostra 15 metodi EA e sei punti di aggancio M109.\n'
        'Un target individuato NON prova compatibilita o presenze.\n'
        'La mancata rilevazione di marker NON esclude altre mod.\n'
        'Risultato: Documents/Electronic Arts/The Sims 4/'
        'MY_HIGH_SCHOOL_M25_TEST_DATA/'
        'MHS_M109_NATIVE_METHODS_READ_ONLY.json\n'
        'Nessuna modifica a studenti, aule, filtri e situazioni EA.\n',
        encoding='utf-8')
    return report


if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise SystemExit(
            'Usage: python -m tooling.build_mhs109_readonly OUT_DIR')
    print(json.dumps(release(sys.argv[1]), indent=2))
