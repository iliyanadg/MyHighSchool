"""Full M1 DBPF assembled in memory and audited: no game validation."""
import hashlib
import importlib.util
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("m1_offline", ROOT/"tooling"/"build_m1_offline.py")
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class M1AssemblyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.package=m.build_m1_bytes()
        cls.entries=m.resources(cls.package)

    def test_nine_resources_total(self):
        self.assertEqual(len(self.entries),9)

    def test_all_resource_types_present(self):
        self.assertEqual({item[0] for item in self.entries},
                         {0x03E9D964,0x545AC67A,m.TYPE_INTERACTION,m.TYPE_SNIPPET,m.TYPE_STBL})

    def test_all_lot51_resources_preserved_exactly(self):
        original=m.resources(m.BASE.read_bytes())
        self.assertEqual(self.entries[:2],original)

    def test_category_and_binary_simdata_pair(self):
        self.assertEqual(self.entries[0][2],m.CATEGORY_INSTANCE)
        self.assertEqual(self.entries[1][2],m.CATEGORY_INSTANCE)
        self.assertTrue(self.entries[1][3].startswith(b"DATA"))

    def test_interactions_and_injector(self):
        self.assertEqual(sum(r[0]==m.TYPE_INTERACTION for r in self.entries),4)
        self.assertEqual(sum(r[0]==m.TYPE_SNIPPET for r in self.entries),1)

    def test_bilingual_nine_entry_stbl(self):
        stbl=[x for x in self.entries if x[0]==m.TYPE_STBL]
        self.assertEqual({x[2]>>56 for x in stbl},{0,0x0B})
        self.assertTrue(all(len(m.parse_stbl(x[3]))==9 for x in stbl))

    def test_each_resource_key_is_unique(self):
        keys=[(x[0],x[1],x[2]) for x in self.entries]
        self.assertEqual(len(keys),len(set(keys)))

    def test_full_package_passes_static_simdata_gate(self):
        self.assertEqual(m.inspect_bytes(self.package)["status"],"STATIC_GATE_PASSED")

    def test_reproducible_build_and_no_source_modification(self):
        original_hash=hashlib.sha256(m.BASE.read_bytes()).hexdigest()
        self.assertEqual(original_hash,m.BASE_SHA256)
        self.assertEqual(self.package,m.build_m1_bytes())
        self.assertEqual(hashlib.sha256(m.BASE.read_bytes()).hexdigest(),original_hash)

    def test_dbpf_index_minor_is_3_not_overwritten(self):
        import struct
        self.assertEqual(struct.unpack_from('<I', self.package, 0x3C)[0], 3)
        self.assertEqual(struct.unpack_from('<I', self.package, 0x28)[0], 0)
        self.assertGreater(struct.unpack_from('<Q', self.package, 0x40)[0], 96)

    def test_corrupt_dbpf_index_version_is_rejected(self):
        import struct
        invalid = bytearray(self.package)
        struct.pack_into('<I', invalid, 0x3C, struct.unpack_from('<I', invalid, 0x40)[0])
        with self.assertRaises(m.inspect_bytes.__globals__['PackageError']):
            m.inspect_bytes(bytes(invalid))

    def test_lot51_original_keeps_index_version_three(self):
        import struct
        self.assertEqual(struct.unpack_from('<I', m.BASE.read_bytes(), 0x3C)[0], 3)

    def test_no_game_load_claim(self):
        self.assertEqual(m.report()["result"],"OFFLINE_ONLY_NOT_READY_FOR_MODS")


if __name__=="__main__":
    unittest.main()
