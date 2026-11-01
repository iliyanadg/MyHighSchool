"""M90 deterministic eligible selection tests."""
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'/'m90_selection'))
from mhs90_session import SelectionSession

class SelectionTests(unittest.TestCase):
    def test_exact_roster_order_and_no_repeats(self):
        s=SelectionSession((('10','20'),('30','40')),playable_ids=('10',))
        self.assertEqual(s.choose((10,20,30,40)),20)
        self.assertTrue(s.confirm(20))
        self.assertEqual(s.choose((10,20,30,40)),30)
        self.assertTrue(s.confirm(30))
        self.assertEqual(s.choose((10,20,30,40)),40)
    def test_do_not_select_unverified_or_existing_students(self):
        s=SelectionSession((('10','20'),),excluded_ids=('20',))
        self.assertIsNone(s.choose(('10',),physically_present_ids=('10',)))
        self.assertIsNone(s.choose(('20',)))
    def test_never_confirm_sim_not_in_roster(self):
        s=SelectionSession((('1',),))
        self.assertFalse(s.confirm(99))
        self.assertTrue(s.confirm(1))
        self.assertFalse(s.confirm(1))
    def test_duplicate_roster_rejected(self):
        with self.assertRaises(ValueError):
            SelectionSession((('1',),('1',)))
if __name__=='__main__':
    unittest.main()
