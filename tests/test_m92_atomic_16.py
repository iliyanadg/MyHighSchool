import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'/'m92_full_roster'))
from mhs92_atomic_16 import full_cohort_plan
class Manifest:
    class_ids=(tuple(str(i) for i in range(1,9)),
               tuple(str(i) for i in range(9,17)))
    all_student_ids=frozenset(str(i) for i in range(1,17))
    active_household_teens=frozenset(('1','9'))
def plan(**kw):
    d=dict(manifest=Manifest(),eligible_npc_ids=tuple(str(i) for i in range(1,17)),
           playable_present_ids=('1','9'),core_role_ids=('2','10'),
           base_job_slots=12,phase1_slots=8,phase2_slots=8,
           zone_cap_free_or_reserved=16,ea_filters_verified=True)
    d.update(kw)
    return full_cohort_plan(**d)
class TestAtomic16(unittest.TestCase):
    def test_all_sixteen_simultaneously(self):
        r=plan()
        self.assertEqual(r['status'],'READY_FOR_ADAPTER')
        self.assertEqual(len(r['all_16']),16)
        self.assertEqual(len(r['normal_npcs']),12)
        self.assertFalse(r['changes_to_ea'])
    def test_two_real_core_roles_are_counted_inside_sixteen(self):
        r=plan(core_role_jobs={278965:'2',278966:'10'})
        self.assertEqual(r['status'],'READY_FOR_ADAPTER')
        self.assertEqual(r['playable_count'],2)
        self.assertEqual(r['core_count'],2)
        self.assertEqual(r['base_invites_needed'],12)
        self.assertTrue(r['core_jobs_verified'])

    def test_five_possible_core_roles_are_not_auto_counted(self):
        r=plan(core_role_ids=(),core_role_jobs={},base_job_slots=14)
        self.assertEqual(r['status'],'READY_FOR_ADAPTER')
        self.assertEqual(r['base_invites_needed'],14)
        self.assertEqual(r['core_count'],0)

    def test_five_observed_core_roles_need_nine_base_invites(self):
        roles={278965:'2',278966:'3',278967:'4',278968:'10',303765:'11'}
        r=plan(core_role_ids=('2','3','4','10','11'),
               core_role_jobs=roles,base_job_slots=9)
        self.assertEqual(r['status'],'READY_FOR_ADAPTER')
        self.assertEqual(r['base_invites_needed'],9)

    def test_unenrolled_core_role_blocks_the_entire_cohort(self):
        r=plan(core_role_jobs={278965:'2',278966:'99'})
        self.assertEqual(r['status'],'BLOCKED')

    def test_teachers_never_appear_in_special_student_roles(self):
        r=plan(core_role_jobs={277895:'2',278966:'10'})
        self.assertEqual(r['status'],'BLOCKED')

    def test_one_sim_cannot_fill_two_core_roles(self):
        r=plan(core_role_ids=('2',),
               core_role_jobs={278965:'2',278966:'2'})
        self.assertEqual(r['status'],'BLOCKED')

    def test_real_core_job_map_must_match_expected_roles(self):
        r=plan(core_role_jobs={278965:'2'})
        self.assertEqual(r['status'],'BLOCKED')

    def test_no_partial_six_of_sixteen(self):
        self.assertEqual(plan(base_job_slots=6)['status'],'BLOCKED')
    def test_both_classes_must_have_eight_seats(self):
        self.assertEqual(plan(phase2_slots=7)['status'],'BLOCKED')
    def test_global_zone_population_capacity(self):
        self.assertEqual(plan(zone_cap_free_or_reserved=15)['status'],'BLOCKED')
    def test_unknown_filter_fails_closed(self):
        self.assertEqual(plan(ea_filters_verified=False)['status'],'BLOCKED')
    def test_missing_playable_fails_closed(self):
        self.assertEqual(plan(playable_present_ids=('1',))['status'],'BLOCKED')
if __name__=='__main__':
    unittest.main()
