"""M108 no-show/departure protection — offline synthetic EA callbacks only."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src' / 'm108_native_roster'))

from mhs108_school_filter_scope import (
    install_offline_only as install_scope,
)
from mhs108_no_show_guard import (
    SchoolNoShowGuard, REQUIRED_NO_SHOW_PROOFS,
    install_offline_only as install_guard,
)
from tests.test_m108_school_filter_scope import (
    Request, Job, SchoolBase, SchoolCore, OtherSituation, ORIGINAL, BLANK,
    BASE_JOB, make_scope, proofs as filter_proofs, BASE_CONTEXT,
)


class DummyRequest(Request):
    """Stand-in for the original EA clone operation dropping the ID."""

    def clone_for_replace(self, only_if_explicit=False):
        # EA returns a fresh unconstrained request: a potential random NPC.
        return {'requested_sim_id': 0,
                'source_requested_sim_id': self._requested_sim_id,
                'only_if_explicit': only_if_explicit}


def guard_proofs():
    # Synthetic fixture ONLY. No in-game origin verification has occurred.
    return {k: True for k in REQUIRED_NO_SHOW_PROOFS}


def installed_hooks(context=None):
    class NativeRequest(DummyRequest):
        pass
    scope = make_scope(overrides=context)
    unfilter = install_scope(
        NativeRequest, scope, filter_proofs())
    assert callable(unfilter)
    guard = SchoolNoShowGuard(scope)
    unguard = install_guard(NativeRequest, guard, guard_proofs())
    assert callable(unguard)
    return NativeRequest, scope, guard, unguard, unfilter


class NoShowGuardTests(unittest.TestCase):
    def test_neither_overlay_nor_guard_is_live_without_proofs(self):
        class NativeRequest(DummyRequest):
            pass
        scope = make_scope()
        guard = SchoolNoShowGuard(scope)
        for key in REQUIRED_NO_SHOW_PROOFS:
            evidence = guard_proofs()
            evidence[key] = False
            self.assertIsNone(install_guard(NativeRequest, guard, evidence))
        self.assertEqual(
            NativeRequest(SchoolBase(), Job(BASE_JOB), 5)
            .clone_for_replace()['requested_sim_id'], 0)

    def test_exact_school_base_no_show_cannot_request_random_replacement(self):
        NativeRequest, scope, guard, unguard, unfilter = installed_hooks()
        req = NativeRequest(SchoolBase(), Job(BASE_JOB), 5)
        self.assertIs(req._sim_filter, BLANK)
        self.assertIsNone(req.clone_for_replace(only_if_explicit=True))
        self.assertEqual(guard.snapshot()['suppressed_random_student_clones'], 1)
        self.assertFalse(guard.snapshot()['student_no_show_fallback_fully_blocked'])
        self.assertTrue(unguard())
        # Removal of the guard cannot change the external EA method.
        self.assertEqual(req.clone_for_replace(only_if_explicit=True)
                         ['requested_sim_id'], 0)
        self.assertTrue(unfilter())

    def test_departure_callback_clears_student_without_submitting_replacement(self):
        NativeRequest, scope, guard, unguard, unfilter = installed_hooks()
        class FakeSituation(object):
            def __init__(self):
                self.members = {5}
                self.submitted = []
            def on_unassign(self, sim_id, request):
                # Same order as EA BaseSituation.submit_replace_request:
                # remove student first; then clone; then submit iff not None.
                self.members.remove(sim_id)
                clone = request.clone_for_replace()
                if clone is not None:
                    self.submitted.append(clone)
        req = NativeRequest(SchoolBase(), Job(BASE_JOB), 5)
        situation = FakeSituation()
        situation.on_unassign(5, req)
        self.assertEqual(situation.members, set())
        self.assertEqual(situation.submitted, [])
        self.assertEqual(guard.snapshot()['suppressed_random_student_clones'], 1)
        self.assertTrue(unguard())
        self.assertTrue(unfilter())

    def test_all_five_core_role_holders_cannot_be_cloned_randomly(self):
        NativeRequest, scope, guard, unguard, unfilter = installed_hooks()
        pins = ((278965, 2), (278966, 3), (278967, 4),
                (278968, 10), (303765, 11))
        for job, sid in pins:
            req = NativeRequest(SchoolCore(), Job(job), sid)
            self.assertIs(req._sim_filter, BLANK)
            self.assertIsNone(req.clone_for_replace())
            self.assertIsNone(req.clone_for_replace(only_if_explicit=True))
        self.assertEqual(guard.snapshot()['suppressed_random_student_clones'], 10)
        self.assertTrue(unguard())
        self.assertTrue(unfilter())

    def test_other_sim_and_teacher_still_use_original_ea_replacement(self):
        NativeRequest, scope, guard, unguard, unfilter = installed_hooks()
        other = NativeRequest(OtherSituation(), Job(BASE_JOB), 5)
        teacher = NativeRequest(SchoolCore(), Job(277895), 8)
        random = NativeRequest(SchoolBase(), Job(BASE_JOB), 0)
        wrong_core = NativeRequest(SchoolCore(), Job(278965), 12)
        for req in (other, teacher, random, wrong_core):
            self.assertIs(req._sim_filter, ORIGINAL)
            self.assertEqual(req.clone_for_replace()['requested_sim_id'], 0)
            self.assertEqual(
                req.clone_for_replace(only_if_explicit=True)['requested_sim_id'], 0)
        self.assertEqual(guard.snapshot()['suppressed_random_student_clones'], 0)
        self.assertEqual(guard.snapshot()['outside_school_clone_calls_preserved'], 8)
        self.assertTrue(unguard())
        self.assertTrue(unfilter())

    def test_alternate_student_request_does_not_qualify(self):
        NativeRequest, scope, guard, unguard, unfilter = installed_hooks()
        req = NativeRequest(
            SchoolBase(), Job(BASE_JOB), 5, accept_alternate_sim=True)
        self.assertIs(req._sim_filter, ORIGINAL)
        self.assertEqual(req.clone_for_replace()['requested_sim_id'], 0)
        self.assertTrue(unguard())
        self.assertTrue(unfilter())

    def test_context_changed_or_non_school_day_restores_vanilla(self):
        NativeRequest, scope, guard, unguard, unfilter = installed_hooks(
            {'sim_day': 13})
        req = NativeRequest(SchoolBase(), Job(BASE_JOB), 5)
        self.assertIs(req._sim_filter, ORIGINAL)
        self.assertEqual(req.clone_for_replace()['requested_sim_id'], 0)
        self.assertEqual(guard.snapshot()['suppressed_random_student_clones'], 0)
        self.assertTrue(unguard())
        self.assertTrue(unfilter())

    def test_guard_does_not_stack_and_restores_original_cloner(self):
        NativeRequest, scope, guard, unguard, unfilter = installed_hooks()
        self.assertIsNone(
            install_guard(NativeRequest, SchoolNoShowGuard(scope),
                          guard_proofs()))
        self.assertTrue(unguard())
        self.assertFalse(unguard())
        req = NativeRequest(SchoolBase(), Job(BASE_JOB), 5)
        self.assertEqual(req.clone_for_replace()['requested_sim_id'], 0)
        self.assertTrue(unfilter())


if __name__ == '__main__':
    unittest.main()
