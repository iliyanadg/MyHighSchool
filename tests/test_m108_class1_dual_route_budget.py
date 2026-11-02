"""Source-backed offline Class1 6+trait/no-trait routing regressions.

These tests prove planner arithmetic, not a live EA tuning override.
"""
import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src' / 'm108_native_roster'))
from mhs108_class1_dual_route_budget import (
    PHASES, STUDENT_JOB, EA_PLAYER_JOB, ClassOneDualRouteBudget,
)
from tests.test_m108_native_invitation import (
    CLASSES, CORE, prepare_fixed_manifest,
)

ASSETS = ROOT / 'assets' / 'ea_2026_11_01'


def manifest(played=('1', '9', '16')):
    return prepare_fixed_manifest(CLASSES, played, CORE, 11, 12, 777)


def school_context(played=('1', '9', '16'), clock='10:00', **overrides):
    value = {
        'native_school_phase_origin_verified': True,
        'school_verified': True,
        'schedule_guid': 277657,
        'save_slot': '11',
        'sim_day': 12,
        'zone_id': '777',
        'time_window': clock,
        'original_ea_player_jobs_verified': True,
        'original_ea_school_members_verified': True,
        'observed_ea_school_ids': CLASSES[0] + CLASSES[1],
        'observed_on_lot_ids': CLASSES[0] + CLASSES[1] + ('201', '202'),
        'observed_player_phase_ids': played,
    }
    value.update(overrides)
    return value


def coordinator(played=('1', '9', '16'), phase='lesson', clock=None):
    if clock is None:
        clock = '10:00' if phase == 'lesson' else '09:30'
    return ClassOneDualRouteBudget(
        manifest(played), phase, school_context(played, clock))


def counts(budget, previous_with=0, players=3):
    p = budget.tuning
    return {
        (p['player_situation'], EA_PLAYER_JOB): players,
        (p['with_trait_situation'], STUDENT_JOB): previous_with,
    }


def proof(budget):
    return {
        'ea_job_counts_verified': True,
        'ea_route_test_results_verified': True,
        'native_school_phase_origin_verified': True,
        'save_slot': '11',
        'sim_day': 12,
        'zone_id': '777',
        'time_window': budget.context['time_window'],
    }


def ticket(budget, route, eligible, previous_with=0, **changes):
    phase_guid = budget.tuning[
        'with_trait_data' if route == 'with_trait'
        else 'no_trait_data']
    return budget.prepare(
        phase_guid,
        counts(budget, previous_with),
        eligible,
        dict(proof(budget), **changes))


class NativeClassOneEAEvidence(unittest.TestCase):
    def test_all_four_original_class1_tunings_have_precise_modifiers(self):
        for stage, data in PHASES.items():
            for route, guid in (
                    ('with_trait', data['with_trait_data']),
                    ('no_trait', data['no_trait_data'])):
                root = ET.parse(str(ASSETS / ('%s.xml' % guid))).getroot()
                first_job = root.find("./L[@n='job_assignments']/U")
                self.assertEqual(
                    int(first_job.find("./T[@n='job']").text), STUDENT_JOB)
                self.assertEqual(
                    int(first_job.find(
                        "./U[@n='sim_count']/T[@n='upper_bound']").text), 6)
                modifiers = first_job.findall(
                    "./L[@n='upper_bound_count_modifiers']/U")
                present = set((
                    int(row.find("./T[@n='situation']").text),
                    int(row.find("./T[@n='job']").text))
                    for row in modifiers)
                expected = {(data['player_situation'], EA_PLAYER_JOB)}
                if route == 'no_trait':
                    expected.add((data['with_trait_situation'], STUDENT_JOB))
                self.assertEqual(present, expected, msg=str(guid))
                self.assertEqual(
                    int(root.find("./T[@n='situation']").text),
                    data['with_trait_situation'] if route == 'with_trait'
                    else data['no_trait_situation'])

    def test_hidden_trait_is_a_native_test_not_a_classroom_identity(self):
        for stage, data in PHASES.items():
            with_trait = ET.parse(
                str(ASSETS / ('%s.xml' % data['with_trait_data']))).getroot()
            no_trait = ET.parse(
                str(ASSETS / ('%s.xml' % data['no_trait_data']))).getroot()
            self.assertIn('293779', tuple(
                (el.text or '').strip() for el in
                with_trait.findall(".//L[@n='whitelist_traits']/T")))
            self.assertEqual(no_trait.findall(
                ".//L[@n='whitelist_traits']/T"), [])


