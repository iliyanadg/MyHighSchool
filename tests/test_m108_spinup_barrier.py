"""M108 observer of actual EA SituationManager post-Bouncer spin-up."""
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'/'m108_native_roster'))

from mhs108_spinup_barrier import (
    install_offline_only,REQUIRED_LIVE_GATES)
from tests.test_m108_post_bouncer_audit import (
    audit,NativeSituation,KEY)

def proofs():
    return {name:True for name in REQUIRED_LIVE_GATES}

def context(**kw):
    d={
        'mhs_school_session_active':True,
        'verified_ea_school_origin':True,
        'post_bouncer_source_verified':True,
        'save_slot':'11',
        'sim_day':12,
        'zone_id':'777',
    }
    d.update(kw)
    return d

def make():
    class SituationManager(object):
        def __init__(self):
            self.natives={}
            self.calls=0
            self._sim_assignment_complete=False

        def on_all_sims_spawned_during_zone_spin_up(self,tag=None):
            self.calls+=1
            self._sim_assignment_complete=True
            return 'EA_FINISHED_'+str(tag)

        def get(self,situation_id):
            return self.natives.get(situation_id)
    return SituationManager

def prepared():
    a=audit()
    assert a.register_created(101,304565,{277919:('2','3')},KEY)
    return a

class SpinupBouncerBarrierTests(unittest.TestCase):
    def test_unsafe_proof_refuses_patch(self):
        for key in REQUIRED_LIVE_GATES:
            Manager=make()
            flags=proofs()
            flags[key]=False
            self.assertIsNone(install_offline_only(
                Manager,prepared(),lambda m:context(),flags))
            self.assertEqual(Manager().on_all_sims_spawned_during_zone_spin_up(),
                             'EA_FINISHED_None')

    def test_original_ea_callback_runs_once_then_real_job_members_checked(self):
        Manager=make()
        a=prepared()
        undo=install_offline_only(Manager,a,lambda m:context(),proofs())
        self.assertTrue(callable(undo))
        m=Manager()
        m.natives[101]=NativeSituation(304565,{277919:(2,3)})
        result=m.on_all_sims_spawned_during_zone_spin_up('test')
        self.assertEqual(result,'EA_FINISHED_test')
        self.assertEqual(m.calls,1)
        self.assertEqual(undo.observations,[(101,'NATIVE_JOBS_MATCH')])
        self.assertEqual(a.snapshot()['native_jobs_verified'],1)
        self.assertFalse(a.snapshot()['full_day_attendance_verified'])
        self.assertTrue(undo())
        self.assertFalse(undo())

    def test_wrong_ea_members_are_rejected_after_original_native_assignment(self):
        Manager=make()
        a=prepared()
        undo=install_offline_only(Manager,a,lambda m:context(),proofs())
        m=Manager()
        m.natives[101]=NativeSituation(304565,{277919:(2,999)})
        self.assertEqual(m.on_all_sims_spawned_during_zone_spin_up(),
                         'EA_FINISHED_None')
        self.assertEqual(a.snapshot()['native_jobs_rejected'],1)
        self.assertEqual(undo.observations,[(101,'WRONG_EA_SIM_OR_JOB')])
        self.assertTrue(undo())

    def test_unverified_world_zone_or_day_does_not_interfere_with_ea(self):
        for delta in (
            {'mhs_school_session_active':False},
            {'verified_ea_school_origin':False},
            {'post_bouncer_source_verified':False},
            {'sim_day':13},
            {'save_slot':'12'},
            {'zone_id':'200'},
        ):
            Manager=make()
            a=prepared()
            undo=install_offline_only(
                Manager,a,lambda m:context(**delta),proofs())
            m=Manager()
            m.natives[101]=NativeSituation(304565,{277919:(2,3)})
            m.on_all_sims_spawned_during_zone_spin_up()
            self.assertEqual(m.calls,1)
            self.assertEqual(undo.observations,[])
            self.assertEqual(a.snapshot()['native_created_awaiting_bouncer'],1)
            self.assertTrue(undo())

    def test_original_exception_is_propagated_without_retry(self):
        class Manager(object):
            called=0
            def on_all_sims_spawned_during_zone_spin_up(self):
                self.called+=1
                raise RuntimeError('EA error')
        undo=install_offline_only(Manager,prepared(),
                                 lambda m:context(),proofs())
        obj=Manager()
        with self.assertRaises(RuntimeError):
            obj.on_all_sims_spawned_during_zone_spin_up()
        self.assertEqual(obj.called,1)
        self.assertTrue(undo())

    def test_unknown_or_not_yet_registered_school_situations_remain_pending(self):
        Manager=make()
        a=audit()
        undo=install_offline_only(Manager,a,lambda m:context(),proofs())
        m=Manager()
        m.natives[101]=NativeSituation(304565,{277919:(2,3)})
        m.on_all_sims_spawned_during_zone_spin_up()
        self.assertEqual(a.snapshot()['native_jobs_verified'],0)
        self.assertTrue(undo())

    def test_no_stacked_observer_and_no_second_audit(self):
        Manager=make()
        a=prepared()
        undo=install_offline_only(Manager,a,lambda m:context(),proofs())
        self.assertIsNone(install_offline_only(
            Manager,prepared(),lambda m:context(),proofs()))
        m=Manager()
        m.natives[101]=NativeSituation(304565,{277919:(2,3)})
        m.on_all_sims_spawned_during_zone_spin_up()
        m.on_all_sims_spawned_during_zone_spin_up()
        self.assertEqual(m.calls,2)
        self.assertEqual(len(undo.observations),1)
        self.assertTrue(undo())


if __name__=='__main__':
    unittest.main()
