"""Offline M108: never equate create_situation with post-Bouncer EA jobs."""
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'/'m108_native_roster'))

from mhs108_post_bouncer_audit import NativeJobAudit
from tests.test_m108_native_invitation import (
    CLASSES,CORE,prepare_fixed_manifest)

KEY=('11',12,'777','10:00')


class NativeJob(object):
    def __init__(self,guid):
        self.guid64=guid


class NativeSim(object):
    def __init__(self,sid):
        self.id=int(sid)
        self.sim_id=int(sid)


class NativeSituation(object):
    def __init__(self,situation_guid,by_job,extra=()):
        self.guid64=situation_guid
        self.by_job={NativeJob(k):tuple(NativeSim(sid) for sid in values)
                     for k,values in by_job.items()}
        self.extra=tuple(NativeSim(x) for x in extra)

    def all_jobs_gen(self):
        return iter(self.by_job.keys())

    def all_sims_in_job_gen(self,job):
        return iter(self.by_job[job])

    def all_sims_in_situation_gen(self):
        for members in self.by_job.values():
            for sim in members:
                yield sim
        for sim in self.extra:
            yield sim


class NativeManager(object):
    def __init__(self,things=None):
        self.things=things or {}
        self.calls=0

    def get(self,situation_id):
        self.calls+=1
        return self.things.get(situation_id)


def manifest():
    return prepare_fixed_manifest(
        CLASSES,('1','9','16'),CORE,11,12,777)


def audit():
    return NativeJobAudit(manifest())


def barrier(sid=101,**changes):
    data={
        'ea_bouncer_assignment_completed':True,
        'post_bouncer_source_verified':True,
        'phase_key':KEY,'situation_id':sid,
    }
    data.update(changes)
    return data


