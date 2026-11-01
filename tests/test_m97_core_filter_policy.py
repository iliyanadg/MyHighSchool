import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for loc in ('src/m97_core_reservations','src/m93_core'):
    sys.path.insert(0,str(ROOT/loc))
from mhs97_core_filter_policy import prepare_core_filter,FILTER_TO_JOB
from tests.test_m97_early_role_plan import make,ASSIGN

def choose(fid,plan=None,**kwargs):
    if plan is None:
        plan=make()
    settings=dict(zone_verified=True,save_verified=True,session_verified=True)
    settings.update(kwargs)
    return prepare_core_filter(plan,fid,**settings)

class TestM97SchoolCorePreselection(unittest.TestCase):
    def test_each_ea_filter_uses_one_correct_registered_role(self):
        for fid,job in FILTER_TO_JOB.items():
            action,ids,why=choose(fid)
            self.assertEqual(action,'constrain')
            self.assertEqual(ids,(int(ASSIGN[job]),))
            self.assertIn('registered',why)

    def test_chess_football_correct_real_mac_filter_ids(self):
        self.assertEqual(FILTER_TO_JOB[276596],278966)
        self.assertEqual(FILTER_TO_JOB[276594],278967)

    def test_not_active_on_home_zone_or_another_save(self):
        self.assertEqual(choose(276596,zone_verified=False)[0],'bypass')
        self.assertEqual(choose(276596,save_verified=False)[0],'bypass')
        self.assertEqual(choose(276596,session_verified=False)[0],'bypass')

    def test_unknown_filters_are_not_intercepted(self):
        self.assertEqual(choose(280516)[0],'bypass')
        self.assertEqual(choose(300742)[0],'bypass')

    def test_missing_role_blocks_instead_of_using_random_ea(self):
        p=dict(make())
        p['status']='BLOCKED'
        self.assertEqual(choose(276596,plan=p)[0],'block')

    def test_ea_explicit_sim_mismatch_is_not_ignored(self):
        self.assertEqual(choose(276596,sim_constraints=(99,))[0],'block')
        self.assertEqual(choose(276596,sim_constraints=(3,4))[1],(3,))

    def test_duplicate_or_wrong_extra_roles_cannot_be_constrained(self):
        p=dict(make())
        p['role_reservations']=tuple((j,'2') for j in ASSIGN)
        self.assertEqual(choose(276596,plan=p)[0],'block')
        p['role_reservations']=((277895,'2'),)
        self.assertEqual(choose(276596,plan=p)[0],'block')

if __name__=='__main__':
    unittest.main()
