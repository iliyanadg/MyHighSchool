"""Regression checks for the exact package exported by the user via Lot51.

This is *not* a playable mod: it contains a category and its SimData ONLY.
"""
import hashlib
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / 'tests' / 'fixtures' / 'lot51_category_only.dbpf'
spec = importlib.util.spec_from_file_location(
    'simdata_gate_real_export', ROOT / 'tooling' / 'simdata_release_gate.py')
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)
EXPECTED_SHA256 = 'ab2ecb3c51485d27f12dfbe5844df5e610e486abe88dce2395f1872872b53c3c'
EXPECTED_INSTANCE = 14567074618947653827


class Lot51RealExportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contents = FIXTURE.read_bytes()
        cls.records = gate.resources(cls.contents)

    def test_same_file_as_user_export(self):
        self.assertEqual(hashlib.sha256(self.contents).hexdigest(), EXPECTED_SHA256)

    def test_contains_only_two_resources(self):
        self.assertEqual(len(self.records), 2)
        self.assertEqual({r[0] for r in self.records},
                         {gate.TYPE_CATEGORY, gate.TYPE_SIMDATA})

    def test_tuning_and_simdata_have_same_instance(self):
        self.assertEqual({r[2] for r in self.records}, {EXPECTED_INSTANCE})

    def test_simdata_is_binary(self):
        data = next(r for r in self.records if r[0] == gate.TYPE_SIMDATA)
        self.assertEqual(data[1], 0x00E9D967)
        self.assertTrue(data[3].startswith(b'DATA'))

    def test_release_gate_structural_checks_pass(self):
        result = gate.inspect_bytes(self.contents)
        self.assertEqual(result['status'], 'STATIC_GATE_PASSED')
        self.assertEqual(result['category_count'], 1)
        self.assertEqual(result['simdata_count'], 1)

    def test_not_a_playable_menu(self):
        types = {r[0] for r in self.records}
        self.assertNotIn(0xE882D22F, types)  # Interaction tuning
        self.assertNotIn(0x220557DA, types)  # STBL strings


if __name__ == '__main__':
    unittest.main()
