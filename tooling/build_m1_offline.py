"""M1 offline-only DBPF assembly from the exact user-exported Lot51 category.

This script DOES NOT establish game compatibility. Do not install the output
in The Sims 4: the picker and injector still need runtime verification.

The category and binary SimData come from the Lot51 export, byte-preserved
after decompression. All other tuning and STBL resources are ORIGINAL MHS.
"""
import collections
import hashlib
from pathlib import Path
import struct
import xml.etree.ElementTree as ET
import zlib

from tooling.simdata_release_gate import inspect_bytes, resources
from tooling.m1_links_and_strings import check_links, compile_stbl, parse_stbl
from tooling.m1_mailbox_validation import validate_injector
from tooling.lot51_source_pair import check_pair

ROOT = Path(__file__).resolve().parents[1]
M1 = ROOT / "src" / "experiments" / "m1_unbuilt"
BASE = ROOT / "tests" / "fixtures" / "lot51_category_only.dbpf"
BASE_SHA256 = "ab2ecb3c51485d27f12dfbe5844df5e610e486abe88dce2395f1872872b53c3c"
TYPE_INTERACTION = 0xE882D22F
TYPE_SNIPPET = 0x7DF2169C
TYPE_STBL = 0x220557DA
CATEGORY_INSTANCE = 14567074618947653827
ENTRY = struct.Struct("<IIIIIIIHH")


class BuildError(ValueError):
    pass


def _xml_resource(path, typ, group=0):
    blob = path.read_bytes()
    root = ET.fromstring(blob)
    try:
        instance = int(root.attrib["s"])
    except (ValueError, KeyError) as exc:
        raise BuildError("Bad tuning instance in " + str(path)) from exc
    return (typ, group, instance, blob)


def build_m1_bytes():
    """Return a combined test DBPF in memory; never install automatically."""
    if check_links()["status"] != "SOURCE_LINKS_COMPLETE_NOT_GAME_VALIDATED":
        raise BuildError("M1 source links invalid")
    if validate_injector()["status"] != "STATIC_SCHEMA_SHAPE_ONLY":
        raise BuildError("M1 injector verification failed")
    check_pair()
    base = BASE.read_bytes()
    if hashlib.sha256(base).hexdigest() != BASE_SHA256:
        raise BuildError("Lot51 category export changed")
    original = resources(base)
    if len(original) != 2:
        raise BuildError("Lot51 export must have exactly two resources")
    entries = list(original)
    for klass in (1, 2):
        entries.append(_xml_resource(M1 / ("ChooseClass%d.xml" % klass), TYPE_INTERACTION))
        entries.append(_xml_resource(M1 / ("ConfirmClass%d.xml" % klass), TYPE_INTERACTION))
    entries.append(_xml_resource(M1 / "Injector.xml", TYPE_SNIPPET))
    for locale in ("en", "it"):
        instance, data = compile_stbl(locale)
        if len(parse_stbl(data)) != 9:
            raise BuildError("STBL count mismatch")
        entries.append((TYPE_STBL, 0x80000000, instance, data))

    keys = [(ty, group, instance) for ty, group, instance, data in entries]
    if len(keys) != len(set(keys)):
        raise BuildError("Duplicate resource TGI")
    expected_counts = {0x03E9D964: 1, 0x545AC67A: 1,
                       TYPE_INTERACTION: 4, TYPE_SNIPPET: 1, TYPE_STBL: 2}
    if dict(collections.Counter(ty for ty, group, instance, data in entries)) != expected_counts:
        raise BuildError("Unexpected resource inventory")

    # Preserve the header layout of the Lot51-generated package rather
    # than attempting to invent a fresh DBPF header.
    header = bytearray(base[:96])
    body = bytearray()
    index = bytearray(struct.pack("<I", 0))
    for ty, group, instance, raw in entries:
        zipped = zlib.compress(raw, 9)
        offset = len(header) + len(body)
        body.extend(zipped)
        index.extend(ENTRY.pack(ty, group, instance >> 32,
                                instance & 0xffffffff, offset,
                                len(zipped) | 0x80000000,
                                len(raw), 0x5A42, 1))
    index_offset = len(header) + len(body)
    struct.pack_into("<I", header, 0x24, len(entries))
    struct.pack_into("<I", header, 0x2C, len(index))
    struct.pack_into("<I", header, 0x3C, index_offset)
    struct.pack_into("<Q", header, 0x40, index_offset)
    result = bytes(header + body + index)
    restored = resources(result)
    if restored != entries:
        raise BuildError("DBPF roundtrip changed original resource payload")
    checked = inspect_bytes(result)
    if checked["status"] != "STATIC_GATE_PASSED":
        raise BuildError("SimData structural gate blocked package")
    return result


def report():
    payload = build_m1_bytes()
    parsed = resources(payload)
    counts = collections.Counter(hex(ty) for ty, group, iid, raw in parsed)
    return {
        "result": "OFFLINE_ONLY_NOT_READY_FOR_MODS",
        "total_resources": len(parsed),
        "resource_types": dict(sorted(counts.items())),
        "bytes": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "category_id": CATEGORY_INSTANCE,
        "source": "Lot51 user's binary category + original MHS XML and STBL",
        "limits": "Static DBPF roundtrip only; no game load or in-game menu verified"
    }


if __name__ == "__main__":
    import json
    print(json.dumps(report(), indent=2))
