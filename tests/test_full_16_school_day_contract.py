"""Full-day 16-student integration contract against the actual EA role split.

This is NOT a release or a runtime adapter. It proves the ENGINEERING
PRECONDITIONS for 16 students: 3 household teens, 5 explicitly allocated
EA core-role students and 8 ordinary NPC slots, rather than using 16
Base requests and accidentally producing 21+ teens. The current vanilla
EA school schedule declares 6 Base situation requests, subject to
household reduction, so it cannot satisfy that plan unmodified.
"""
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT=Path(__file__).resolve().parents[1]
for subdir in ('m92_full_roster','m96_scheduler','m97_core_reservations','m93_core'):
    sys.path.insert(0,str(ROOT/'src'/subdir))
from mhs92_atomic_16 import full_cohort_plan
from mhs96_exact_school_count import approved_base_count
from mhs97_early_role_plan import CORE_JOB_ORDER,early_role_plan

GROUPS=(tuple(str(i) for i in range(1,9)),
        tuple(str(i) for i in range(9,17)))
ALL=GROUPS[0]+GROUPS[1]
PLAYED=('1','9','10')
CORE=('2','3','4','11','12')
NORMAL=tuple(x for x in ALL if x not in set(PLAYED+CORE))
JOBS=dict(zip(CORE_JOB_ORDER,CORE))

class CompleteSchoolDayContract(unittest.TestCase):
    def manifest(self):
        return SimpleNamespace(
            class_ids=GROUPS,all_student_ids=frozenset(ALL),
            active_household_teens=frozenset(PLAYED))
    def plan(self,base=8,phase1=8,phase2=8,student_seats=16,
             eligible=True,jobs=None):
        return full_cohort_plan(
            self.manifest(),NORMAL if eligible else (),PLAYED,CORE,
            base,phase1,phase2,student_seats,
            ea_filters_verified=True,
            core_role_jobs=JOBS if jobs is None else jobs)

    def test_exact_school_population_is_3_playable_plus_5_core_plus_8_base(self):
        self.assertEqual((len(PLAYED),len(CORE),len(NORMAL)),(3,5,8))
        p=self.plan()
        self.assertEqual(p['status'],'READY_FOR_ADAPTER')
        self.assertEqual(p['playable_count'],3)
        self.assertEqual(p['core_count'],5)
        self.assertEqual(p['base_invites_needed'],8)
        self.assertEqual(len(p['all_16']),16)
        # READY_FOR_ADAPTER is NOT permission to patch EA schedule:
        # five original core roles must first be bound and reserved.
        self.assertIsNone(approved_base_count(277657,277733,p))
        self.assertIsNone(approved_base_count(279958,277733,p))

    def test_do_not_create_13_or_16_base_situations_on_top_of_five_core(self):
        self.assertEqual(self.plan(base=6)['status'],'BLOCKED')
        p=self.plan(base=16)
        self.assertEqual(p['base_invites_needed'],8)
        self.assertNotEqual(p['base_invites_needed'],16)
        # A hypothetical future binding proof can authorize exactly 8,
        # never the whole enrollment count as extra NPCs.
        p=dict(p,core_roles_reserved_before_ea=True)
        self.assertEqual(approved_base_count(277657,277733,p),(8,8))

    def test_class1_six_vanilla_is_insufficient_for_eight(self):
        self.assertEqual(self.plan(phase1=6)['status'],'BLOCKED')
        self.assertEqual(self.plan(phase1=8)['status'],'READY_FOR_ADAPTER')
        self.assertEqual(self.plan(phase2=7)['status'],'BLOCKED')

    def test_capacity_unknown_and_missing_special_assignment_block_release(self):
        self.assertEqual(self.plan(student_seats=15)['status'],'BLOCKED')
        self.assertEqual(self.plan(student_seats=None)['status'],'BLOCKED')
        self.assertEqual(self.plan(jobs={})['status'],'BLOCKED')
        self.assertEqual(self.plan(eligible=False)['status'],'BLOCKED')

    def test_early_role_plan_is_not_actual_ea_binding(self):
        eligible={job:(sid,) for job,sid in JOBS.items()}
        p=early_role_plan(GROUPS,PLAYED,JOBS,eligible)
        self.assertEqual(p['status'],'EARLY_ROLE_PLAN_VALIDATED_NOT_EA_BOUND')
        self.assertFalse(p['role_binding_confirmed'])
        self.assertEqual(p['base_invites_needed'],8)
        self.assertEqual(len(p['role_reservations']),5)

if __name__=='__main__':
    unittest.main()
