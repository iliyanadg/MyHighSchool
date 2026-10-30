"""Offline unit tests; NEVER imply a playable game build was validated."""
import importlib.util
from pathlib import Path
import struct
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'tooling' / 'package_audit.py'
spec = importlib.util.spec_from_file_location('package_audit_under_test', SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def fixture(resources):
    """Produce a deliberately small synthetic DBPF for auditing the index only."""
    header = bytearray(96)
    header[:4] = b'DBPF'
    struct.pack_into('<II', header, 4, 2, 1)
    struct.pack_into('<I', header, 0x24, len(resources))
    data = bytearray()
    index = bytearray(struct.pack('<I', 0))
    for kind, instance in resources:
        offset = 96 + len(data)
        data.extend(b'FAKE')
        index.extend(mod.ENTRY.pack(kind, 0, instance >> 32, instance & 0xffffffff,
                                    offset, 4, 4, 0, 0))
    struct.pack_into('<I', header, 0x2c, len(index))
    struct.pack_into('<Q', header, 0x40, 96 + len(data))
    return bytes(header + data + index)


class PackageAuditTests(unittest.TestCase):
    def test_complete_category_pair(self):
        data = fixture([(mod.TYPE_CATEGORY, 23), (mod.TYPE_SIMDATA, 23)])
        result = mod.inspect_package(data)
        self.assertEqual(result['resource_count'], 2)
        self.assertEqual(result['missing_category_simdata'], [])

    def test_m0_style_missing_simdata_is_flagged(self):
        data = fixture([(mod.TYPE_CATEGORY, 23)])
        result = mod.inspect_package(data)
        self.assertEqual(result['missing_category_simdata'], ['23'])
        self.assertEqual(len(result['warnings']), 1)

    def test_bad_header_is_rejected(self):
        with self.assertRaises(mod.PackageError):
            mod.inspect_package(b'not-a-package')

    def test_duplicate_resource_is_rejected(self):
        with self.assertRaises(mod.PackageError):
            mod.inspect_package(fixture([(mod.TYPE_CATEGORY, 5), (mod.TYPE_CATEGORY, 5)]))

    def test_truncated_index_is_rejected(self):
        with self.assertRaises(mod.PackageError):
            mod.inspect_package(fixture([(mod.TYPE_CATEGORY, 23)])[:-4])

    def test_bad_payload_range_is_rejected(self):
        data = bytearray(fixture([(mod.TYPE_CATEGORY, 23)]))
        offset_index = struct.unpack_from('<Q', data, 0x40)[0]
        struct.pack_into('<I', data, offset_index + 4 + 16, offset_index + 99)
        with self.assertRaises(mod.PackageError):
            mod.inspect_package(data)


if __name__ == '__main__':
    unittest.main()
