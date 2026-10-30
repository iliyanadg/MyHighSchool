"""Test offline: non importano API EA e non verificano l'avvio del gioco."""
from pathlib import Path
import importlib.util
import unittest

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "src" / "legacy_v1_6" / "mhs_registry.py"
spec = importlib.util.spec_from_file_location("mhs_registry_tested", PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
SchoolRoster = module.SchoolRoster
RosterError = module.RosterError


class RosterTests(unittest.TestCase):
    def test_two_classes_defaults(self):
        r = SchoolRoster("test-save")
        self.assertEqual(r.capacities, {1: 8, 2: 8})

    def test_no_more_than_eight_in_class(self):
        r = SchoolRoster("test-save")
        for i in range(1, 9):
            self.assertTrue(r.enroll(str(i), 1, True))
        with self.assertRaises(RosterError):
            r.enroll("9", 1, True)

    def test_can_use_three_classes_explicitly(self):
        r = SchoolRoster("test-save", capacities={1: 8, 2: 8, 3: 8})
        self.assertTrue(r.enroll("100", 3, True))
        self.assertEqual(r.list_class(3), ["100"])

    def test_prevent_nonteen(self):
        r = SchoolRoster("test-save")
        with self.assertRaises(RosterError):
            r.enroll("99", 1, False)

    def test_save_isolated_by_key(self):
        a = SchoolRoster("save-a")
        b = SchoolRoster("save-b")
        a.enroll("100", 1, True)
        self.assertEqual(b.assignments, {})

    def test_serialization_roundtrip(self):
        a = SchoolRoster("save-a")
        a.enroll("123", 2, True)
        b = SchoolRoster.from_json(a.to_json())
        self.assertEqual(a.to_dict(), b.to_dict())

    def test_graduation_frees_seat(self):
        r = SchoolRoster("test-save")
        r.enroll("123", 1, True)
        self.assertTrue(r.graduate("123"))
        self.assertEqual(r.list_class(1), [])
        self.assertEqual(len(r.alumni), 1)


if __name__ == "__main__":
    unittest.main()
