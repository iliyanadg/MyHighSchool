"""Read-only inspection of The Sims 4 DBPF packages.

Does not load game resources or prove that a package will start The Sims 4.
Uses a conservative, format-specific interpretation of the index used by M0.
"""
import argparse
import json
from pathlib import Path
import struct

TYPE_CATEGORY = 0x03E9D964
TYPE_SIMDATA = 0x545AC67A
ENTRY = struct.Struct('<IIIIIIIHH')


class PackageError(ValueError):
    pass


def inspect_package(blob):
    if len(blob) < 96 or blob[:4] != b'DBPF':
        raise PackageError('DBPF header missing or truncated')
    n = struct.unpack_from('<I', blob, 0x24)[0]
    index_size = struct.unpack_from('<I', blob, 0x2C)[0]
    index_position = struct.unpack_from('<Q', blob, 0x40)[0]
    if n > 100000 or index_position < 96 or index_position > len(blob):
        raise PackageError('Invalid resource count or index offset')
    if index_size > len(blob) - index_position:
        raise PackageError('Index outside package')
    # The DBPF index used here has a four-byte index header followed by 32-byte entries.
    if index_size != 4 + ENTRY.size * n:
        raise PackageError('Unrecognised index format (no interpretation attempted)')
    records = []
    seen = set()
    for index in range(n):
        fields = ENTRY.unpack_from(blob, index_position + 4 + index * ENTRY.size)
        kind, group, hi, lo, offset, packed, unpacked, compression, flags = fields
        instance = (hi << 32) | lo
        key = (kind, group, instance)
        if key in seen:
            raise PackageError('Duplicate TGI at entry {}'.format(index))
        seen.add(key)
        packed_size = packed & 0x7fffffff
        if offset < 96 or offset + packed_size > index_position:
            raise PackageError('Payload outside data section at entry {}'.format(index))
        records.append({'type': '0x{:08X}'.format(kind), 'group': '0x{:08X}'.format(group),
                        'instance': str(instance), 'offset': offset, 'stored_size': packed_size,
                        'unpacked_size': unpacked, 'compressed': bool(packed & 0x80000000),
                        'compression': compression, 'flags': flags})
    groups = {}
    for record in records:
        groups.setdefault(record['type'], []).append(record['instance'])
    categories = set(groups.get('0x{:08X}'.format(TYPE_CATEGORY), []))
    simdata = set(groups.get('0x{:08X}'.format(TYPE_SIMDATA), []))
    missing = sorted(categories - simdata, key=int)
    return {'resource_count': n, 'resources_by_type': {k: len(v) for k,v in sorted(groups.items())},
            'missing_category_simdata': missing,
            'warnings': ['Menu category without matching SimData (comparison finding, not proven crash cause)'] if missing else []}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('package', type=Path, help='Read-only .package path, never modified')
    args = parser.parse_args()
    try:
        result = inspect_package(args.package.read_bytes())
    except (OSError, PackageError) as exc:
        parser.exit(2, 'Package audit unable to validate: {}\n'.format(exc))
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
