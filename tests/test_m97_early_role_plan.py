"""M97 explicit EA core role registry plan and live-binding checks."""
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for loc in ('src/m97_core_reservations','src/m93_core'):
    sys.path.insert(0,str(ROOT/loc))
from mhs97_early_role_plan import early_role_plan,validate_live_binding,CORE_JOB_ORDER

GROUPS=(tuple(str(i) for i in range(1,9)),
        tuple(str(i) for i in range(9,17)))
ASSIGN={278965:'2',278966:'3',278967:'4',278968:'10',303765:'11'}
ELIG={j:(sid,) for j,sid in ASSIGN.items()}

def make(**kwargs):
    values={'class_ids':GROUPS,'playable_ids':('1','9'),
            'assignments':dict(ASSIGN),'ea_eligible_ids_by_job':dict(ELIG)}
    values.update(kwargs)
    return early_role_plan(**values)

class TestM97Reservations(unittest.TestCase):
    def test_exact_five_roles_plus_playables_are_already_in_the_same_sixteen(self):
        plan=make()
        self.assertEqual(plan['status'],'EARLY_ROLE_PLAN_VALIDATED_NOT_EA_BOUND')
        self.assertEqual(plan['base_invites_needed'],9)
        self.assertEqual(len(plan['all_16']),16)
        self.assertEqual(len(plan['core']),5)
        self.assertEqual(len(plan['normal_npcs']),9)
        self.assertFalse(plan['changes_to_ea'])
        self.assertFalse(plan['role_binding_confirmed'])

    def test_no_automatic_guess_of_missing_special_role(self):
        roles=dict(ASSIGN)
        del roles[278967]
        self.assertEqual(make(assignments=roles)['status'],'BLOCKED')

    def test_unenrolled_core_student_cannot_enter_school(self):
        roles=dict(ASSIGN)
        roles[278968]='99'
        self.assertEqual(make(assignments=roles)['status'],'BLOCKED')

    def test_one_teen_cannot_hold_two_special_roles(self):
        roles=dict(ASSIGN)
        roles[278968]=roles[278965]
        self.assertEqual(make(assignments=roles)['status'],'BLOCKED')

    def test_teen_playable_not_also_auto_invited_as_ea_npc(self):
        roles=dict(ASSIGN)
        roles[278968]='1'
        eligibility=dict(ELIG)
        eligibility[278968]=('1',)
        self.assertEqual(make(assignments=roles,
                              ea_eligible_ids_by_job=eligibility)['status'],'BLOCKED')

    def test_missing_or_failed_ea_filter_blocks_all_five_roles(self):
        self.assertEqual(make(ea_eligible_ids_by_job={})['status'],'BLOCKED')
        eligibility=dict(ELIG)
        eligibility[278966]=('200',)
        self.assertEqual(make(ea_eligible_ids_by_job=eligibility)['status'],'BLOCKED')

    def test_wrong_chess_football_filter_specs_block(self):
        from mhs93_verified_jobs import VERIFIED_SPECS
        altered=dict(VERIFIED_SPECS)
        altered[278966],altered[278967]=altered[278967],altered[278966]
        self.assertEqual(make(filter_specs=altered)['status'],'BLOCKED')

    def test_teacher_or_base_student_cannot_be_core_role(self):
        roles=dict(ASSIGN)
        roles[277895]=roles.pop(278965)
        self.assertEqual(make(assignments=roles)['status'],'BLOCKED')
        roles=dict(ASSIGN)
        roles[277894]=roles.pop(278965)
        self.assertEqual(make(assignments=roles)['status'],'BLOCKED')

    def test_class_not_full_denies_early_plan(self):
        self.assertEqual(make(class_ids=(GROUPS[0],GROUPS[1][:-1]))['status'],'BLOCKED')

    def test_live_binding_cannot_fake_early_reservation(self):
        plan=make()
        self.assertFalse(validate_live_binding(plan,ASSIGN))
        self.assertTrue(validate_live_binding(
            plan,ASSIGN,school_verified=True,save_verified=True,day_verified=True))
        wrong=dict(ASSIGN)
        wrong[278965]='99'
        self.assertFalse(validate_live_binding(
            plan,wrong,school_verified=True,save_verified=True,day_verified=True))
        self.assertFalse(plan['role_binding_confirmed'])

    def test_invalid_identifiers_block(self):
        roles=dict(ASSIGN)
        roles[278965]=0
        self.assertEqual(make(assignments=roles)['status'],'BLOCKED')
        roles=dict(ASSIGN)
        roles[278965]='02'
        self.assertEqual(make(assignments=roles)['status'],'BLOCKED')

if __name__=='__main__':
    unittest.main()
