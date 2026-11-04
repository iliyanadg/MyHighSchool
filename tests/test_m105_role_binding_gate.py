"""M105 EA actual school job membership is not just a filter invitation."""
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for loc in ('m105_day_controller',):
    sys.path.insert(0,str(ROOT/'src'/loc))
from mhs105_atomic_school_roster import CORE_JOBS,ALL_JOBS,plan_school_day
from mhs105_role_binding_gate import verify_core_membership

CLASSES=(tuple(str(i) for i in range(1,9)),
         tuple(str(i) for i in range(9,17)))
PLAYED=('1','9','10')
NPCS=tuple(s for group in CLASSES for s in group if s not in PLAYED)
PINNED=dict(zip(CORE_JOBS,('2','3','4','11','12')))
ELIGIBLE={job:NPCS for job in ALL_JOBS}
PLAN=plan_school_day(CLASSES,PLAYED,ELIGIBLE,PINNED)
MEMBERS={job:(int(sid),) for job,sid in PINNED.items()}
CTX={'observed_school_context':True,'observed_same_save':True,
     'observed_same_day':True,'observed_situation_is_ea_core':True,
     'observed_on_lot_ids':tuple(map(int,NPCS))}

class EACoreBindingProofTests(unittest.TestCase):
    def test_exact_five_live_members_verified_but_not_pre_spawn(self):
        proof=verify_core_membership(PLAN,MEMBERS,**CTX)
        self.assertEqual(proof['status'],
                         'FIVE_ACTUAL_EA_CORE_MEMBERS_VERIFIED')
        self.assertTrue(proof['actual_ea_core_binding_verified'])
        self.assertFalse(proof['before_school_spawn_reservation_proved'])
        self.assertFalse(proof['full_16_present_verified'])
        self.assertFalse(proof['eight_per_class_verified'])
        self.assertFalse(proof['mutated_ea'])

    def test_guest_filter_match_is_not_ea_membership(self):
        self.assertFalse(verify_core_membership(PLAN,None,**CTX)[
            'actual_ea_core_binding_verified'])
        self.assertFalse(verify_core_membership(
            PLAN,{'filtered_eligible':tuple(NPCS)},**CTX)[
                'actual_ea_core_binding_verified'])

    def test_wrong_role_unregistered_and_duplicate_fail(self):
        wrong=dict(MEMBERS);wrong[CORE_JOBS[0]]=(3,)
        self.assertFalse(verify_core_membership(
            PLAN,wrong,**CTX)['actual_ea_core_binding_verified'])
        stranger=dict(MEMBERS);stranger[CORE_JOBS[0]]=(9999999,)
        self.assertFalse(verify_core_membership(
            PLAN,stranger,**CTX)['actual_ea_core_binding_verified'])
        two=dict(MEMBERS);two[CORE_JOBS[0]]=(2,3)
        self.assertFalse(verify_core_membership(
            PLAN,two,**CTX)['actual_ea_core_binding_verified'])

    def test_unknown_job_and_unsupported_live_membership_are_not_proof(self):
        data=dict(MEMBERS);del data[CORE_JOBS[0]]
        self.assertFalse(verify_core_membership(
            PLAN,data,**CTX)['actual_ea_core_binding_verified'])
        data=dict(MEMBERS);data[CORE_JOBS[0]]=None
        self.assertFalse(verify_core_membership(
            PLAN,data,**CTX)['actual_ea_core_binding_verified'])

    def test_no_non_school_context_and_wrong_day_or_save(self):
        for key in ('observed_school_context','observed_same_save',
                    'observed_same_day','observed_situation_is_ea_core'):
            bad=dict(CTX);bad[key]=False
            self.assertFalse(verify_core_membership(
                PLAN,MEMBERS,**bad)['actual_ea_core_binding_verified'])

    def test_on_lot_ids_required_and_all_five_must_arrive(self):
        missing=dict(CTX);missing['observed_on_lot_ids']=None
        self.assertFalse(verify_core_membership(
            PLAN,MEMBERS,**missing)['actual_ea_core_binding_verified'])
        missing=dict(CTX);missing['observed_on_lot_ids']=(2,3,4,11)
        self.assertFalse(verify_core_membership(
            PLAN,MEMBERS,**missing)['actual_ea_core_binding_verified'])

    def test_suggestions_do_not_count_as_confirmed_assignments(self):
        suggestion=plan_school_day(CLASSES,PLAYED,ELIGIBLE,
                                   propose_missing_roles=True)
        self.assertFalse(verify_core_membership(
            suggestion,MEMBERS,**CTX)['actual_ea_core_binding_verified'])

if __name__=='__main__':
    unittest.main()
