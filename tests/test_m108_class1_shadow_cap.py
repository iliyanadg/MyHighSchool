"""Verify Class1 native original caps can be projected without EA tuning writes."""
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace as Obj

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src' / 'm108_native_roster'))

from mhs108_class1_shadow_cap import project_class1_tuning
from mhs108_class1_dual_route_budget import (
    PHASES, STUDENT_JOB, EA_PLAYER_JOB,
)
from tests.test_m108_class1_dual_route_budget import (
    coordinator, ticket,
)


class Ref(object):
    def __init__(self, guid):
        self.guid64 = guid


def original_class(phase='lesson', route='with_trait'):
    data = PHASES[phase]
    guid = data['with_trait_data' if route == 'with_trait'
                else 'no_trait_data']
    situation = data['with_trait_situation' if route == 'with_trait'
                     else 'no_trait_situation']
    player = Obj(situation=Ref(data['player_situation']),
                 job=Ref(EA_PLAYER_JOB))
    modifiers = [player]
    if route == 'no_trait':
        modifiers.append(Obj(
            situation=Ref(data['with_trait_situation']),
            job=Ref(STUDENT_JOB)))
    tests = Obj(tag='exact original EA eligibility tests')
    entry = Obj(
        job=Ref(STUDENT_JOB),
        sim_count=Obj(lower_bound=0, upper_bound=6),
        tests=tests, upper_bound_count_modifiers=tuple(modifiers))

    situation_ref = Ref(situation)
    class EAOriginalClass1Data(object):
        guid64 = guid
        job_assignments = (entry,)
        situation = situation_ref
        user_facing = 'EA_NATIVE_USER_FACING_NEVER'
        default_job_order = [entry.job]
        default_met_minimum_jobs = {entry.job: entry}
        default_need_minimum_jobs = {}

    return EAOriginalClass1Data


class NativeClass1ShadowTests(unittest.TestCase):
    def test_shadow_class1_with_trait_is_isolated_from_original_tuning(self):
        b = coordinator()
        first = ticket(b, 'with_trait', ('2', '3'))
        original = original_class()
        projected = project_class1_tuning(original, first)
        self.assertIsNotNone(projected)
        self.assertIsNot(projected, original)
        self.assertEqual(str(projected), str(original))
        self.assertEqual(projected.guid64, original.guid64)
        self.assertIs(projected.situation, original.situation)
        self.assertIs(projected.user_facing, original.user_facing)
        self.assertIs(projected.job_assignments[0].tests,
                      original.job_assignments[0].tests)
        self.assertIs(projected.job_assignments[0].job,
                      original.job_assignments[0].job)
        self.assertIs(
            projected.job_assignments[0].upper_bound_count_modifiers,
            original.job_assignments[0].upper_bound_count_modifiers)
        self.assertEqual(
            projected.job_assignments[0].sim_count.upper_bound, 5)
        self.assertEqual(
            original.job_assignments[0].sim_count.upper_bound, 6)
        self.assertIs(projected.default_met_minimum_jobs[
            original.job_assignments[0].job],
            projected.job_assignments[0])
        self.assertEqual(projected.default_need_minimum_jobs, {})

    def test_no_trait_cap_subtracts_observed_global_players_and_with_trait(self):
        b = coordinator()
        first = ticket(b, 'with_trait', ('2', '3'))
        self.assertTrue(b.confirm(first, (2, 3), 100))
        last = ticket(
            b, 'no_trait', ('4', '5', '6', '7', '8'),
            previous_with=2)
        original = original_class(route='no_trait')
        projected = project_class1_tuning(original, last)
        self.assertIsNotNone(projected)
        self.assertEqual(
            projected.job_assignments[0].sim_count.upper_bound, 10)
        modifiers = 3 + 2
        self.assertEqual(
            projected.job_assignments[0].sim_count.upper_bound - modifiers,
            len(last['exact_candidate_ids']))
        self.assertEqual(original.job_assignments[0].sim_count.upper_bound, 6)
        self.assertEqual(len(original.job_assignments), 1)
        self.assertEqual(len(projected.job_assignments), 1)

    def test_same_projection_for_both_class1_school_periods(self):
        for stage, when in (
                ('prepare', '09:30'), ('prepare', '13:30'),
                ('lesson', '10:00'), ('lesson', '14:00')):
            b = coordinator(phase=stage, clock=when)
            first = ticket(b, 'with_trait', ('2', '3'))
            orig = original_class(phase=stage)
            view = project_class1_tuning(orig, first)
            self.assertIsNotNone(view)
            self.assertEqual(view.job_assignments[0].sim_count.upper_bound, 5)

    def test_unknown_ea_tuning_or_original_ea_change_is_not_overwritten(self):
        b = coordinator()
        first = ticket(b, 'with_trait', ('2', '3'))
        original = original_class()
        original.guid64 = 999
        self.assertIsNone(project_class1_tuning(original, first))
        original = original_class()
        original.job_assignments[0].sim_count.upper_bound = 7
        self.assertIsNone(project_class1_tuning(original, first))
        original = original_class()
        original.job_assignments[0].upper_bound_count_modifiers = ()
        self.assertIsNone(project_class1_tuning(original, first))
        original = original_class()
        original.job_assignments[0].job = Ref(222)
        self.assertIsNone(project_class1_tuning(original, first))
        original = original_class()
        original.job_assignments += (original.job_assignments[0],)
        self.assertIsNone(project_class1_tuning(original, first))

    def test_ticket_must_match_same_branch_and_original_job(self):
        b = coordinator()
        first = ticket(b, 'with_trait', ('2', '3'))
        original = original_class()
        for change in (
            {'data_guid': 304561},
            {'route': 'no_trait'},
            {'phase': 'prepare'},
            {'native_situation': 304703},
            {'native_student_job': 280777},
            {'native_original_tuned_upper': 8},
            {'changes_to_ea_tuning': True},
            {'exact_candidate_ids': ('2', '2')},
            {'proposed_per_call_tuned_upper': 10},
            {'proposed_effective_upper': 200},
        ):
            self.assertIsNone(project_class1_tuning(
                original, dict(first, **change)), msg=str(change))

    def test_projection_is_only_a_plan_not_proof_of_ea_seating(self):
        b = coordinator()
        first = ticket(b, 'with_trait', ('2', '3'))
        view = project_class1_tuning(original_class(), first)
        self.assertEqual(view.job_assignments[0].sim_count.upper_bound, 5)
        self.assertFalse(first['native_phase_assignments_verified'])
        self.assertFalse(b.snapshot()['actual_ea_classroom_seating_verified'])


if __name__ == '__main__':
    unittest.main()
