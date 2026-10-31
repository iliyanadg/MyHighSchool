"""M49 minimal fix for M48 Mac error: EA picker max_selectable strategy.

The user reports:
  'ImmutableSlots' object has no attribute 'get_max_selectable'
while opening 'Prepara iscrizione'.

M49 reuses the *exact same* 35 DBPF resources / 5 Lot51 SimData and
3 checked pickers as M48, and recompiles 17 Python 3.7 modules with the
native EA UiDialogObjectPicker._MaxSelectableUnlimited class instead of
a hand-crafted 2015 ImmutableSlots. The callback enforces <=8 students
and transaction enforces max 8 occupied seats.

No M45 menu, roster JSON, child category or school attendance changes.
A Mac runtime test is required. The UI may allow >8 selection, but the
callback rejects that choice without writing the JSON.
"""
import hashlib
import json
import sys
from pathlib import Path

from tooling.build_m48_single_checkmark import (
    package_bytes,compile_scripts,SCRIPTS)

PACKAGE='MHS_M49_PICKER_COMPATIBILE_TEST.package'
SCRIPT='MHS_M49_PICKER_COMPATIBILE_TEST.ts4script'


def release(folder):
    folder=Path(folder)
    folder.mkdir(parents=True,exist_ok=True)
    data=package_bytes()
    (folder/PACKAGE).write_bytes(data)
    compile_scripts(folder/SCRIPT)
    return {
        'status':'MAC_GAME_TEST_REQUIRED',
        'package_sha256':hashlib.sha256(data).hexdigest(),
        'only_change':'replacement of obsolete ImmutableSlots max_selectable strategy',
        'compiled_scripts':len(SCRIPTS),
        'ui_checkmark':'one accepted selection writes',
        'ui_x':'no registry write'
    }


if __name__=='__main__':
    if len(sys.argv)!=2:
        raise SystemExit('Usage: python -m tooling.build_m49_picker_strategy <outdir>')
    print(json.dumps(release(sys.argv[1]),indent=2))
