"""M50: preserve M49 package; only fix enrolled filtering and native seat cap.

M49's in-game Mac screenshot proves native UiSimPicker, checkmark commit and
X cancel work. Preserve its package byte-for-byte and update only scripts:

- Enrolled teens (in ANY class) no longer appear in Iscrivi;
- Existing teens remain available from Consulta/Rimuovi/Trasferisci;
- EA's tested _MaxSelectableUnlimited strategy is subclassed with
  get_max_selectable() returning min(8-current_class_size, available_rows);
- Backend only_new flag guards against switching classes via Iscrivi, even
  if another action writes before a picker is confirmed.

Eight seats are a *registry capacity*, not proof that 8 pupils actually
spawn at High School Years. In-game Mac validation required.
"""
import hashlib
import json
import sys
from pathlib import Path
from tooling.build_m48_single_checkmark import (
    package_bytes, compile_scripts, SCRIPTS)
from tooling.simdata_release_gate import inspect_bytes

PACKAGE="MHS_M50_ISCRIZIONI_FILTRATE_LIMITE_POSTI_TEST.package"
SCRIPT="MHS_M50_ISCRIZIONI_FILTRATE_LIMITE_POSTI_TEST.ts4script"

def release(directory):
    directory=Path(directory)
    directory.mkdir(parents=True,exist_ok=True)
    payload=package_bytes()
    validation=inspect_bytes(payload)
    if (validation["status"]!="STATIC_GATE_PASSED"
            or validation["category_count"]!=5
            or validation["simdata_count"]!=5):
        raise RuntimeError("M45 menu categories are not intact")
    (directory/PACKAGE).write_bytes(payload)
    compile_scripts(directory/SCRIPT)
    return {
        "status":"MAC_GAME_VALIDATION_REQUIRED",
        "same_package_as_M49":True,
        "package_sha256":hashlib.sha256(payload).hexdigest(),
        "modules":len(SCRIPTS),
        "student_filter":"not enrolled in any class",
        "picker_max":"min(available seats, eligible candidate count)"
    }

if __name__=="__main__":
    if len(sys.argv)!=2:
        raise SystemExit("Usage: python -m tooling.build_m50_filtered_cap <dir>")
    print(json.dumps(release(sys.argv[1]),indent=2))
