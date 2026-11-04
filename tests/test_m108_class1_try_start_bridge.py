"""Class1 M108 dual-route -> original EA try_start, offline integration tests.

All controls are synthetic; no actual EA metaclass, Bouncer or game
attendance is exercised, and there is no installer in release builds.
"""
import sys
import unittest
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src' / 'm108_native_roster'))

from mhs108_class1_try_start_bridge import (
    install_offline_only, REQUIRED_LIVE_GATES,
)
from mhs108_class1_dual_route_budget import (
    ClassOneDualRouteBudget,
)
from tests.test_m108_class1_shadow_cap import original_class
from tests.test_m108_class1_dual_route_budget import (
    coordinator, manifest, counts,
    school_context,
)

ALL = tuple(str(x) for x in range(1, 17))
EXTRAS = ('200', '201', '999')


class Sim(object):
    def __init__(self, sid):
        self.sim_id = int(sid)

    def __hash__(self):
        return self.sim_id

    def __eq__(self, other):
        return isinstance(other, Sim) and other.sim_id == self.sim_id


class Filter(object):
    def __init__(self, allowed):
        self.allowed = frozenset(str(x) for x in allowed)

    def run_tests(self, sim):
        return str(sim.sim_id) in self.allowed


def proved():
    # Synthetic flags only. No verified provider exists inside The Sims.
    return {key: True for key in REQUIRED_LIVE_GATES}


def stage_fixture(phase='lesson', with_ids=('2', '3'),
                  no_ids=('4', '5', '6', '7', '8'),
                  played=('1', '9', '16'),
                  created=True, only_one=False):
    class NativeEA(object):
        seen = []
        created_ids = []
        calls = 0

        @classmethod
        def try_start(cls, sims, sim_info, duration, extra_ids, job_counts):
            NativeEA.calls += 1
            entry = cls.job_assignments[0]
            cap = entry.sim_count.upper_bound
            for modifier in entry.upper_bound_count_modifiers:
                cap -= job_counts[(modifier.situation, modifier.job)]
            if cap <= 0:
                return None
            ids = tuple(sorted((sim for sim in sims
                                if entry.tests.run_tests(sim)),
                               key=lambda x: x.sim_id))
            selected = ids[:min(cap, 1) if only_one else cap]
            if not selected or not created:
                return None
            NativeEA.seen.append(
                (cls.guid64, tuple(s.sim_id for s in selected),
                 str(cls), entry.sim_count.upper_bound))
            new_id = 1000 + len(NativeEA.seen)
            NativeEA.created_ids.append(new_id)
            sims.difference_update(selected)
            job_counts[(cls.situation, entry.job)] += len(selected)
            return new_id

    # Real EA snippet classes inherit the same WeeklyScheduleSituationData
    # classmethod. The original-class fixtures hold tuned attributes only.
    def derive(tuning, name):
        keys = ('guid64', 'situation', 'job_assignments', 'user_facing',
                'default_job_order', 'default_met_minimum_jobs',
                'default_need_minimum_jobs')
        attrs = {key: getattr(tuning, key) for key in keys}
        return type(name, (NativeEA,), attrs)

    with_cls = derive(original_class(phase, 'with_trait'), 'WithTrait')
    no_cls = derive(original_class(phase, 'no_trait'), 'NoTrait')
    refs = {}
    def unify(obj):
        guid = obj.guid64
        return refs.setdefault(guid, obj)
    for cls in (with_cls, no_cls):
        cls.situation = unify(cls.situation)
        for job_entry in cls.job_assignments:
            job_entry.job = unify(job_entry.job)
            for modifier in job_entry.upper_bound_count_modifiers:
                modifier.situation = unify(modifier.situation)
                modifier.job = unify(modifier.job)
            cls.default_job_order = [job_entry.job]
            cls.default_met_minimum_jobs = {job_entry.job: job_entry}
            cls.default_need_minimum_jobs = {}
    with_cls.job_assignments[0].tests = Filter(with_ids)
    no_cls.job_assignments[0].tests = Filter(no_ids)

    game_counts = defaultdict(int)
    player_mod = with_cls.job_assignments[0].upper_bound_count_modifiers[0]
    game_counts[(player_mod.situation, player_mod.job)] = len(played)
    clock = '10:00' if phase == 'lesson' else '09:30'
    budget = coordinator(played=played, phase=phase, clock=clock)

    ctx = dict(school_context(played=played, clock=clock),
               mhs_class1_dual_route_active=True,
               ea_job_counts_verified=True,
               ea_route_test_results_verified=True,
               native_ea_candidate_set_verified=True)
    result = install_offline_only(NativeEA,
                                  lambda cls, context: budget,
                                  lambda cls: dict(
                                      ctx,
                                      verified_native_eligible_ids=(
                                          with_ids if cls is with_cls
                                          else no_ids)),
                                  proved())
    assert callable(result)
    sims = {Sim(sid) for sid in ALL + EXTRAS}
    return (NativeEA, with_cls, no_cls, budget, game_counts, sims,
            ctx, result)


