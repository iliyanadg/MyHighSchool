"""Three previously uncertain M1 patterns now have direct sample counterparts."""
import importlib.util
from pathlib import Path
import unittest

root = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("m1audit", root / "tooling" / "m1_schema_review.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class ReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.x = m.inspect()

    def test_pickers_are_native(self):
        for klass in (1, 2):
            self.assertEqual(m.ET.parse(m.F / ("ChooseClass%d.xml" % klass)).getroot().get("c"),
                             "SimPickerInteraction")

    def test_both_classes_have_three_supported_patterns(self):
        self.assertEqual({v["class"] for v in self.x["supported_patterns"]}, {1, 2})
        self.assertEqual(len(self.x["supported_patterns"]), 6)

    def test_teen_sim_info_has_sonozaki_exemplar(self):
        self.assertEqual(sum(v["pattern"] == "PICKEDSIM_SIM_INFO_TEEN"
                             for v in self.x["supported_patterns"]), 2)

    def test_notification_title_has_ea_exemplar(self):
        self.assertEqual(sum(v["pattern"] == "NOTIFICATION_TITLE"
                             for v in self.x["supported_patterns"]), 2)

    def test_notification_timing_has_ea_exemplar(self):
        self.assertEqual(sum(v["pattern"] == "NOTIFICATION_TIMING_AT_BEGINNING"
                             for v in self.x["supported_patterns"]), 2)

    def test_tdesc_version_gap_remains(self):
        self.assertEqual(self.x["ea_version"], "1.129.39.1230")
        self.assertEqual(self.x["lot51_tdesc_version"], "1.128.90")

    def test_release_still_blocked(self):
        self.assertFalse(self.x["release_ready"])
        self.assertEqual(self.x["status"], "PATTERNS_SUPPORTED_NOT_GAME_VALIDATED")
        self.assertGreaterEqual(len(self.x["open_checks"]), 3)

    def test_two_distinct_picker_sources(self):
        a = m.ET.parse(m.F / "ChooseClass1.xml").getroot()
        b = m.ET.parse(m.F / "ChooseClass2.xml").getroot()
        self.assertNotEqual(a.get("s"), b.get("s"))


if __name__ == "__main__":
    unittest.main()
