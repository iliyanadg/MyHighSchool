"""Offline gate for a The Sims 4 pie-menu package.

This intentionally rejects incomplete packages before a human game test. It
cannot certify EA tuning schemas or actual The Sims 4 startup compatibility.
"""
import argparse
import json
import struct
import xml.etree.ElementTree as ET
import zlib
from pathlib import Path

TYPE_CATEGORY = 0x03E9D964
TYPE_SIMDATA = 0x545AC67A
INDEX_ENTRY = struct.Struct('<IIIIIIIHH')

class PackageError(ValueError):
    pass


def resources(blob):
    if len(blob) < 96 or blob[:4] != b'DBPF':
        raise PackageError('Not a DBPF file or truncated header')
    major, minor = struct.unpack_from('<II', blob, 0x04)
    if (major, minor) != (2, 1):
        raise PackageError('Expected The Sims 4 DBPF version 2.1')
    index_minor = struct.unpack_from('<I', blob, 0x3C)[0]
    if index_minor != 3:
        raise PackageError('Unsupported DBPF index minor version (expected 3)')
    total = struct.unpack_from('<I', blob, 0x24)[0]
    index_size = struct.unpack_from('<I', blob, 0x2c)[0]
    index_offset_short = struct.unpack_from('<I', blob, 0x28)[0]
    index_offset_long = struct.unpack_from('<Q', blob, 0x40)[0]
    index_offset = index_offset_short if index_offset_short else index_offset_long
    if total > 100000 or index_offset < 96 or index_offset > len(blob):
        raise PackageError('Bad package index information')
    if index_size != 4 + total * INDEX_ENTRY.size or index_offset + index_size > len(blob):
        raise PackageError('Unsupported or corrupted DBPF index format')
    if struct.unpack_from('<I', blob, index_offset)[0] != 0:
        raise PackageError('Unsupported DBPF common index')
    seen = set()
    result = []
    for number in range(total):
        typ, group, hi, lo, offset, size, raw_size, compression, flags = INDEX_ENTRY.unpack_from(blob, index_offset+4+number*INDEX_ENTRY.size)
        instance = (hi << 32) | lo
        key = (typ, group, instance)
        if key in seen:
            raise PackageError('Duplicate resource key at index {}'.format(number))
        seen.add(key)
        compressed = bool(size & 0x80000000)
        stored_size = size & 0x7fffffff
        if offset < 96 or offset + stored_size > index_offset:
            raise PackageError('Resource outside data section')
        payload = blob[offset:offset+stored_size]
        if compressed:
            if compression != 0x5A42:
                raise PackageError('Unsupported compression {:04x}'.format(compression))
            try:
                payload = zlib.decompress(payload)
            except zlib.error:
                raise PackageError('Damaged zlib resource')
            if len(payload) != raw_size:
                raise PackageError('Incorrect decompressed size')
        result.append((typ, group, instance, payload))
    return result


def inspect_bytes(blob):
    records = resources(blob)
    categories = [r for r in records if r[0] == TYPE_CATEGORY]
    data_by_instance = {}
    for typ, group, instance, content in records:
        if typ == TYPE_SIMDATA:
            data_by_instance.setdefault(instance, []).append(content)
    findings = []
    for typ, group, instance, xml in categories:
        try:
            root = ET.fromstring(xml)
        except ET.ParseError:
            findings.append({'category': str(instance), 'code': 'CATEGORY_XML_INVALID'})
            continue
        if root.tag != 'I' or root.attrib.get('c') != 'PieMenuCategory':
            findings.append({'category': str(instance), 'code': 'CATEGORY_TUNING_TYPE_INVALID'})
        if root.attrib.get('s') != str(instance):
            findings.append({'category': str(instance), 'code': 'CATEGORY_ID_MISMATCH'})
        companions = data_by_instance.get(instance, [])
        if not companions:
            findings.append({'category': str(instance), 'code': 'MISSING_SIMDATA'})
        elif not any(content.startswith(b'DATA') and len(content) >= 64 for content in companions):
            findings.append({'category': str(instance), 'code': 'SIMDATA_HEADER_INVALID'})
    return {'status': 'BLOCKED' if findings else 'STATIC_GATE_PASSED',
            'resource_count': len(records), 'category_count': len(categories),
            'simdata_count': sum(r[0] == TYPE_SIMDATA for r in records),
            'findings': findings,
            'limits': 'Static structural checks only; not a Sims 4 game-load validation.'}


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('package',type=Path)
    args=ap.parse_args()
    try:
        result=inspect_bytes(args.package.read_bytes())
    except (OSError,PackageError) as exc:
        ap.exit(2,'CANNOT AUDIT: {}\n'.format(exc))
    print(json.dumps(result,indent=2))
    if result['status']=='BLOCKED':
        ap.exit(1)

if __name__=='__main__':
    main()
