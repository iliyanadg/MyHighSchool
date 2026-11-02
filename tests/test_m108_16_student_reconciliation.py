"""M108: exact 16 and no extras across native Class1 + Class2 jobs."""
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'/'m108_native_roster'))

from mhs108_16_student_reconciliation import reconcile_16_school_members
from tests.test_m108_post_bouncer_audit import (
    audit,NativeManager,NativeSituation,barrier,KEY)

ON_LOT=tuple(str(n) for n in range(1,17))
PLAYABLE=('1','9','16')


def make_audit():
    obj=audit()
    cases={
        101:(304565,{277919:(2,3)}),
        102:(304703,{277919:(4,5,6,7,8)}),
        103:(304567,{280777:(10,11,12,13,14,15),
                     277918:(200,201),278224:(202,)}),
    }
    for sid,(type_,members) in cases.items():
        assert obj.register_created(sid,type_,members,KEY)
    manager=NativeManager({
        sid:NativeSituation(type_,members)
        for sid,(type_,members) in cases.items()})
    return obj,manager


def ctx(**changes):
    result={
        'observed_player_ea_job_verified':True,
        'observed_zone_teens_verified':True,
        'post_bouncer_phase_verified':True,
        'ea_all_classroom_phase_situations_verified':True,
        'strict_enrolled_teens_only_verified':True,
        'observed_ea_classroom_phase_situation_ids':(101,102,103),
        'zone_id':'777',
        'time_window':'10:00',
    }
    result.update(changes)
    return result


def reconcile(audit_,zone=ON_LOT,player=PLAYABLE,context=None):
    return reconcile_16_school_members(
        audit_.manifest,audit_,KEY,zone,player,
        ctx() if context is None else context)


class ExactSixteenAfterEAJobTests(unittest.TestCase):
    def test_invited_sim_ids_do_not_count_as_native_jobs(self):
        observer,manager=make_audit()
        result=reconcile(observer)
        self.assertEqual(result['status'],
                         'NATIVE_EA_JOBS_PENDING_OR_REJECTED')
        self.assertFalse(result['native_ea_16_student_membership_verified'])

    def test_all_13_npc_jobs_and_3_real_ea_players_match_but_not_seated(self):
        observer,manager=make_audit()
        for sid in (101,102,103):
            self.assertEqual(observer.observe(
                sid,manager,barrier(sid))['status'],'NATIVE_JOBS_MATCH')
        result=reconcile(observer)
        self.assertEqual(result['status'],
                         'EXACT_NATIVE_16_STUDENTS_ASSIGNED_NOT_SEATED')
        self.assertEqual(result['actual_students'],16)
        self.assertEqual(result['class1_registered'],8)
        self.assertEqual(result['class2_registered'],8)
        self.assertEqual(result['class1_native_npc_members'],7)
        self.assertEqual(result['class2_native_npc_members'],6)
        self.assertTrue(result['native_ea_16_student_membership_verified'])
        self.assertFalse(result['class_8_plus_8_seating_verified'])
        self.assertFalse(result['full_school_day_verified'])
        self.assertFalse(result['game_modified'])

    def test_one_playable_missing_from_ea_player_jobs_fails(self):
        observer,manager=make_audit()
        for sid in (101,102,103):
            observer.observe(sid,manager,barrier(sid))
        result=reconcile(observer,player=('1','9'))
        self.assertEqual(result['status'],'PLAYABLE_SCHOOL_JOB_MISMATCH')
        self.assertEqual(result['missing_playables'],('16',))

    def test_missing_playable_on_school_lot_fails(self):
        observer,manager=make_audit()
        for sid in (101,102,103):
            observer.observe(sid,manager,barrier(sid))
        result=reconcile(observer,zone=ON_LOT[:-1])
        self.assertEqual(result['status'],'REGISTERED_STUDENT_NOT_ON_LOT')
        self.assertEqual(result['missing_students'],('16',))

    def test_unregistered_teen_on_school_lot_is_not_silently_allowed(self):
        observer,manager=make_audit()
        for sid in (101,102,103):
            observer.observe(sid,manager,barrier(sid))
        result=reconcile(observer,zone=ON_LOT+('999',))
        self.assertEqual(result['status'],'EXTRANEOUS_TEEN_ON_SCHOOL_LOT')
        self.assertEqual(result['extraneous_teen_ids'],('999',))

    def test_untracked_fourth_ea_classroom_situation_fails(self):
        observer,manager=make_audit()
        for sid in (101,102,103):
            observer.observe(sid,manager,barrier(sid))
        result=reconcile(observer,context=ctx(
            observed_ea_classroom_phase_situation_ids=(101,102,103,104)))
        self.assertEqual(result['status'],
                         'UNTRACKED_NATIVE_CLASSROOM_SITUATIONS')
        self.assertEqual(result['untracked_situation_ids'],('104',))

    def test_role_swap_in_native_job_cannot_pass_sixteen_even_with_right_counts(self):
        observer,manager=make_audit()
        manager.things[103]=NativeSituation(
            304567,{280777:(200,11,12,13,14,15),
                    277918:(10,201),278224:(202,)})
        for sid in (101,102,103):
            observer.observe(sid,manager,barrier(sid))
        self.assertEqual(reconcile(observer)['status'],
                         'NATIVE_EA_JOBS_PENDING_OR_REJECTED')

    def test_incomplete_observation_context_does_not_claim_16(self):
        observer,manager=make_audit()
        for sid in (101,102,103):
            observer.observe(sid,manager,barrier(sid))
        for bad in (
            {'observed_player_ea_job_verified':False},
            {'observed_zone_teens_verified':False},
            {'post_bouncer_phase_verified':False},
            {'ea_all_classroom_phase_situations_verified':False},
            {'strict_enrolled_teens_only_verified':False},
            {'zone_id':'999'},
            {'time_window':'14:00'},
        ):
            result=reconcile(observer,context=ctx(**bad))
            self.assertEqual(result['status'],
                             'UNVERIFIED_LIVE_OBSERVATIONS',
                             msg=str(bad))


if __name__=='__main__':
    unittest.main()
