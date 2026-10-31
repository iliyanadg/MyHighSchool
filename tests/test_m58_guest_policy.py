import unittest
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'/'m58_selection'))
from mhs58_guest_policy import guest_list_decision,classify_situation


class M58GuestPolicyTests(unittest.TestCase):
    def test_known_situation_ids(self):
        self.assertEqual(classify_situation(277733),'student')
        self.assertEqual(classify_situation(298052),'core')
        self.assertEqual(classify_situation(298096),'venue')
        self.assertIsNone(classify_situation(280756))
    def test_preselection_requires_verified_school(self):
        args=(277733,[(277894,0)],['3','4'])
        self.assertEqual(guest_list_decision(*args,verified_school_zone=True)['action'],'candidate')
        self.assertEqual(guest_list_decision(*args)['action'],'preserve')
        self.assertEqual(guest_list_decision(*args,verified_school_zone=True,active=False)['action'],'preserve')
    def test_preserve_ea_guests_and_other_jobs(self):
        self.assertEqual(guest_list_decision(277733,[(277894,42)],['3'],True)['action'],'preserve')
        self.assertEqual(guest_list_decision(298052,[(277895,0)],['3'],True)['action'],'preserve')
        self.assertEqual(guest_list_decision(277733,[(277895,0)],['3'],True)['action'],'preserve')
    def test_empty_requests(self):
        self.assertEqual(guest_list_decision(277733,[],['3'],True)['action'],'observe')
        self.assertEqual(guest_list_decision(277733,[(277894,0)],[],True)['action'],'preserve')
    def test_no_live_api_calls(self):
        source=(Path(__file__).resolve().parents[1]/'src'/'m58_selection'/'mhs58_guest_policy.py').read_text()
        for fragment in ('create_situation(', 'setattr(', 'add_guest_info('):
            self.assertNotIn(fragment,source)


if __name__=='__main__':
    unittest.main()
