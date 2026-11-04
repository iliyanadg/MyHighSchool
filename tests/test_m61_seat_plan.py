"""M61 offline regression for school seat planning."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'/'m58_selection'))
from mhs61_seat_plan import plan_seats

class M61Tests(unittest.TestCase):
    def test_only_missing_get_vacant_seat(self):
        r=plan_seats(range(1,17),(1,2,3,4),seat_count=6)
        self.assertEqual(r['candidates'],tuple(str(i) for i in range(5,11)))
        self.assertEqual(len(r['not_yet_assigned']),6)
        self.assertEqual(r['mode'],'PLAN_ONLY_NO_EA_MUTATION')
    def test_never_double_assign_playable_or_role_occupied(self):
        r=plan_seats((1,2,3,4,5),(),playable_ids=(1,2),occupied_ids=(3,),seat_count=6)
        self.assertEqual(r['candidates'],('4','5'))
    def test_never_overbook_or_guess_more_than_six_slots(self):
        with self.assertRaises(ValueError):
            plan_seats((1,),(),seat_count=7)
        with self.assertRaises(ValueError):
            plan_seats((1,1),())
        self.assertEqual(plan_seats((1,2),(),seat_count=0)['candidates'],())
if __name__=='__main__':
    unittest.main()
