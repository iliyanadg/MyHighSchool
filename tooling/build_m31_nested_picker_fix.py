"""M31 cumulative The Sims 4 test build.

Includes all M30 nested class menus plus native picker policy fix in
M27 source, shared by both removal and view. No changes to the
existing M25 test register, Sim IDs, or EA attendance.
"""
import hashlib
import json
from pathlib import Path
from tooling.build_m30_nested_menu import (package_bytes, compile_scripts,
                                          SCRIPTS)
from tooling.simdata_release_gate import resources, inspect_bytes

PACK_NAME = 'MHS_M31_SOTTOMENU_PICKER_FIX_TEST.package'
SCRIPT_NAME = 'MHS_M31_SOTTOMENU_PICKER_FIX_TEST.ts4script'


def release(folder):
    folder=Path(folder)
    folder.mkdir(parents=True,exist_ok=True)
    payload=package_bytes()
    report=inspect_bytes(payload)
    if (report['status']!='STATIC_GATE_PASSED' or
            report['category_count']!=4 or report['simdata_count']!=4):
        raise RuntimeError('The M30 submenu resources failed validation')
    (folder/PACK_NAME).write_bytes(payload)
    compile_scripts(folder/SCRIPT_NAME)
    return {'status':'EXPERIMENTAL_GAME_TEST_REQUIRED',
            'resources':len(resources(payload)),
            'scripts':len(SCRIPTS),
            'sha256':hashlib.sha256(payload).hexdigest()}


if __name__=='__main__':
    import sys
    if len(sys.argv)!=2:
        raise SystemExit('Usage: python -m tooling.build_m31_nested_picker_fix <folder>')
    print(json.dumps(release(sys.argv[1]),indent=2))
