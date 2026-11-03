"""M119 single EA Base experimental Mac build. Python 3.7 bytecode."""
import hashlib
import importlib.util
import json
import py_compile
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
NAME='MHS_M119_UN_POSTO_BASE_MAC_BETA.ts4script'
EXPECTED=bytes((66,13,13,10))
FILES=(
 ROOT/'src'/'m2_registry'/'mhs_m2_roster.py',
 ROOT/'src'/'m2_registry'/'mhs_m2_store.py',
 ROOT/'src'/'m2_registry'/'mhs56_slot_identity.py',
 ROOT/'src'/'m2_registry'/'mhs_m2_game_bridge.py',
 ROOT/'src'/'m2_registry'/'mhs34_settings.py',
 ROOT/'src'/'m119_live_trial'/'mhs119_one_base_live_trial.py',
)


def build(directory):
    if sys.version_info[:2]!=(3,7) or importlib.util.MAGIC_NUMBER!=EXPECTED:
        raise RuntimeError('The Sims 4 M119 requires original Python3.7 bytecode')
    output=Path(directory)
    output.mkdir(parents=True,exist_ok=True)
    script=output/NAME
    with tempfile.TemporaryDirectory() as temp:
        with zipfile.ZipFile(str(script),'w',zipfile.ZIP_DEFLATED) as archive:
            for file in FILES:
                compiled=Path(temp)/(file.stem+'.pyc')
                py_compile.compile(str(file),cfile=str(compiled),doraise=True)
                archive.write(str(compiled),arcname=compiled.name)
    with zipfile.ZipFile(str(script)) as archive:
        names=set(archive.namelist())
        assert names==set(file.stem+'.pyc' for file in FILES)
        assert all(archive.read(name)[:4]==EXPECTED for name in names)
    report={
        'kind':'M119_SINGLE_BASE_EA_INTERVENTION_EXP_BETA',
        'status':'PYTHON37_BUILT_NOT_YET_TESTED_INSIDE_SIMS',
        'script':NAME,
        'sha256':hashlib.sha256(script.read_bytes()).hexdigest(),
        'compiled_modules':len(FILES),
        'intervention':'one registered Class1 NPC in one original EA Base situation',
        'real_gameplay_student_spawn_proven':False,
        'modifies_ea_runtime_methods_on_manual_arm':True,
        'edits_save_or_registry_files':False,
        'full_16_attendance_proven':False,
    }
    (output/'M119_BUILD_REPORT.json').write_text(
        json.dumps(report,indent=2,sort_keys=True),encoding='utf-8')
    (output/'LEGGIMI_M119.txt').write_text(
        'M119 UN POSTO BASE - BETA SPERIMENTALE MAC.\n'
        'NON e una soluzione 16 studenti, un solo NPC viene provato.\n'
        'Usare SOLTANTO una COPIA del salvataggio di prova.\n'
        'Chiudere The Sims 4, rimuovere M111/M110/M119 precedenti\n'
        'e altre beta controller dalla cartella Mods.\n'
        'Mettere questo unico .ts4script in Mods (non necessita package).\n'
        'Il registro MHS gia esistente deve avere due classi da 8\n'
        'e la famiglia attiva tre teen iscritti.\n'
        'Da casa prima del liceo: mhs119.arm\n'
        'Il comando mostra il SimID di un NPC iscritto alla Classe 1.\n'
        'Al liceo: mhs119.status (dopo le 08:00).\n'
        'Se attempts=1 ed EA_situation > 0 abbiamo almeno provato\n'
        'una convocazione, NON che lo studente sia presente.\n'
        'EA_ruolo=SI_TARGET_PRESENTE: NPC scelto nel job EA Base.\n'
        'EA_ruolo=NO_SIM_DIVERSO: sostituito da altro Sim.\n'
        'Altri valori: assegnazione EA non verificabile o incompleta.\n'
        'Inviare screenshot del risultato e controllo visivo dello studente.\n'
        'Alla fine: mhs119.stop per ripristinare i metodi EA.\n'
        'I metodi originali sono ripristinati anche riavviando il gioco.\n'
        'Non usare su salvataggi importanti. Non garantisce capienza.\n',
        encoding='utf-8')
    return report


if __name__=='__main__':
    if len(sys.argv)!=2:
        raise SystemExit('Usage python -m tooling.build_mhs119_trial OUTDIR')
    print(json.dumps(build(sys.argv[1]),indent=2))
