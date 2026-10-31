import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'/'m58_selection'))
sys.path.insert(0,str(ROOT/'src'/'m57_selection'))
sys.path.insert(0,str(ROOT/'src'/'m2_registry'))
sys.path.insert(0,str(ROOT/'src'/'m53_staff'))
from mhs58_base_plan import (plan_base_roster,M58PlanError,
                             BASE_STUDENT_SITUATION_COUNT,BASE_STUDENT_CAPACITY)
from mhs57_school_manifest import make_manifest
from mhs_m2_roster import SchoolRoster
from mhs53_staff_store import StaffRoster


def _manifest(teens=()):
    roster=SchoolRoster(11,{str(x):1 if x<=8 else 2 for x in range(1,17)})
    staff=StaffRoster(11,{'principal':'201','teacher1':'202','teacher2':'203',
                          'teacher3':None,'cafeteria':[],'custodians':[]})
    return make_manifest(roster,staff,2,teens)


class M58BasePlanTests(unittest.TestCase):
    def test_vanilla_six_base_job_slots_are_not_sixteen(self):
        self.assertEqual(BASE_STUDENT_SITUATION_COUNT,6)
        self.assertEqual(BASE_STUDENT_CAPACITY,6)
        p=plan_base_roster(_manifest())
        self.assertEqual(p['base_guest_ids'],tuple(str(i) for i in range(1,7)))
        self.assertEqual(len(p['overflow_ids']),10)
        self.assertTrue(p['requires_capacity_change'])
    def test_playable_no_duplicate_and_verified_core_reservation(self):
        p=plan_base_roster(_manifest(('1','2','16')),
                           core_roles={'cheer':'3','chess':'4'})
        self.assertEqual(p['playable_ids'],('1','2','16'))
        self.assertEqual(p['base_guest_ids'],tuple(str(i) for i in range(5,11)))
        self.assertEqual(len(p['overflow_ids']),5)
        self.assertEqual(p['core_roles'],{'cheer':'3','chess':'4'})
    def test_unknown_core_never_invented(self):
        p=plan_base_roster(_manifest())
        self.assertEqual(len(p['unassigned_core_slots']),5)
        self.assertEqual(p['core_roles'],{})
    def test_excluded_sim_never_invited(self):
        p=plan_base_roster(_manifest(),unavailable=('1',))
        self.assertEqual(p['base_guest_ids'],tuple(str(i) for i in range(2,8)))
        self.assertEqual(p['unavailable_ids'],('1',))
    def test_reject_unsafe_role_and_duplicates(self):
        m=_manifest(('1',))
        for kwargs in ({'core_roles':{'football':'1'}},
                       {'core_roles':{'unknown':'3'}},
                       {'core_roles':{'cheer':'3','chess':'3'}},
                       {'core_roles':{'mean':'999'}},
                       {'unavailable':('999',)}):
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(M58PlanError):
                    plan_base_roster(m,**kwargs)
    def test_never_spawn_or_persist(self):
        code=(ROOT/'src'/'m58_selection'/'mhs58_base_plan.py').read_text()
        for unsafe in ('create_situation(', 'add_trait(', 'os.remove(', 'open('):
            self.assertNotIn(unsafe,code)


if __name__=='__main__':
    unittest.main()