def execute(cls, sims, counts):
    return cls.try_start(sims, None, 'EA_DURATION', (), counts)


class Class1DualRouteTryStartTests(unittest.TestCase):
    def test_without_any_proof_the_ea_class_is_never_patched(self):
        for missing in REQUIRED_LIVE_GATES:
            class EA(object):
                @classmethod
                def try_start(cls, *args):
                    return 7
            proof = proved()
            proof[missing] = False
            undo = install_offline_only(
                EA, lambda cls, ctx: None, lambda cls: {}, proof)
            self.assertIsNone(undo)
            self.assertEqual(EA.try_start(None), 7)

    def test_both_routes_exactly_seven_npcs_no_duplicates(self):
        NativeEA, first, second, budget, counts, sims, ctx, undo = (
            stage_fixture())
        try:
            original_count = len(sims)
            first_id = execute(first, sims, counts)
            self.assertEqual(first_id, 1001)
            self.assertEqual(NativeEA.seen[0][1], (2, 3))
            self.assertEqual(NativeEA.seen[0][3], 5)
            self.assertEqual(counts[
                (first.situation, first.job_assignments[0].job)], 2)
            self.assertEqual(len(sims), original_count - 2)
            second_id = execute(second, sims, counts)
            self.assertEqual(second_id, 1002)
            self.assertEqual(NativeEA.seen[1][1], (4, 5, 6, 7, 8))
            self.assertEqual(NativeEA.seen[1][3], 10)
            self.assertEqual(NativeEA.calls, 2)
            self.assertTrue(budget.snapshot()['phase_plan_complete_offline'])
            self.assertEqual(
                {s.sim_id for s in sims},
                {1, 9, 10, 11, 12, 13, 14, 15, 16, 200, 201, 999})
            self.assertEqual(
                first.job_assignments[0].sim_count.upper_bound, 6)
            self.assertEqual(
                second.job_assignments[0].sim_count.upper_bound, 6)
            self.assertFalse(
                budget.snapshot()['actual_ea_bouncer_acceptance_verified'])
            self.assertFalse(
                budget.snapshot()['actual_ea_classroom_seating_verified'])
        finally:
            self.assertTrue(undo())

    def test_no_trait_first_then_with_trait_must_not_repeat_students(self):
        NativeEA, with_class, no_class, budget, counts, sims, ctx, undo = (
            stage_fixture(with_ids=('2', '3'), no_ids=('2', '3', '4', '5', '6', '7', '8')))
        try:
            self.assertEqual(execute(no_class, sims, counts), 1001)
            self.assertEqual(NativeEA.seen[0][1],
                             (2, 3, 4, 5, 6, 7, 8))
            self.assertIsNone(execute(with_class, sims, counts))
            self.assertEqual(NativeEA.calls, 1)  # empty second route skips EA
            self.assertTrue(budget.snapshot()['phase_plan_complete_offline'])
        finally:
            undo()

    def test_no_sim_passes_with_trait_but_other_route_assigns_exact_seven(self):
        NativeEA, with_class, no_class, budget, counts, sims, ctx, undo = (
            stage_fixture(with_ids=(), no_ids=('2', '3', '4', '5', '6', '7', '8')))
        try:
            self.assertIsNone(execute(with_class, sims, counts))
            self.assertEqual(NativeEA.calls, 0)
            self.assertEqual(execute(no_class, sims, counts), 1001)
            self.assertEqual(NativeEA.seen[0][1],
                             (2, 3, 4, 5, 6, 7, 8))
            self.assertTrue(budget.snapshot()['phase_plan_complete_offline'])
        finally:
            undo()

    def test_native_partial_assignment_blocks_but_does_not_retry_or_remove_shared(self):
        NativeEA, first, second, budget, counts, sims, ctx, undo = (
            stage_fixture(only_one=True))
        try:
            original = set(sims)
            # EA created its one partial situation, but not for both IDs.
            self.assertEqual(execute(first, sims, counts), 1001)
            self.assertEqual(NativeEA.calls, 1)
            self.assertEqual(sims, original)
            self.assertTrue(budget.snapshot()['blocked'])
            self.assertIsNone(execute(second, sims, counts))
            self.assertEqual(NativeEA.calls, 1)
        finally:
            undo()

    def test_native_creation_failure_never_advances_or_reattempts(self):
        NativeEA, first, second, budget, counts, sims, ctx, undo = (
            stage_fixture(created=False))
        try:
            before = set(sims)
            self.assertIsNone(execute(first, sims, counts))
            self.assertEqual(NativeEA.calls, 1)
            self.assertEqual(sims, before)
            self.assertTrue(budget.snapshot()['blocked'])
            self.assertIsNone(execute(first, sims, counts))
            self.assertEqual(NativeEA.calls, 1)
        finally:
            undo()

    def test_wrong_player_modifier_count_blocks_without_native_original(self):
        NativeEA, first, second, budget, counts, sims, ctx, undo = (
            stage_fixture())
        try:
            mod = first.job_assignments[0].upper_bound_count_modifiers[0]
            counts[(mod.situation, mod.job)] = 2
            original = set(sims)
            self.assertIsNone(execute(first, sims, counts))
            self.assertEqual(NativeEA.calls, 0)
            self.assertEqual(sims, original)
            self.assertFalse(budget.snapshot()['phase_plan_complete_offline'])
        finally:
            undo()

    def test_class1_with_two_players_has_six_npc_seats(self):
        NativeEA, first, second, budget, counts, sims, ctx, undo = (
            stage_fixture(played=('1', '5', '9'),
                          with_ids=('2', '3'),
                          no_ids=('4', '6', '7', '8')))
        try:
            execute(first, sims, counts)
            execute(second, sims, counts)
            self.assertTrue(budget.snapshot()['phase_plan_complete_offline'])
            self.assertEqual(budget.snapshot()['exact_npc_required'], 6)
            self.assertEqual(len({s.sim_id for s in sims} &
                                 {2, 3, 4, 6, 7, 8}), 0)
        finally:
            undo()

    def test_original_unrelated_ea_situation_remains_untouched(self):
        NativeEA, with_cl, no_cl, budget, counts, sims, ctx, undo = (
            stage_fixture())
        class Other(NativeEA):
            guid64 = 999999
            situation = with_cl.situation
            job_assignments = with_cl.job_assignments
            default_job_order = with_cl.default_job_order
            default_met_minimum_jobs = with_cl.default_met_minimum_jobs
            default_need_minimum_jobs = with_cl.default_need_minimum_jobs
        try:
            # Original receives all candidates, including unregistered 999.
            _ = execute(Other, sims, counts)
            self.assertEqual(NativeEA.calls, 1)
            self.assertNotEqual(len(sims), 19)
        finally:
            undo()

    def test_second_hook_or_old_adapter_must_not_stack(self):
        NativeEA, with_cl, no_cl, budget, counts, sims, ctx, undo = (
            stage_fixture())
        try:
            self.assertIsNone(
                install_offline_only(
                    NativeEA, lambda cls, ctx: budget, lambda cls: ctx,
                    proved()))
        finally:
            undo()
        # Old M108 hook must also block Class1 bridge.
        class Other(object):
            @classmethod
            def try_start(cls, *args):
                return None
        fn = Other.__dict__['try_start'].__func__
        fn._mhs108_exact_phase = True
        self.assertIsNone(install_offline_only(
            Other, lambda cls, ctx: budget, lambda cls: ctx, proved()))

    def test_generic_m108_phase_adapter_cannot_stack_after_class1_bridge(self):
        from mhs108_ea_phase_adapter import (
            install_offline_only as install_generic,
            REQUIRED_LIVE_GATES as GENERIC_GATES,
        )
        NativeEA, with_cl, no_cl, budget, counts, sims, ctx, undo = (
            stage_fixture())
        try:
            self.assertIsNone(install_generic(
                NativeEA, manifest(), lambda cls: dict(ctx),
                {k: True for k in GENERIC_GATES}))
        finally:
            undo()

    def test_original_ea_source_tuning_remains_six_after_uninstall(self):
        NativeEA, with_cl, no_cl, budget, counts, sims, ctx, undo = (
            stage_fixture())
        try:
            execute(with_cl, sims, counts)
        finally:
            self.assertTrue(undo())
        self.assertFalse(undo())
        self.assertEqual(with_cl.job_assignments[0].sim_count.upper_bound, 6)
        self.assertEqual(no_cl.job_assignments[0].sim_count.upper_bound, 6)


if __name__ == '__main__':
    unittest.main()
