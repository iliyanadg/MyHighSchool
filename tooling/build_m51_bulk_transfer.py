"""M51 end-to-end bulk transfer with M50 filtered enrollment, stable M45 menus.

M50 package remains byte-for-byte identical to the M49 Mac-verified menu.
M51 changes ONLY Python script mhs32_transfer_ui.py inside 17-module bundle.
It removes the old 'one Sim at a time + console commit' behavior from menu
actions. The native dialog allows selecting up to free seats in destination;
its checkmark rechecks the roster and saves all selected in ONE atomic change.
X cancels without changing JSON.

No new high-school attendance implementation. EP12 (High School Years) is
the exclusive target pack of the finished project; additional runtime pack
gate will be validated separately rather than guessing an EA API here.
"""
import hashlib
import json
import sys
from pathlib import Path

from tooling.build_m50_filtered_cap import package_bytes
from tooling.build_m48_single_checkmark import compile_scripts,SCRIPTS
from tooling.simdata_release_gate import inspect_bytes

PACKAGE="MHS_M51_ISCRIZIONI_E_TRASFERIMENTI_MULTIPLI_TEST.package"
SCRIPT="MHS_M51_ISCRIZIONI_E_TRASFERIMENTI_MULTIPLI_TEST.ts4script"


def release(directory):
    directory=Path(directory)
    directory.mkdir(parents=True,exist_ok=True)
    payload=package_bytes()
    check=inspect_bytes(payload)
    if check['status']!='STATIC_GATE_PASSED' or (
            check['category_count']!=5 or check['simdata_count']!=5):
        raise RuntimeError('Verified M45 category tree was modified')
    if not any(src.name=='mhs32_transfer_ui.py' for src in SCRIPTS):
        raise RuntimeError('M32 transfer module missing from archive')
    (directory/PACKAGE).write_bytes(payload)
    compile_scripts(directory/SCRIPT)
    return {
        "status":"MAC_GAME_TEST_REQUIRED",
        "same_dbpf_as_mac_verified_M49":True,
        "package_sha256":hashlib.sha256(payload).hexdigest(),
        "scripts":len(SCRIPTS),
        "single_step_multi_transfer":True,
        "transfer_capacity":8,
        "pack_target":"High School Years (EP12)"
    }


if __name__=="__main__":
    if len(sys.argv)!=2:
        raise SystemExit("Usage: python -m tooling.build_m51_bulk_transfer <output dir>")
    print(json.dumps(release(sys.argv[1]),indent=2))
