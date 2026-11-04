import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src' / 'm147_integrated'))
from mhs147_class_timing_policy import can_early_request, preparation_period

CLASS1 = [{'situation_guid': 293815, 'job_guid': 277919,
           'is_preparation': True}]
CLASS1_ALT = [{'situation_guid': 304701, 'job_guid': 277919,
               'is_preparation': True}]
CLASS2 = [{'situation_guid': 297774, 'job_guid': 277919,
           'is_preparation': True}]

class NativeSchoolPreparations(unittest.TestCase):
    def test_both_classes_native_preparations(self):
        for h in (9, 13):
            c = {'hour': h, 'minute': 35}
            self.assertTrue(can_early_request(1, CLASS1, c, '', False)[0])
            self.assertTrue(can_early_request(1, CLASS1_ALT, c, '', False)[0])
            self.assertTrue(can_early_request(2, CLASS2, c, '', False)[0])

    def test_no_cross_class_role(self):
        c = {'hour': 13, 'minute': 35}
        self.assertFalse(can_early_request(1, CLASS2, c, '', False)[0])
        self.assertFalse(can_early_request(2, CLASS1, c, '', False)[0])

    def test_no_late_school_push(self):
        for hour, minute in ((10, 0), (14, 1), (15, 0)):
            c = {'hour': hour, 'minute': minute}
            self.assertFalse(can_early_request(1, CLASS1, c, '', False)[0])
            self.assertFalse(can_early_request(2, CLASS2, c, '', False)[0])

    def test_duplicate_and_protected_action(self):
        c = {'hour': 9, 'minute': 35}
        self.assertFalse(can_early_request(1, CLASS1, c, '', True)[0])
        self.assertFalse(can_early_request(
            1, CLASS1, c, 'super_HighSchool_Active_Whiteboard_Attend_Art',
            False)[0])

if __name__ == '__main__':
    unittest.main()
