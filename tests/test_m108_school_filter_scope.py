"""M108 Bouncer request filter scope: synthetic safety tests only.

Never interpret test success as evidence of native EA SimFilter acceptance.
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src' / 'm108_native_roster'))
from tests.test_m108_native_invitation import session, CORE_JOBS
from mhs108_school_filter_scope import (
    BASE_JOB, BASE_SITUATION, CORE_SITUATION, REQUIRED_FILTER_PROOF,
    SchoolFilterScope, install_offline_only)


class Filter(object):
    def get_filter_terms(self):
        return ()


ORIGINAL = Filter()
BLANK = Filter()


class Job(object):
    def __init__(self, guid):
        self.guid64 = guid
        self.filter = ORIGINAL


class SchoolBase(object):
    guid64 = BASE_SITUATION


class SchoolCore(object):
    guid64 = CORE_SITUATION


class OtherSituation(object):
    guid64 = 99990


class Info(object):
    def __init__(self, sid, age='TEEN', species='HUMAN', selectable=False):
        self.sim_id = sid
        self.age = age
        self.species = species
        self.is_selectable = selectable


class Request(object):
    def __init__(self, situation, job, requested_sim_id,
                 accept_alternate_sim=False, for_persisted_sim=False):
        self._situation = situation
        self._job_type = job
        self._sim_filter = job.filter
        self._requested_sim_id = requested_sim_id
        self._constrained_sim_ids = ({requested_sim_id}
                                     if requested_sim_id else None)
        self._continue_if_constraints_fail = accept_alternate_sim
        self._for_persisted_sim = for_persisted_sim
        self.blacklist = {44, 55}

    def get_additional_filter_terms(self):
        return ('keep-EA-terms',)


BASE_CONTEXT = {
    'native_school_bouncer_origin_verified': True,
    'school_verified': True,
    'schedule_guid': 277657,
    'save_slot': '11',
    'sim_day': 12,
    'zone_id': '777'
}


def proofs():
    # Only synthetic flags for testing. No production caller exists.
    return {key: True for key in REQUIRED_FILTER_PROOF}


def make_scope(overrides=None, extra_info=None):
    context = dict(BASE_CONTEXT)
    if overrides:
        context.update(overrides)
    infos = {sid: Info(sid, selectable=sid in (1, 9, 16))
             for sid in range(1, 17)}
    if extra_info:
        infos.update(extra_info)
    return SchoolFilterScope(session(), BLANK, 'TEEN', 'HUMAN',
                             infos.get, lambda: context)


class FilterScopeTests(unittest.TestCase):
    def test_unproven_gates_refuse_to_patch_ea_class(self):
        for missing in REQUIRED_FILTER_PROOF:
            class NativeRequest(Request):
                pass
            gate = proofs()
            gate[missing] = False
            scope = make_scope()
            self.assertIsNone(install_offline_only(NativeRequest, scope, gate))
            req = NativeRequest(SchoolBase(), Job(BASE_JOB), 5)
            self.assertIs(req._sim_filter, ORIGINAL)
            self.assertEqual(req.get_additional_filter_terms(),
                             ('keep-EA-terms',))

    def test_exact_base_only_bypasses_job_terms_for_one_request(self):
        class NativeRequest(Request):
            pass
        scope = make_scope()
        undo = install_offline_only(NativeRequest, scope, proofs())
        self.assertTrue(callable(undo))
        targeted = NativeRequest(SchoolBase(), Job(BASE_JOB), 5)
        outside = NativeRequest(OtherSituation(), Job(BASE_JOB), 6)
        teacher = NativeRequest(SchoolCore(), Job(277895), 8)
        self.assertIs(targeted._sim_filter, BLANK)
        self.assertIs(targeted._job_type.filter, ORIGINAL)
        self.assertEqual(targeted.get_additional_filter_terms(), ())
        self.assertEqual(targeted.blacklist, {44, 55})
        self.assertIs(outside._sim_filter, ORIGINAL)
        self.assertEqual(outside.get_additional_filter_terms(),
                         ('keep-EA-terms',))
        self.assertIs(teacher._sim_filter, ORIGINAL)
        self.assertEqual(teacher.get_additional_filter_terms(),
                         ('keep-EA-terms',))
        self.assertEqual(scope.snapshot()['requests_proposed'], 1)
        self.assertFalse(scope.snapshot()['native_filter_runtime_verified'])
        self.assertTrue(undo())
        self.assertIs(targeted._sim_filter, ORIGINAL)
        self.assertEqual(targeted.get_additional_filter_terms(),
                         ('keep-EA-terms',))
        self.assertFalse(undo())

    def test_exact_five_special_roles_respect_user_mapping(self):
        class NativeRequest(Request):
            pass
        scope = make_scope()
        undo = install_offline_only(NativeRequest, scope, proofs())
        expected = {278965: 2, 278966: 3, 278967: 4,
                    278968: 10, 303765: 11}
        for job, sim in expected.items():
            allowed = NativeRequest(SchoolCore(), Job(job), sim)
            self.assertIs(allowed._sim_filter, BLANK)
            self.assertEqual(allowed.get_additional_filter_terms(), ())
            other = NativeRequest(SchoolCore(), Job(job), 12)
            self.assertIs(other._sim_filter, ORIGINAL)
            self.assertEqual(other.get_additional_filter_terms(),
                             ('keep-EA-terms',))
        self.assertEqual(scope.snapshot()['requests_proposed'], 5)
        self.assertTrue(undo())

    def test_reject_random_auto_fill_alt_playable_missing_pets_adults(self):
        class NativeRequest(Request):
            pass
        scope = make_scope(extra_info={
            5: Info(5, age='ADULT'),
            6: Info(6, species='DOG'),
            7: Info(7, selectable=True),
            8: None
        })
        undo = install_offline_only(NativeRequest, scope, proofs())
        for sid, extras in (
                (0, {}), (5, {}), (6, {}), (7, {}), (8, {}),
                (9, {}), (1, {}),
                (12, {'accept_alternate_sim': True}),
                (13, {'for_persisted_sim': True})):
            req = NativeRequest(SchoolBase(), Job(BASE_JOB), sid, **extras)
            self.assertIs(req._sim_filter, ORIGINAL)
            self.assertEqual(req.get_additional_filter_terms(),
                             ('keep-EA-terms',))
        self.assertEqual(scope.snapshot()['requests_proposed'], 0)
        self.assertTrue(undo())

    def test_wrong_job_situation_and_context_are_never_rewritten(self):
        for change in (
                {'native_school_bouncer_origin_verified': False},
                {'school_verified': False}, {'schedule_guid': 88},
                {'save_slot': 2}, {'sim_day': 13}, {'zone_id': 1}):
            class NativeRequest(Request):
                pass
            scope = make_scope(overrides=change)
            undo = install_offline_only(NativeRequest, scope, proofs())
            req = NativeRequest(SchoolBase(), Job(BASE_JOB), 5)
            self.assertIs(req._sim_filter, ORIGINAL)
            self.assertTrue(undo())

    def test_scope_restores_filter_when_school_context_changes(self):
        class NativeRequest(Request):
            pass
        context = dict(BASE_CONTEXT)
        scope = SchoolFilterScope(
            session(), BLANK, 'TEEN', 'HUMAN',
            lambda sid: Info(sid), lambda: context)
        undo = install_offline_only(NativeRequest, scope, proofs())
        req = NativeRequest(SchoolBase(), Job(BASE_JOB), 5)
        self.assertIs(req._sim_filter, BLANK)
        self.assertEqual(req.get_additional_filter_terms(), ())
        context['school_verified'] = False
        self.assertEqual(req.get_additional_filter_terms(),
                         ('keep-EA-terms',))
        self.assertIs(req._sim_filter, ORIGINAL)
        self.assertEqual(scope.snapshot()['tracked_requests'], 0)
        self.assertTrue(undo())

    def test_existing_global_hook_cannot_be_stacked(self):
        class NativeRequest(Request):
            pass
        first = make_scope()
        undo = install_offline_only(NativeRequest, first, proofs())
        self.assertIsNone(
            install_offline_only(NativeRequest, make_scope(), proofs()))
        self.assertTrue(undo())

    def test_other_job_remains_unmodified_even_if_id_matches(self):
        class NativeRequest(Request):
            pass
        scope = make_scope()
        undo = install_offline_only(NativeRequest, scope, proofs())
        for thing in (
                NativeRequest(SchoolBase(), Job(CORE_JOBS[0]), 2),
                NativeRequest(SchoolCore(), Job(BASE_JOB), 5),
                NativeRequest(SchoolCore(), Job(278965), 3)):
            self.assertIs(thing._sim_filter, ORIGINAL)
        self.assertTrue(undo())

    def test_request_scope_does_not_claim_in_game_success(self):
        scope = make_scope()
        snapshot = scope.snapshot()
        self.assertFalse(snapshot['native_bouncer_assignment_verified'])
        self.assertFalse(snapshot['attendance_verified'])


if __name__ == '__main__':
    unittest.main()
