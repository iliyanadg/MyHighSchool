"""M113 EA SituationJob and invitation object resolver tests, offline only."""
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'/'m108_native_roster'))
sys.path.insert(0,str(ROOT/'src'/'m113_controller'))

from mhs113_native_guest_factory import (
    make_native_guest_session, native_guest_session_factory, EXPECTED_JOBS
)
from tests.test_m108_native_invitation import (
    session, EAInfo, Job, EARLY_CONTEXT, CONTEXT, EAList,
    BASE_SITUATION,
)


def fake_native_jobs(missing=None,bad_guid=None,no_ctor=False):
    services=types.ModuleType('services')
    class Manager(object):
        def get(self, guid):
            if guid==missing:
                return None
            if guid==bad_guid:
                return Job(12345)
            return Job(guid)
    services.get_instance_manager=lambda typ:Manager()
    sims4=types.ModuleType('sims4')
    sims4.__path__=[]
    resources=types.ModuleType('sims4.resources')
    resources.Types=type('Types',(),{'SITUATION_JOB':'JOBS'})
    sims4.resources=resources
    situations=types.ModuleType('situations')
    situations.__path__=[]
    guests=types.ModuleType('situations.situation_guest_list')
    guestcls=(type('BadGuest',(),{}) if no_ctor else EAInfo)
    guests.SituationGuestInfo=guestcls
    guests.SituationInvitationPurpose=type('Purpose',(),{'INVITED':'INVITED'})
    situations.situation_guest_list=guests
    return {'services':services,'sims4':sims4,
            'sims4.resources':resources,
            'situations':situations,
            'situations.situation_guest_list':guests}


class NativeOriginalEAObjectTests(unittest.TestCase):
    def test_all_six_native_EA_jobs_and_guest_constructor_loaded(self):
        manifest=session().manifest
        with patch.dict(sys.modules,fake_native_jobs()):
            instance,reason=make_native_guest_session(manifest)
        self.assertEqual(reason,'EA_JOB_OBJECTS_RESOLVED_NOT_BOUNCER_VERIFIED')
        self.assertIsNotNone(instance)
        self.assertEqual(set(instance.job_by_id),set(EXPECTED_JOBS))
        self.assertTrue(instance.reserve_core_before_schedule(EARLY_CONTEXT))
        ticket,guests=instance.preview(BASE_SITUATION,EAList(),CONTEXT)
        self.assertEqual(ticket,'base:5')
        self.assertEqual([g.sim_id for g in guests.guest_info_gen()],[5])
        self.assertFalse(instance.snapshot()['attendance_verified'])
        self.assertFalse(instance.snapshot()['ea_job_assignment_verified'])

    def test_missing_or_wrong_EA_tuning_blocks_before_any_guest_preview(self):
        manifest=session().manifest
        for bad in (EXPECTED_JOBS[0],EXPECTED_JOBS[-1]):
            for settings in ({'missing':bad},{'bad_guid':bad}):
                with patch.dict(sys.modules,fake_native_jobs(**settings)):
                    value,reason=make_native_guest_session(manifest)
                self.assertIsNone(value)
                self.assertIn('EA_ORIGINAL_STUDENT_JOB_MISSING_',reason)

    def test_missing_constructor_or_manifest_is_not_assumed(self):
        manifest=session().manifest
        with patch.dict(sys.modules,fake_native_jobs(no_ctor=True)):
            value,reason=make_native_guest_session(manifest)
        self.assertIsNone(value)
        self.assertEqual(reason,'EA_INVITATION_CONSTRUCTOR_MISSING')
        with patch.dict(sys.modules,fake_native_jobs()):
            value,reason=make_native_guest_session({'status':'MANUAL'})
        self.assertIsNone(value)
        self.assertEqual(reason,'UNVERIFIED_M108_MANIFEST')

    def test_callback_shape_returns_native_session_or_none(self):
        manifest=session().manifest
        with patch.dict(sys.modules,fake_native_jobs()):
            self.assertIsNotNone(native_guest_session_factory(manifest))
        with patch.dict(sys.modules,fake_native_jobs(missing=277894)):
            self.assertIsNone(native_guest_session_factory(manifest))


if __name__=='__main__':
    unittest.main()
