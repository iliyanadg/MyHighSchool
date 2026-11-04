"""Regression against EA source tuning XML extracted from the real game.

Do not let synthetic M108 tests pass if they assume a different school
creation order or classroom capacity than the actual EA resources.
"""
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

EA = Path(__file__).resolve().parents[1] / 'assets' / 'ea_2026_11_01'


def tuning(number):
    return ET.parse(str(EA / ('%s.xml' % number))).getroot()


class OriginalEANativeTuningTests(unittest.TestCase):
    def test_both_ea_school_schedules_create_base_before_core(self):
        for number in (277657, 279958):
            root = tuning(number)
            situations = []
            for row in root.findall("./L[@n='long_term_situations']/U"):
                entry = row.find("./T[@n='situation']")
                if entry is not None:
                    situations.append(int(entry.text.strip()))
            self.assertIn(277733, situations)
            self.assertIn(298052, situations)
            self.assertLess(situations.index(277733),
                            situations.index(298052),
                            msg='M108 must support Base-before-Core; schedule %s' % number)
            base = root.find("./L[@n='long_term_situations']/U[1]/U[@n='count']")
            self.assertEqual(int(base.find("./T[@n='lower_bound']").text), 6)
            self.assertEqual(int(base.find("./T[@n='upper_bound']").text), 6)

    def test_ea_class_one_still_has_six_npc_phase_slots(self):
        for number in (293642, 293644, 304561, 304563):
            root = tuning(number)
            upper = root.find(
                "./L[@n='job_assignments']/U/U[@n='sim_count']/T[@n='upper_bound']")
            self.assertIsNotNone(upper)
            self.assertEqual(int(upper.text), 6)

    def test_ea_other_class_has_eight_phase_slots_but_no_seat_proof(self):
        root = tuning(304570)
        assignment = root.find("./L[@n='job_assignments']/U")
        self.assertEqual(int(assignment.find("./T[@n='job']").text), 280777)
        self.assertEqual(
            int(assignment.find("./U[@n='sim_count']/T[@n='upper_bound']").text), 8)


if __name__ == '__main__':
    unittest.main()
