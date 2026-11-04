"""M87 check capacity before any live student selection."""
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'/'m87_roster'))
from mhs87_seat_allocation import allocate
A=tuple(str(i) for i in range(1,9))
B=tuple(str(i) for i in range(9,17))
def run(**changes):
    opts=dict(class1=A,class2=B,playable=('1','9'),
              core_role_members=('2','10'),
              ea_eligible=tuple(str(i) for i in range(1,17)),
              base_slot_count=6)
    opts.update(changes)
    return allocate(**opts)

class SeatTests(unittest.TestCase):
    def test_six_vanilla_base_jobs_cannot_host_twelve_npcs(self):
        x=run()
        self.assertEqual(x['status'],'BLOCKED')
        self.assertEqual(x['required_base_npcs'],12)
    def test_verified_extra_six_slots_produce_only_a_plan(self):
        x=run(base_slot_count=12)
        self.assertEqual(x['status'],'PLAN_ONLY')
        self.assertEqual(len(x['base_job_candidates']),12)
        self.assertFalse(x['changes_to_ea'])
    def test_duplicate_classmates_block(self):
        self.assertEqual(run(class2=A)['status'],'BLOCKED')
    def test_core_roles_not_double_counted(self):
        self.assertEqual(run(core_role_members=('1',))['status'],'BLOCKED')
    def test_ea_filter_must_accept_every_npc(self):
        self.assertEqual(run(ea_eligible=('3',),base_slot_count=20)['status'],'BLOCKED')
    def test_never_change_ea_through_this_module(self):
        src=(ROOT/'src'/'m87_roster'/'mhs87_seat_allocation.py').read_text()
        for forbidden in ('import services','create_situation(', 'setattr(',
                          'add_guest_info(','set_trait(', 'sim_constraints'):
            self.assertNotIn(forbidden,src)
if __name__=='__main__':
    unittest.main()