class ClassOneBudgetTests(unittest.TestCase):
    def test_one_playable_class1_seven_npcs_split_between_original_routes(self):
        b = coordinator()
        # WithTrait only accepts two specific real enrolled students.
        first = ticket(b, 'with_trait', ('2', '3'))
        self.assertEqual(first['exact_candidate_ids'], ('2', '3'))
        self.assertEqual(first['proposed_per_call_tuned_upper'], 5)
        self.assertEqual(first['proposed_effective_upper'], 2)
        self.assertEqual(first['playables_in_global_ea_phase'], 3)
        self.assertEqual(first['playables_in_class1'], 1)
        self.assertFalse(first['changes_to_ea_tuning'])
        self.assertTrue(b.confirm(first, (2, 3), 100))
        # Native NoTrait references the actual prior WithTrait job count
        # and the total EA player job count, not only Class1 players.
        second = ticket(
            b, 'no_trait', ('2', '3', '4', '5', '6', '7', '8', '99'),
            previous_with=2)
        self.assertEqual(second['exact_candidate_ids'],
                         ('4', '5', '6', '7', '8'))
        self.assertEqual(second['native_original_effective_upper'], 1)
        self.assertEqual(second['proposed_per_call_tuned_upper'], 10)
        self.assertEqual(second['proposed_effective_upper'], 5)
        self.assertTrue(b.confirm(second, (4, 5, 6, 7, 8), 101))
        snap = b.snapshot()
        self.assertTrue(snap['phase_plan_complete_offline'])
        self.assertEqual(snap['exact_npc_required'], 7)
        self.assertEqual(snap['missing_registered_npc_ids'], ())
        self.assertFalse(snap['actual_ea_bouncer_acceptance_verified'])
        self.assertFalse(snap['actual_ea_classroom_seating_verified'])

    def test_2_playable_in_class1_reduces_required_npc_to_six(self):
        played = ('1', '5', '9')  # none of the 5 Core holders replaced
        b = coordinator(played)
        first = ticket(b, 'with_trait', ('2', '3'))
        self.assertEqual(first['exact_candidate_ids'], ('2', '3'))
        self.assertTrue(b.confirm(first, (2, 3), 401))
        last = ticket(b, 'no_trait', ('4', '6', '7', '8'),
                      previous_with=2)
        self.assertEqual(last['proposed_per_call_tuned_upper'], 9)
        self.assertEqual(last['proposed_effective_upper'], 4)
        self.assertTrue(b.confirm(last, (4, 6, 7, 8), 402))
        self.assertEqual(b.snapshot()['exact_npc_required'], 6)
        self.assertTrue(b.snapshot()['phase_plan_complete_offline'])

    def test_zero_playable_class1_requires_all_eight_npcs(self):
        played = ('9', '12', '16')
        b = coordinator(played)
        with_trait = ticket(b, 'with_trait', ('2', '3', '4', '5'))
        self.assertEqual(with_trait['proposed_per_call_tuned_upper'], 7)
        self.assertTrue(b.confirm(with_trait, (2, 3, 4, 5), 501))
        no_trait = ticket(b, 'no_trait', ('6', '7', '8', '1'),
                          previous_with=4)
        self.assertEqual(no_trait['proposed_per_call_tuned_upper'], 11)
        self.assertEqual(no_trait['exact_candidate_ids'],
                         ('1', '6', '7', '8'))
        self.assertTrue(b.confirm(no_trait, (1, 6, 7, 8), 502))
        self.assertEqual(b.snapshot()['exact_npc_required'], 8)
        self.assertTrue(b.snapshot()['phase_plan_complete_offline'])

    def test_no_trait_fills_everyone_if_no_sim_has_class1_trait(self):
        b = coordinator()
        first = ticket(b, 'with_trait', ())
        self.assertEqual(first['exact_candidate_ids'], ())
        self.assertEqual(first['proposed_per_call_tuned_upper'], 3)
        self.assertTrue(b.confirm(first, (), None))  # EA does not create.
        last = ticket(b, 'no_trait', CLASSES[0], previous_with=0)
        self.assertEqual(last['proposed_per_call_tuned_upper'], 10)
        self.assertEqual(last['proposed_effective_upper'], 7)
        self.assertTrue(b.confirm(last, (2, 3, 4, 5, 6, 7, 8), 611))
        self.assertTrue(b.snapshot()['phase_plan_complete_offline'])

    def test_branch_order_not_assumed_from_missing_situation_set_xml(self):
        # If NoTrait runs first it can take exactly the Class1 students
        # and the second, WithTrait, must see zero candidates.
        b = coordinator()
        first = ticket(b, 'no_trait', CLASSES[0], previous_with=0)
        self.assertEqual(first['proposed_per_call_tuned_upper'], 10)
        self.assertTrue(b.confirm(first, (2, 3, 4, 5, 6, 7, 8), 701))
        last = ticket(b, 'with_trait', ('2', '3'))
        self.assertEqual(last['exact_candidate_ids'], ())
        self.assertTrue(b.confirm(last, (), None))
        self.assertTrue(b.snapshot()['phase_plan_complete_offline'])

    def test_prepare_and_lesson_require_new_coordinator_instance(self):
        for stage, when in (
                ('prepare', '09:30'), ('prepare', '13:30'),
                ('lesson', '10:00'), ('lesson', '14:00')):
            b = coordinator(phase=stage, clock=when)
            with_trait = ticket(b, 'with_trait', ('2', '3'))
            self.assertEqual(with_trait['phase'], stage)
            self.assertEqual(with_trait['proposed_effective_upper'], 2)
            self.assertEqual(b.snapshot()['school_time'], when)

    def test_no_duplicate_second_branch_or_unauthorized_student(self):
        b = coordinator()
        first = ticket(b, 'with_trait', ('2', '3', '99', '9'))
        self.assertEqual(first['exact_candidate_ids'], ('2', '3'))
        self.assertTrue(b.confirm(first, (2, 3), 800))
        self.assertIsNone(ticket(b, 'with_trait', ('4',)))
        self.assertEqual(b.snapshot()['with_trait_assigned_ids'], ('2', '3'))

    def test_unverified_ea_counts_never_guess_the_modifier(self):
        b = coordinator()
        self.assertIsNone(ticket(b, 'with_trait', ('2',), players=2))
        self.assertIsNone(b.prepare(
            304563, {}, ('2',), proof(b)))
        self.assertIsNone(ticket(b, 'with_trait', ('2',),
                                 ea_job_counts_verified=False))
        self.assertIsNone(ticket(b, 'with_trait', ('2',),
                                 ea_route_test_results_verified=False))
        self.assertFalse(b.snapshot()['phase_plan_complete_offline'])

    def test_native_job_count_must_agree_with_actual_first_route_assignments(self):
        b = coordinator()
        first = ticket(b, 'with_trait', ('2', '3'))
        self.assertTrue(b.confirm(first, (2, 3), 905))
        self.assertIsNone(ticket(b, 'no_trait', ('4', '5', '6', '7', '8'),
                                 previous_with=0))
        self.assertEqual(b.snapshot()['missing_registered_npc_ids'],
                         ('4', '5', '6', '7', '8'))

    def test_partial_or_duplicate_native_result_fails_permanently_closed(self):
        b = coordinator()
        first = ticket(b, 'with_trait', ('2', '3'))
        self.assertFalse(b.confirm(first, ('2',), 907))
        self.assertTrue(b.snapshot()['blocked'])
        self.assertIsNone(ticket(b, 'no_trait', CLASSES[0]))
        self.assertFalse(b.snapshot()['phase_plan_complete_offline'])

        b2 = coordinator()
        first = ticket(b2, 'with_trait', ('2', '3'))
        self.assertFalse(b2.confirm(first, ('2', '3', '99'), 908))
        self.assertTrue(b2.snapshot()['blocked'])

    def test_failed_native_creation_never_prompts_a_replacement(self):
        b = coordinator()
        first = ticket(b, 'with_trait', ('2', '3'))
        self.assertTrue(b.cancel(first))
        self.assertIsNone(ticket(b, 'with_trait', ('2', '3')))
        self.assertTrue(b.snapshot()['blocked'])

    def test_unknown_school_time_and_cross_save_context_rejected(self):
        for change in (
            {'native_school_phase_origin_verified': False},
            {'school_verified': False},
            {'schedule_guid': 1},
            {'save_slot': 77},
            {'sim_day': 14},
            {'zone_id': 998},
            {'time_window': '12:00'},
            {'original_ea_player_jobs_verified': False},
            {'observed_ea_school_ids': CLASSES[0]},
            {'observed_player_phase_ids': ('1',)},
            {'observed_on_lot_ids': CLASSES[0]},
        ):
            with self.assertRaises(ValueError):
                ClassOneDualRouteBudget(
                    manifest(), 'lesson', school_context(**change))

    def test_different_day_or_school_zone_does_not_activate_routes(self):
        b = coordinator()
        for value in (
            {'sim_day': 15}, {'save_slot': '35'}, {'zone_id': 900},
            {'time_window': '14:00'},
            {'native_school_phase_origin_verified': False},
        ):
            self.assertIsNone(ticket(b, 'with_trait', ('2', '3'), **value))
        self.assertEqual(b.snapshot()['missing_registered_npc_ids'],
                         ('2', '3', '4', '5', '6', '7', '8'))


if __name__ == '__main__':
    unittest.main()
