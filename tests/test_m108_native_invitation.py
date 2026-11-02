"""M108: original EA SituationManager guest-list contract, strictly offline."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src' / 'm108_native_roster'))
from mhs108_native_invitation import (
    BASE_JOB, BASE_SITUATION, CORE_JOBS, CORE_SITUATION,
    SchoolNativeGuestSession, InvitationPlanError, prepare_fixed_manifest)


class Job(object):
    def __init__(self, guid):
        self.guid64 = guid


class Guest(object):
    def __init__(self, sim_id, job_type, accept_alternate_sim=False):
        self.sim_id = sim_id
        self.job_type = job_type
        self.accept_alternate_sim = accept_alternate_sim

    def clone_for_guest_list(self):
        return Guest(self.sim_id, self.job_type, self.accept_alternate_sim)


class EAInfo(Guest):
    @classmethod
    def construct_from_purpose(cls, sim_id, job_type, purpose):
        if purpose != 'INVITED':
            raise ValueError('wrong EA invitation purpose')
        return cls(sim_id, job_type, False)


class EAList(object):
    def __init__(self, invite_only=False, host_sim_id=0,
                 filter_requesting_sim_id=0):
        self.invite_only = invite_only
        self.host_sim_id = host_sim_id
        self.filter_requesting_sim_id = filter_requesting_sim_id
        self._guests = []

    def guest_info_gen(self):
        return iter(self._guests)

    def add_guest_info(self, info):
        self._guests.append(info)


CLASSES = (tuple(str(n) for n in range(1, 9)),
           tuple(str(n) for n in range(9, 17)))
PLAYABLE = ('1', '9', '16')
CORE = dict(zip(CORE_JOBS, ('2', '3', '4', '10', '11')))
JOBS = {job: Job(job) for job in (BASE_JOB,) + CORE_JOBS}
CONTEXT = {
    'native_origin_verified': True,
    'school_verified': True,
    'schedule_guid': 277657,
    'save_slot': '11',
    'sim_day': 12,
    'zone_id': '777',
}


def session():
    manifest = prepare_fixed_manifest(
        CLASSES, PLAYABLE, CORE, 11, 12, 777)
    return SchoolNativeGuestSession(manifest, EAInfo, 'INVITED', JOBS)


class NativeInvitationTests(unittest.TestCase):

    def test_manifest_has_16_fixed_students_3_playable_5_core_8_base(self):
        m = session().manifest
        self.assertEqual(m['all_16'], CLASSES[0] + CLASSES[1])
        self.assertEqual(m['playable'], PLAYABLE)
        self.assertEqual(dict(m['core_assignments']), CORE)
        self.assertEqual(m['base_ids'], ('5', '6', '7', '8',
                                         '12', '13', '14', '15'))
        self.assertEqual(len(set(m['playable']) |
                             {sid for _, sid in m['core_assignments']} |
                             set(m['base_ids'])), 16)
        self.assertEqual(m['native_schedule_order'], 'BASE_BEFORE_CORE')
        self.assertFalse(m['core_reservations_before_ea_verified'])
        self.assertFalse(m['native_filter_bypass_verified'])
        self.assertFalse(m['class_8_plus_8_verified'])
        self.assertFalse(m['attendance_verified'])

    def test_duplicate_or_changed_roster_and_roles_refused(self):
        bad = [list(CLASSES[0]), list(CLASSES[1])]
        bad[1][1] = bad[0][0]
        for classes, playable, core in (
            (bad, PLAYABLE, CORE),
            (CLASSES, ('1', '9', '30'), CORE),
            (CLASSES, PLAYABLE,
             {k: v for k, v in CORE.items() if k != 303765}),
            (CLASSES, PLAYABLE, dict(zip(CORE_JOBS, ['2'] * 5)))):
            with self.assertRaises(InvitationPlanError):
                prepare_fixed_manifest(classes, playable, core, 11, 12, 777)
        with self.assertRaises(InvitationPlanError):
            prepare_fixed_manifest(CLASSES, PLAYABLE, CORE, 11, -1, 777)
        with self.assertRaises(InvitationPlanError):
            prepare_fixed_manifest(CLASSES, PLAYABLE, CORE, True, 12, 777)

    def test_manifest_is_revalidated_then_frozen_before_any_invites(self):
        original = prepare_fixed_manifest(CLASSES, PLAYABLE, CORE, 11, 12, 777)
        corrupted = dict(original)
        corrupted['base_ids'] = ('999',) * 8
        with self.assertRaises(InvitationPlanError):
            SchoolNativeGuestSession(corrupted, EAInfo, 'INVITED', JOBS)
        s = SchoolNativeGuestSession(original, EAInfo, 'INVITED', JOBS)
        original['base_ids'] = ('999',) * 8
        self.assertEqual(s.manifest['base_ids'],
                         ('5', '6', '7', '8', '12', '13', '14', '15'))

    def test_unverified_context_never_prepares_mutation(self):
        s = session()
        for change in (
            {'native_origin_verified': False},
            {'school_verified': False},
            {'save_slot': '99'},
            {'sim_day': 13},
            {'zone_id': 778},
            {'schedule_guid': 9999}):
            context = dict(CONTEXT, **change)
            self.assertEqual(s.preview(CORE_SITUATION, EAList(), context),
                             (None, None))
        self.assertEqual(s.snapshot()['base_situations_created'], 0)

    def test_core_exact_five_guests_preserves_original_teacher(self):
        s = session()
        original = EAList(host_sim_id=16, filter_requesting_sim_id=1)
        teacher = Guest(222, Job(277895))
        original.add_guest_info(teacher)
        ticket, clone = s.preview(CORE_SITUATION, original, CONTEXT)
        self.assertEqual(ticket, 'core')
        self.assertIsNot(clone, original)
        self.assertTrue(clone.invite_only)
        self.assertEqual(clone.host_sim_id, 16)
        self.assertEqual(clone.filter_requesting_sim_id, 1)
        self.assertEqual(len(list(original.guest_info_gen())), 1)
        self.assertEqual([g.sim_id for g in clone.guest_info_gen()],
                         [222, 2, 3, 4, 10, 11])
        self.assertEqual([g.job_type.guid64 for g in
                          list(clone.guest_info_gen())[1:]], list(CORE_JOBS))
        self.assertTrue(all(g.accept_alternate_sim is False for g in
                            list(clone.guest_info_gen())[1:]))

    def test_core_original_unknown_student_cannot_be_erased(self):
        s = session()
        original = EAList()
        original.add_guest_info(Guest(999, Job(CORE_JOBS[0])))
        self.assertEqual(s.preview(CORE_SITUATION, original, CONTEXT),
                         (None, None))
        self.assertEqual(len(list(original.guest_info_gen())), 1)

    def test_core_receipt_is_not_evidence_of_any_sim_arriving(self):
        s = session()
        ticket, _ = s.preview(CORE_SITUATION, EAList(), CONTEXT)
        self.assertEqual(ticket, 'core')
        self.assertFalse(s.acknowledge_created('core', None))
        self.assertEqual(s.preview(CORE_SITUATION, EAList(), CONTEXT),
                         (None, None))
        self.assertTrue(s.cancel('core'))
        ticket, _ = s.preview(CORE_SITUATION, EAList(), CONTEXT)
        self.assertTrue(s.acknowledge_created(ticket, 100))
        self.assertFalse(s.acknowledge_created(ticket, 101))
        snap = s.snapshot()
        self.assertTrue(snap['core_situation_created'])
        self.assertFalse(snap['attendance_verified'])
        self.assertFalse(snap['ea_job_assignment_verified'])

    def test_eight_base_invites_in_original_eight_requests(self):
        s = session()
        # Both native EA school schedules call Base before Core.
        self.assertFalse(s.snapshot()['core_situation_created'])
        originals = []
        for index, expected in enumerate(s.manifest['base_ids']):
            old = EAList()
            originals.append(old)
            ticket, clone = s.preview(BASE_SITUATION, old, CONTEXT)
            self.assertEqual(ticket, 'base:' + expected)
            self.assertTrue(clone.invite_only)
            self.assertEqual([g.sim_id for g in clone.guest_info_gen()],
                             [int(expected)])
            self.assertEqual([g.job_type.guid64 for g in clone.guest_info_gen()],
                             [BASE_JOB])
            self.assertEqual(list(old.guest_info_gen()), [])
            self.assertTrue(s.acknowledge_created(ticket, index + 200))
        self.assertEqual(s.preview(BASE_SITUATION, EAList(), CONTEXT),
                         (None, None))
        self.assertFalse(s.snapshot()['all_nine_situations_created'])
        ticket, _ = s.preview(CORE_SITUATION, EAList(), CONTEXT)
        self.assertTrue(s.acknowledge_created(ticket, 100))
        snap = s.snapshot()
        self.assertTrue(snap['all_nine_situations_created'])
        self.assertFalse(snap['core_reservations_before_ea_verified'])
        self.assertEqual(snap['base_situations_created'], 8)
        self.assertEqual(len(set(snap['student_ids_requested'])), 13)
        self.assertEqual(len(snap['student_ids_requested']), 13)
        self.assertFalse(snap['attendance_verified'])
        self.assertFalse(snap['class_8_plus_8_verified'])

    def test_base_guest_occupied_by_ea_must_not_be_overwritten(self):
        s = session()
        token, _ = s.preview(CORE_SITUATION, EAList(), CONTEXT)
        s.acknowledge_created(token, 100)
        old = EAList()
        old.add_guest_info(Guest(999, Job(BASE_JOB)))
        self.assertEqual(s.preview(BASE_SITUATION, old, CONTEXT), (None, None))
        self.assertEqual([x.sim_id for x in old.guest_info_gen()], [999])

    def test_failed_or_duplicate_creation_receipt_cannot_skip_a_base_child(self):
        s = session()
        token, _ = s.preview(CORE_SITUATION, EAList(), CONTEXT)
        self.assertTrue(s.acknowledge_created(token, 100))
        token, _ = s.preview(BASE_SITUATION, EAList(), CONTEXT)
        self.assertEqual(token, 'base:5')
        self.assertFalse(s.acknowledge_created(token, 100))  # Duplicate ID.
        self.assertTrue(s.cancel(token))
        token, _ = s.preview(BASE_SITUATION, EAList(), CONTEXT)
        self.assertEqual(token, 'base:5')
        self.assertTrue(s.acknowledge_created(token, 101))
        self.assertEqual(s.preview(111111, EAList(), CONTEXT), (None, None))

    def test_unsupported_job_mapping_fails_closed(self):
        with self.assertRaises(InvitationPlanError):
            SchoolNativeGuestSession(
                session().manifest, EAInfo, 'INVITED',
                {BASE_JOB: Job(BASE_JOB)})

    def test_native_situation_id_not_school_arrival_or_ea_job(self):
        s = session()
        s.preview(CORE_SITUATION, EAList(), CONTEXT)
        evidence = s.snapshot()
        self.assertEqual(evidence['base_situations_created'], 0)
        self.assertFalse(evidence['all_nine_situations_created'])
        self.assertFalse(evidence['ea_job_assignment_verified'])


if __name__ == '__main__':
    unittest.main()
