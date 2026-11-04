"""M117 original EA post-spinup callback binding: synthetic unit tests."""
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
for name in ('m108_native_roster','m116_admission','m117_spinup'):
    sys.path.insert(0,str(ROOT/'src'/name))

from mhs117_post_spinup_admission import (
    M117PostSpinupAdmission, PROOF_KEYS,
)
from tests.test_m116_native_guest_job_readback import assembled


def evidence():
    return {key:True for key in PROOF_KEYS}


def callback_owner():
    class SituationManager(object):
        def __init__(self, actual):
            self._sim_assignment_complete=False
            self.situations=actual.situations
            self.calls=0
            self.lookups=0
        def on_all_sims_spawned_during_zone_spin_up(self, tag='x'):
            self.calls+=1
            self._sim_assignment_complete=True
            return 'EA_ORIGINAL_'+tag
        def get(self, situation_id):
            self.lookups+=1
            return self.situations.get(situation_id)
    SituationManager.__module__='situations.situation_manager'
    return SituationManager


def setting(changes=None):
    guest,native=assembled()
    manager=callback_owner()
    context={
        'source':'EA_RUNTIME_OBSERVATION', # TEST FIXTURE, NOT LIVE PROOF
        'original_ea_school_spinup_callback':True,
        'active_school_lot_verified':True,
        'save_slot':'11','sim_day':12,
        'zone_id':'777','schedule_guid':277657,
    }
    if changes:
        context.update(changes)
    reads=[0]
    def provider(instance):
        reads[0]+=1
        return dict(context,manager_identity=instance)
    observer=M117PostSpinupAdmission(guest,provider)
    return guest,manager,native,observer,reads


