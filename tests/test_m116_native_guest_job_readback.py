"""M116 original EA 8 Base + 1 Core job readback; synthetic games only."""
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'/'m108_native_roster'))
sys.path.insert(0,str(ROOT/'src'/'m116_admission'))

from tests.test_m108_native_invitation import (
    session, EAList, CONTEXT, BASE_SITUATION, CORE_SITUATION,
    BASE_JOB, CORE_JOBS,
)
from mhs116_native_guest_job_readback import (
    inspect_created_native_guest_jobs,
)


class Job(object):
    def __init__(self, guid):
        self.guid64=guid


class Sim(object):
    def __init__(self,sid):
        self.id=int(sid)
        self.sim_id=int(sid)


class Situation(object):
    def __init__(self,guid,jobs):
        self.guid64=guid
        self.jobs=jobs

    def all_jobs_gen(self):
        return tuple(Job(guid) for guid in self.jobs)

    def all_sims_in_job_gen(self,job):
        return tuple(Sim(sid) for sid in self.jobs[job.guid64])

    def all_sims_in_situation_gen(self):
        return tuple(Sim(sid) for group in self.jobs.values()
                     for sid in group)


class Manager(object):
    def __init__(self,situations,complete=True):
        self._sim_assignment_complete=complete
        self.situations=situations
        self.calls=0

    def get(self,situation_id):
        self.calls+=1
        return self.situations.get(situation_id)


def assembled():
    guest=session()
    situations={}
    for index,sid in enumerate(guest.manifest['base_ids']):
        ticket,cloned=guest.preview(BASE_SITUATION,EAList(),CONTEXT)
        assert ticket=='base:'+sid
        situation_id=index+201
        assert guest.acknowledge_created(ticket,situation_id)
        situations[situation_id]=Situation(BASE_SITUATION,
                                           {BASE_JOB:(int(sid),)})
    ticket,clone=guest.preview(CORE_SITUATION,EAList(),CONTEXT)
    assert ticket=='core'
    assert guest.acknowledge_created(ticket,300)
    core={job:(int(sid),) for job,sid in
          guest.manifest['core_assignments']}
    # Original EA Core can include staff, whom we must not erase.
    core[277895]=(999,)
    situations[300]=Situation(CORE_SITUATION,core)
    return guest,Manager(situations)


class OriginalJobReadbackTests(unittest.TestCase):
    def test_exact_nine_original_created_receipts_remain_stable(self):
        guest,manager=assembled()
        receipts=dict(guest.native_created_receipts())
        self.assertEqual(len(receipts),9)
        self.assertEqual(receipts['core'],300)
        self.assertEqual(receipts['base:5'],201)
        self.assertEqual(guest.snapshot()['native_creation_receipts_count'],9)
        self.assertFalse(guest.snapshot()['ea_job_assignment_verified'])

    def test_all_thirteen_exact_native_NPC_roles_observed_not_seating(self):
        guest,manager=assembled()
        r=inspect_created_native_guest_jobs(guest,manager)
        self.assertEqual(r['status'],'NATIVE_GUEST_JOBS_MATCH_OBSERVED')
        self.assertEqual(r['enrolled_npc_job_ids_observed'],13)
        self.assertEqual(r['number_original_native_situations_found'],9)
        self.assertTrue(r['native_guest_jobs_13_verified_in_snapshot'])
        self.assertEqual(manager.calls,9)
        self.assertFalse(r['post_bouncer_callback_provenance_verified'])
        self.assertFalse(r['all_3_playables_on_lot_verified'])
        self.assertFalse(r['all_16_students_attending_verified'])
        self.assertFalse(r['classroom_seating_verified'])

    def test_NPC_wrongly_substituted_detected_with_source_ticket(self):
        guest,manager=assembled()
        manager.situations[201].jobs[BASE_JOB]=(9999,)
        r=inspect_created_native_guest_jobs(guest,manager)
        self.assertEqual(r['status'],'NATIVE_GUEST_JOBS_DIFFER')
        self.assertIn(('base:5','BASE_NPC_JOB_MISMATCH'),
                      r['discrepancies'])
        self.assertIn('9999',r['extra_native_student_ids'])
        self.assertFalse(r['native_guest_jobs_13_verified_in_snapshot'])

    def test_wrong_special_role_holder_fails(self):
        guest,manager=assembled()
        job=CORE_JOBS[0]
        manager.situations[300].jobs[job]=(3,)
        r=inspect_created_native_guest_jobs(guest,manager)
        self.assertEqual(r['status'],'NATIVE_GUEST_JOBS_DIFFER')
        self.assertIn(('core','CORE_NPC_JOB_MISMATCH'),
                      r['discrepancies'])

    def test_wrong_staff_job_for_registered_student_fails(self):
        guest,manager=assembled()
        manager.situations[300].jobs[277895]=(5,)
        r=inspect_created_native_guest_jobs(guest,manager)
        self.assertEqual(r['status'],'NATIVE_GUEST_JOBS_DIFFER')
        self.assertIn(('core','ValueError'),r['discrepancies'])

    def test_incomplete_session_does_not_fake_nine_receipts(self):
        guest=session()
        r=inspect_created_native_guest_jobs(guest,Manager({}))
        self.assertEqual(r['status'],
                         'NATIVE_EA_NINE_CREATE_RECEIPTS_NOT_READY')
        self.assertEqual(r['receipts_present'],0)

    def test_native_EA_spinup_assignment_flag_must_be_observed(self):
        guest,manager=assembled()
        manager._sim_assignment_complete=False
        r=inspect_created_native_guest_jobs(guest,manager)
        self.assertEqual(r['status'],
                         'EA_SPINUP_ASSIGNMENT_FLAG_NOT_OBSERVED')
        self.assertFalse(r['post_bouncer_callback_provenance_verified'])

    def test_original_missing_situation_does_not_become_success(self):
        guest,manager=assembled()
        del manager.situations[203]
        r=inspect_created_native_guest_jobs(guest,manager)
        self.assertEqual(r['status'],'NATIVE_GUEST_JOBS_DIFFER')
        self.assertIn(('base:7','EA_SITUATION_ID_MISSING'),
                      r['discrepancies'])
        self.assertFalse(r['native_guest_jobs_13_verified_in_snapshot'])

    def test_duplicated_job_sim_membership_is_not_accepted(self):
        guest,manager=assembled()
        manager.situations[300].jobs[277895]=(2,)
        r=inspect_created_native_guest_jobs(guest,manager)
        self.assertEqual(r['status'],'NATIVE_GUEST_JOBS_DIFFER')
        self.assertIn(('core','ValueError'),r['discrepancies'])

    def test_original_EA_unsupported_job_blocks(self):
        guest,manager=assembled()
        manager.situations[201].jobs[123456]=(7777,)
        r=inspect_created_native_guest_jobs(guest,manager)
        self.assertEqual(r['status'],'NATIVE_GUEST_JOBS_DIFFER')
        self.assertIn(('base:5','ValueError'),r['discrepancies'])


if __name__=='__main__':
    unittest.main()
