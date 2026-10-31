"""M54: surgical M53 staff selector fix for animals appearing as adults.

The Sims 4 assigns Age.ADULT to pets too. A valid school employee must be
Species.HUMAN AND Age.YOUNGADULT/ADULT/ELDER. The check runs BOTH while
constructing the player-visible picker and in the final accepted callback
before any JSON commit. Existing accidental pet appointments stay removable
through the Remove menu (not the Assign menu).

Re-use EXACT unchanged M53 package including ten Lot51 categories, IT/EN
STBL and all M52 enrollment/remove/transfer tuning. Recompile the 19 source
Python modules in TS4 Python 3.7 format. Does not touch any user save.
"""
import hashlib
import json
import sys
from pathlib import Path
from tooling.build_m53_staff_management import package_bytes,compile_scripts,SCRIPTS
from tooling.simdata_release_gate import inspect_bytes

PACKAGE='MHS_M54_PERSONALE_SOLO_UMANI_TEST.package'
SCRIPT='MHS_M54_PERSONALE_SOLO_UMANI_TEST.ts4script'


def release(folder):
    folder=Path(folder)
    folder.mkdir(parents=True,exist_ok=True)
    contents=package_bytes()
    report=inspect_bytes(contents)
    if (report['status']!='STATIC_GATE_PASSED'
            or report['category_count']!=10
            or report['simdata_count']!=10
            or len(SCRIPTS)!=19):
        raise RuntimeError('M53 proven menu changed unexpectedly')
    (folder/PACKAGE).write_bytes(contents)
    compile_scripts(folder/SCRIPT)
    return {
        'status':'MAC_GAME_TEST_REQUIRED',
        'source':'M53 successful Mac test',
        'package_same_as_M53':True,
        'package_sha256':hashlib.sha256(contents).hexdigest(),
        'scripts':19,
        'new_appointments':'human young adult, adult or elder only',
        'previously_wrong_staff':'can still be removed',
    }


if __name__=='__main__':
    if len(sys.argv)!=2:
        raise SystemExit('Usage: python -m tooling.build_m54_human_only_staff <dir>')
    print(json.dumps(release(sys.argv[1]),indent=2))
