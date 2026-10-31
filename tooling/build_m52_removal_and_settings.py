"""M52: M51 bulk transfer/enrollment + single-✓ bulk withdrawal + notices.

DBPF package stays 100% byte-identical with the M51 Mac-tested source.
Only 2 existing .py modules inside the existing 17-script TS4 script ZIP
are changed: mhs27_remove_ui.py and mhs34_settings_ui.py.

M52 removal UX:
  MY HIGH SCHOOL -> Classe 1/2/3 -> Rimuovi studenti
  -> native multi-select of enrolled students only
  -> ✓ deletes ALL selected roster memberships atomically; X does nothing.
The original Sims remain in the EA save. No console commands required.

Occupied Classe 3 cannot be disabled by design, but now warns users with a
native popup rather than failing silently. To disable it, first transfer
or withdraw its students. Maximum of 8 seats per class remains.

The project's intended mandatory expansion is High School Years (EP12).
EA attendance / staff management and pack availability gate are not yet
implemented. Python 3.7 for game Mac builds; no user save is modified here.
"""
import hashlib
import json
import sys
from pathlib import Path
from tooling.build_m51_bulk_transfer import package_bytes
from tooling.build_m48_single_checkmark import compile_scripts,SCRIPTS
from tooling.simdata_release_gate import inspect_bytes

PACKAGE="MHS_M52_RIMOZIONI_MULTIPLE_AVVISI_TEST.package"
SCRIPT="MHS_M52_RIMOZIONI_MULTIPLE_AVVISI_TEST.ts4script"

def release(directory):
    directory=Path(directory)
    directory.mkdir(parents=True,exist_ok=True)
    package=package_bytes()
    gate=inspect_bytes(package)
    if gate['status']!='STATIC_GATE_PASSED' or gate['category_count']!=5 or gate['simdata_count']!=5:
        raise RuntimeError('M51 category graph changed')
    required={'mhs27_remove_ui.py','mhs34_settings_ui.py',
              'mhs32_transfer_ui.py','mhs48_single_picker.py'}
    if not required.issubset({p.name for p in SCRIPTS}) or len(SCRIPTS)!=17:
        raise RuntimeError('Incorrect TS4 script module inventory')
    (directory/PACKAGE).write_bytes(package)
    compile_scripts(directory/SCRIPT)
    return {
        'status':'MAC_GAME_TEST_REQUIRED',
        'package_sha256':hashlib.sha256(package).hexdigest(),
        'same_DBPF_as_M51':True,
        'modules':len(SCRIPTS),
        'remove_native_multi_select':True,
        'class3_occupied_disable_notice':True,
        'high_school_years_EP12_required_for_future_product':True
    }

if __name__=="__main__":
    if len(sys.argv)!=2:
        raise SystemExit('Usage: python -m tooling.build_m52_removal_and_settings <dir>')
    print(json.dumps(release(sys.argv[1]),indent=2))