class M117RealEAChainTests(unittest.TestCase):
    def test_original_callback_first_then_thirteen_jobs_appear(self):
        guest,manager,native,observer,reads=setting()
        original=manager.__dict__[
            'on_all_sims_spawned_during_zone_spin_up']
        self.assertTrue(observer.install(manager,evidence()))
        self.assertEqual(observer.state,'OBSERVING')
        simmanager=manager(native)
        self.assertEqual(simmanager.calls,0)
        self.assertEqual(simmanager.on_all_sims_spawned_during_zone_spin_up(
            'school'),'EA_ORIGINAL_school')
        self.assertEqual(simmanager.calls,1)
        self.assertEqual(simmanager.lookups,9)
        self.assertEqual(reads[0],1)
        self.assertEqual(len(observer.observations),1)
        report=observer.observations[0]
        self.assertEqual(report['status'],'NATIVE_GUEST_JOBS_MATCH_OBSERVED')
        self.assertTrue(report['native_guest_jobs_13_verified_in_snapshot'])
        self.assertTrue(report['post_bouncer_callback_provenance_verified'])
        self.assertEqual(report['post_bouncer_provenance_scope'],
                         'ORIGINAL_EA_ZONE_SPINUP_ONLY')
        self.assertFalse(report['all_16_students_attending_verified'])
        self.assertFalse(report['classroom_seating_verified'])
        self.assertTrue(observer.restore())
        self.assertIs(manager.__dict__[
            'on_all_sims_spawned_during_zone_spin_up'],original)

    def test_duplicate_callback_does_not_repeat_job_readback(self):
        guest,manager,native,observer,reads=setting()
        self.assertTrue(observer.install(manager,evidence()))
        try:
            simmanager=manager(native)
            simmanager.on_all_sims_spawned_during_zone_spin_up()
            simmanager.on_all_sims_spawned_during_zone_spin_up()
            self.assertEqual(simmanager.calls,2)
            self.assertEqual(simmanager.lookups,9)
            self.assertEqual(len(observer.observations),1)
        finally:
            self.assertTrue(observer.restore())

    def test_wrong_save_day_zone_school_does_not_access_EA_jobs(self):
        for bad in (
            {'save_slot':'12'},{'sim_day':13},{'zone_id':'999'},
            {'schedule_guid':1},{'active_school_lot_verified':False},
            {'original_ea_school_spinup_callback':False},
            {'source':'CLAIMED_NOT_FROM_ENGINE'}):
            guest,manager,native,observer,reads=setting(bad)
            self.assertTrue(observer.install(manager,evidence()))
            try:
                obj=manager(native)
                self.assertEqual(
                    obj.on_all_sims_spawned_during_zone_spin_up(),
                    'EA_ORIGINAL_x')
                self.assertEqual(obj.calls,1)
                self.assertEqual(obj.lookups,0)
                self.assertEqual(observer.observations,[])
            finally:
                self.assertTrue(observer.restore())

    def test_missing_original_flag_blocks_without_reading_situations(self):
        guest,manager,native,observer,reads=setting()
        def original_without_assignment(self):
            self.calls+=1
            return 'EA_NO_FLAG'
        manager.on_all_sims_spawned_during_zone_spin_up=(
            original_without_assignment)
        self.assertTrue(observer.install(manager,evidence()))
        try:
            obj=manager(native)
            self.assertEqual(obj.on_all_sims_spawned_during_zone_spin_up(),
                             'EA_NO_FLAG')
            self.assertEqual(obj.lookups,0)
            self.assertEqual(observer.observations[0]['status'],
                             'ORIGINAL_EA_SPINUP_FLAG_NOT_SET')
            self.assertFalse(observer.observations[0][
                'post_bouncer_callback_provenance_verified'])
        finally:
            self.assertTrue(observer.restore())

    def test_changed_native_job_is_detected_only_after_callback(self):
        guest,manager,native,observer,reads=setting()
        native.situations[201].jobs[277894]=(987,)
        self.assertTrue(observer.install(manager,evidence()))
        try:
            obj=manager(native)
            obj.on_all_sims_spawned_during_zone_spin_up()
            report=observer.observations[0]
            self.assertEqual(report['status'],'NATIVE_GUEST_JOBS_DIFFER')
            self.assertIn(('base:5','BASE_NPC_JOB_MISMATCH'),
                          report['discrepancies'])
            self.assertFalse(report['native_guest_jobs_13_verified_in_snapshot'])
            self.assertTrue(report['post_bouncer_callback_provenance_verified'])
        finally:
            self.assertTrue(observer.restore())

    def test_callback_exception_propagates_without_audit_or_double_call(self):
        guest,manager,native,observer,reads=setting()
        def original_raises(self):
            self.calls+=1
            raise RuntimeError('EA died')
        manager.on_all_sims_spawned_during_zone_spin_up=original_raises
        self.assertTrue(observer.install(manager,evidence()))
        try:
            obj=manager(native)
            with self.assertRaises(RuntimeError):
                obj.on_all_sims_spawned_during_zone_spin_up()
            self.assertEqual(obj.calls,1)
            self.assertEqual(obj.lookups,0)
            self.assertEqual(observer.observations,[])
        finally:
            self.assertTrue(observer.restore())

    def test_bad_gate_or_non_native_owner_does_not_patch(self):
        for key in PROOF_KEYS:
            guest,manager,native,observer,reads=setting()
            proof=evidence()
            proof[key]=False
            original=manager.__dict__[
                'on_all_sims_spawned_during_zone_spin_up']
            self.assertFalse(observer.install(manager,proof))
            self.assertIs(manager.__dict__[
                'on_all_sims_spawned_during_zone_spin_up'],original)
        guest,manager,native,observer,reads=setting()
        manager.__module__='external_mod'
        self.assertFalse(observer.install(manager,evidence()))

    def test_no_stacking_and_refuse_to_clobber_other_hook_on_restore(self):
        guest,manager,native,observer,reads=setting()
        self.assertTrue(observer.install(manager,evidence()))
        self.assertFalse(observer.install(manager,evidence()))
        original=manager.__dict__[
            'on_all_sims_spawned_during_zone_spin_up']
        def other(self):
            return 'thirdparty'
        manager.on_all_sims_spawned_during_zone_spin_up=other
        self.assertFalse(observer.restore())
        self.assertEqual(observer.state,'RESTORE_CONFLICT')
        self.assertIs(manager.__dict__[
            'on_all_sims_spawned_during_zone_spin_up'],other)
        # Restore fixture manually, not by the implementation.
        manager.on_all_sims_spawned_during_zone_spin_up=original

    def test_stage_rejects_wrong_manifest_and_never_fabricates_success(self):
        guest,manager,native,observer,reads=setting()
        stage=observer.stage(manager,evidence())
        self.assertFalse(stage['install']({},{}))
        self.assertEqual(observer.state,'NOT_INSTALLED')
        self.assertTrue(stage['restore']())
        self.assertTrue(stage['install'](guest.manifest,{}))
        self.assertEqual(observer.state,'OBSERVING')
        self.assertTrue(stage['restore']())
        self.assertEqual(observer.snapshot()['reports'],0)
        self.assertFalse(observer.snapshot()['late_lessons_verified'])

    def test_wrapped_source_marker_matches_M109_descriptor_rollback(self):
        guest,manager,native,observer,reads=setting()
        self.assertTrue(observer.install(manager,evidence()))
        self.assertTrue(getattr(
            manager.__dict__['on_all_sims_spawned_during_zone_spin_up'],
            '_mhs108_post_bouncer',False))
        self.assertTrue(observer.restore())


if __name__=='__main__':
    unittest.main()