class EAJobObserverTests(unittest.TestCase):

    def test_create_receipt_is_never_a_job_confirmation(self):
        a=audit()
        self.assertTrue(a.register_created(
            101,304567,{280777:('10','11','12','13','14','15'),
                        277918:('200','201'),278224:('202',)},KEY))
        manager=NativeManager({
            101:NativeSituation(304567,{
                280777:(10,11,12,13,14,15),
                277918:(200,201),278224:(202,)})
        })
        self.assertEqual(a.observe(101,manager,{})['status'],
                         'CREATED_AWAITING_BOUNCER')
        self.assertEqual(manager.calls,0)
        self.assertEqual(a.snapshot()['native_created_awaiting_bouncer'],1)
        result=a.observe(101,manager,barrier())
        self.assertEqual(result['status'],'NATIVE_JOBS_MATCH')
        self.assertTrue(result['native_job_assignment_verified'])
        self.assertFalse(result['seating_verified'])
        self.assertEqual(result['actual_ids_by_job'][280777],
                         ('10','11','12','13','14','15'))

    def test_pre_spawning_or_wrong_day_barrier_must_not_read_jobs(self):
        for changes in (
            {'post_bouncer_source_verified':False},
            {'ea_bouncer_assignment_completed':False},
            {'phase_key':('11',13,'777','10:00')},
            {'situation_id':900},
        ):
            a=audit()
            self.assertTrue(a.register_created(
                101,304565,{277919:('2','3')},KEY))
            manager=NativeManager({
                101:NativeSituation(304565,{277919:(2,3)})
            })
            self.assertEqual(a.observe(101,manager,
                                      barrier(**changes))['status'],
                             'CREATED_AWAITING_BOUNCER')
            self.assertEqual(manager.calls,0)

    def test_correct_student_total_but_wrong_teacher_job_rejected(self):
        a=audit()
        jobs={280777:(10,11,12,13,14,15),
              277918:(200,201),278224:(202,)}
        a.register_created(101,304567,jobs,KEY)
        wrong={280777:(200,11,12,13,14,15),
               277918:(10,201),278224:(202,)}
        manager=NativeManager({101:NativeSituation(304567,wrong)})
        result=a.observe(101,manager,barrier())
        self.assertEqual(result['status'],'WRONG_EA_SIM_OR_JOB')
        self.assertFalse(result['native_job_assignment_verified'])
        self.assertEqual(a.snapshot()['native_jobs_rejected'],1)
        # A false negative cannot be retroactively converted to a PASS.
        manager.things[101]=NativeSituation(304567,jobs)
        self.assertEqual(a.observe(101,manager,barrier())['status'],
                         'WRONG_EA_SIM_OR_JOB')
        self.assertEqual(manager.calls,1)

    def test_extra_unregistered_sim_in_situation_is_detected(self):
        a=audit()
        a.register_created(101,304565,{277919:('2','3')},KEY)
        s=NativeSituation(304565,{277919:(2,3)},extra=(999,))
        r=a.observe(101,NativeManager({101:s}),barrier())
        self.assertEqual(r['status'],'EA_JOB_MEMBERSHIP_INCONSISTENT')

    def test_situation_type_or_job_layout_must_match_original_ea(self):
        for sit in (
            NativeSituation(777,{277919:(2,3)}),
            NativeSituation(304565,{277919:(2,3),277918:()}),
        ):
            a=audit()
            a.register_created(101,304565,{277919:('2','3')},KEY)
            r=a.observe(101,NativeManager({101:sit}),barrier())
            self.assertIn(r['status'],
                          ('WRONG_EA_SITUATION_TYPE','EA_JOB_LAYOUT_MISMATCH'))

    def test_exact_class1_split_two_native_situations_is_not_seating(self):
        a=audit()
        self.assertTrue(a.register_created(
            101,304565,{277919:('2','3')},KEY))
        self.assertTrue(a.register_created(
            102,304703,{277919:('4','5','6','7','8')},KEY))
        mgr=NativeManager({
            101:NativeSituation(304565,{277919:(2,3)}),
            102:NativeSituation(304703,{277919:(4,5,6,7,8)}),
        })
        self.assertEqual(a.observe(101,mgr,barrier())['status'],
                         'NATIVE_JOBS_MATCH')
        self.assertEqual(a.observe(102,mgr,barrier(102))['status'],
                         'NATIVE_JOBS_MATCH')
        self.assertEqual(a.snapshot()['native_jobs_verified'],2)
        self.assertFalse(a.snapshot()['all_registered_16_seated_verified'])
        self.assertFalse(a.snapshot()['full_day_attendance_verified'])

    def test_job_id_alias_is_not_another_class_and_no_duplicate_ids(self):
        a=audit()
        self.assertFalse(a.register_created(
            101,297774,{277919:('10','10')},KEY))
        self.assertFalse(a.register_created(
            101,297774,{277919:(10,),277918:(10,)},KEY))
        self.assertTrue(a.register_created(
            101,297774,{277919:(10,11),277918:(200,)},KEY))
        self.assertFalse(a.register_created(
            101,297774,{277919:(12,)},KEY))
        self.assertEqual(a.snapshot()['native_created_awaiting_bouncer'],1)

    def test_incorrect_native_job_ids_cannot_be_verified(self):
        a=audit()
        a.register_created(101,304565,{277919:('2','3')},KEY)
        s=NativeSituation(304565,{277919:(2,3,999)})
        self.assertEqual(a.observe(101,NativeManager({101:s}),
                                   barrier())['status'],
                         'WRONG_EA_SIM_OR_JOB')
        self.assertFalse(a.snapshot()['all_registered_16_seated_verified'])

    def test_bouncer_not_yet_created_situation_is_failed_not_success(self):
        a=audit()
        a.register_created(101,304565,{277919:('2','3')},KEY)
        self.assertEqual(a.observe(101,NativeManager(),barrier())['status'],
                         'EA_SITUATION_MISSING')

    def test_sim_info_identifiers_disagree_must_fail(self):
        class BadSim(object):
            id=2
            sim_id=3

        class BadSituation(NativeSituation):
            def all_sims_in_job_gen(self,job):
                return iter((BadSim(),))

            def all_sims_in_situation_gen(self):
                return iter((BadSim(),))

        a=audit()
        a.register_created(101,304565,{277919:('2',)},KEY)
        self.assertEqual(a.observe(
            101,NativeManager({101:BadSituation(304565,
                                                {277919:(2,)})}),
            barrier())['status'],'DUPLICATE_OR_UNKNOWN_SIM')

    def test_registration_is_scoped_to_ea_class_and_true_student_job(self):
        for situation, jobs in (
            (123456,{277919:('2','3')}),
            (304565,{280777:('2','3')}),
            (304565,{277919:('10','11')}),
            (304567,{280777:('2','3'),277918:('200',),
                     278224:('202',)}),
            (304567,{280777:('10','11'),277918:('200',),
                     278224:('1',)}),
            (304565,{277919:('2','999')}),
            (304567,{280777:('10','11'),277918:('10',),
                     278224:('202',)}),
        ):
            a=audit()
            self.assertFalse(a.register_created(101,situation,jobs,KEY),
                             msg=str((situation,jobs)))
            self.assertEqual(a.snapshot()['native_created_awaiting_bouncer'],0)

    def test_class_one_both_branches_cannot_invite_same_sim_twice(self):
        a=audit()
        self.assertTrue(a.register_created(
            101,304565,{277919:('2','3')},KEY))
        self.assertFalse(a.register_created(
            102,304703,{277919:('3','4')},KEY))
        self.assertTrue(a.register_created(
            102,304703,{277919:('4','5')},KEY))
        self.assertEqual(a.snapshot()['native_created_awaiting_bouncer'],2)

    def test_original_ea_phase_time_and_save_must_match(self):
        a=audit()
        for phase_key in (
            ('22',12,'777','10:00'),
            ('11',13,'777','10:00'),
            ('11',12,'888','10:00'),
            ('11',12,'777','09:30'),
        ):
            self.assertFalse(a.register_created(
                101,304565,{277919:('2','3')},phase_key))
        self.assertEqual(a.snapshot()['native_created_awaiting_bouncer'],0)

    def test_bouncer_probe_never_mutates_situation(self):
        a=audit()
        a.register_created(101,304565,{277919:('2','3')},KEY)
        sit=NativeSituation(304565,{277919:(2,3)})
        before={k:tuple(v) for k,v in sit.by_job.items()}
        self.assertEqual(a.observe(
            101,NativeManager({101:sit}),barrier())['status'],
            'NATIVE_JOBS_MATCH')
        self.assertEqual(sit.by_job,before)


if __name__=='__main__':
    unittest.main()
