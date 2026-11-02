"""M108 original EA 6->8 Base situations count proposal, offline Python 3.7."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src' / 'm108_native_roster'))

from tests.test_m108_native_invitation import (
    session as prepared_session, session, EAList, CONTEXT,
    BASE_SITUATION,
)
from mhs108_native_base_count import (
    REQUIRED_LIVE_GATES, propose_native_base_count,
    install_offline_only,
)

MAIN = 277657
FROM_VENUE = 279958

def verified_context(adjustment=0, **changes):
    c = dict(
        native_weekly_school_origin_verified=True,
        school_verified=True,
        ea_schedule_not_started=True,
        schedule_guid=MAIN,
        save_slot='11',
        sim_day=12,
        school_zone='777',
        ea_original_playable_adjustment=adjustment,
        ea_playable_adjustment_verified=True)
    c.update(changes)
    return c


def all_gates():
    # ONLY a synthetic fixture; no live EA runtime has proven these!
    return {gate: True for gate in REQUIRED_LIVE_GATES}


def fake_ea_schedule(original=(6, 6)):
    class WeeklyScheduleDay(object):
        calls = 0

        @classmethod
        def get_long_term_situation_count(cls, data, resolver):
            cls.calls += 1
            return original

    class HighSchoolMain(WeeklyScheduleDay):
        guid64 = MAIN

    class HighSchoolFromVenue(WeeklyScheduleDay):
        guid64 = FROM_VENUE

    class OtherDay(WeeklyScheduleDay):
        guid64 = 12345

    class StudentSituation(object):
        guid64 = BASE_SITUATION

    class StaffSituation(object):
        guid64 = 298096

    class Data(object):
        def __init__(self, situation):
            self.situation = situation

    return (WeeklyScheduleDay, HighSchoolMain, HighSchoolFromVenue,
            OtherDay, Data(StudentSituation()), Data(StaffSituation()))


class EightBaseCountTests(unittest.TestCase):

    def test_eight_base_two_classes_five_core_prebooked(self):
        s = prepared_session()
        self.assertEqual(len(s.manifest['all_16']), 16)
        self.assertEqual(len(s.manifest['playable']), 3)
        self.assertEqual(len(s._local_core_holds), 5)
        self.assertEqual(len(s.manifest['base_ids']), 8)
        self.assertEqual(
            propose_native_base_count((6, 6), MAIN, BASE_SITUATION,
                                      s, verified_context()), (8, 8))
        self.assertEqual(
            propose_native_base_count((6, 6), FROM_VENUE,
                                      BASE_SITUATION, s,
                                      verified_context(schedule_guid=FROM_VENUE)),
            (8, 8))
        self.assertEqual(
            propose_native_base_count((6, 6), FROM_VENUE,
                                      BASE_SITUATION, s,
                                      verified_context(schedule_guid=MAIN)),
            (6, 6))

    def test_verified_playable_modifier_must_match_actual_original_count(self):
        s = session()
        self.assertEqual(
            propose_native_base_count((3, 3), MAIN, BASE_SITUATION,
                                      s, verified_context(adjustment=3)), (8, 8))
        self.assertEqual(
            propose_native_base_count((3, 3), MAIN, BASE_SITUATION,
                                      s, verified_context(adjustment=0)), (3, 3))
        self.assertEqual(
            propose_native_base_count((6, 6), MAIN, BASE_SITUATION,
                                      s, verified_context(adjustment=3)), (6, 6))
        self.assertEqual(
            propose_native_base_count((4, 4), MAIN, BASE_SITUATION,
                                      s, verified_context(adjustment=2)), (8, 8))
        self.assertEqual(
            propose_native_base_count((4, 6), MAIN, BASE_SITUATION,
                                      s, verified_context(adjustment=2)), (4, 6))

    def test_base_count_never_changes_without_early_role_holds(self):
        s = session(arm=False)
        self.assertEqual(
            propose_native_base_count((6, 6), MAIN, BASE_SITUATION,
                                      s, verified_context()), (6, 6))
        self.assertIsNone(
            install_offline_only(fake_ea_schedule()[0], s,
                                 verified_context, all_gates()))

    def test_count_not_issued_if_ea_schedule_already_started(self):
        s = session()
        for delta in (
            {'ea_schedule_not_started': False},
            {'native_weekly_school_origin_verified': False},
            {'school_verified': False},
            {'schedule_guid': 987},
            {'save_slot': '22'},
            {'sim_day': 13},
            {'school_zone': '901'},
            {'ea_original_playable_adjustment': -1},
            {'ea_original_playable_adjustment': 4},
            {'ea_original_playable_adjustment': True},
            {'ea_playable_adjustment_verified': False},
        ):
            self.assertEqual(
                propose_native_base_count((6, 6), MAIN, BASE_SITUATION,
                                          s, verified_context(**delta)),
                (6, 6), msg=str(delta))

    def test_incomplete_or_unrecognized_counts_remain_vanilla(self):
        s = session()
        for original in ((0, 8), (8, 8), (7, 7), (6, 7),
                         (6,), (6, 6, 6), (True, 6),
                         [6, 6], None, 6, ('6', '6')):
            self.assertEqual(
                propose_native_base_count(original, MAIN, BASE_SITUATION,
                                          s, verified_context()), original)
        self.assertEqual(
            propose_native_base_count((6, 6), MAIN, 298096,
                                      s, verified_context()), (6, 6))
        self.assertEqual(
            propose_native_base_count((6, 6), 12345, BASE_SITUATION,
                                      s, verified_context()), (6, 6))

    def test_count_not_repeated_after_first_ea_base_invitation(self):
        s = session()
        token, _ = s.preview(BASE_SITUATION, EAList(), CONTEXT)
        self.assertEqual(token, 'base:5')
        self.assertTrue(s.acknowledge_created(token, 901))
        self.assertEqual(
            propose_native_base_count((6, 6), MAIN, BASE_SITUATION,
                                      s, verified_context()), (6, 6))

    def test_classmethod_called_once_and_other_jobs_unchanged(self):
        Day, Main, Venue, Other, base, staff = fake_ea_schedule()
        s = session()
        undo = install_offline_only(Day, s, lambda: verified_context(),
                                    all_gates())
        self.assertTrue(callable(undo))
        self.assertEqual(Main.get_long_term_situation_count(base, None),
                         (8, 8))
        # Context Main cannot authorize the FromVenue schedule by accident.
        self.assertEqual(Venue.get_long_term_situation_count(base, None),
                         (6, 6))
        self.assertEqual(Other.get_long_term_situation_count(base, None),
                         (6, 6))
        self.assertEqual(Main.get_long_term_situation_count(staff, None),
                         (6, 6))
        self.assertEqual(Main.calls, 2)
        self.assertEqual(Venue.calls, 1)
        self.assertEqual(Other.calls, 1)
        self.assertTrue(undo())
        self.assertFalse(undo())
        self.assertEqual(Main.get_long_term_situation_count(base, None),
                         (6, 6))

        # A fresh, separately verified EA FromVenue context may use 8.
        undo_venue = install_offline_only(
            Day, s, lambda: verified_context(schedule_guid=FROM_VENUE),
            all_gates())
        self.assertTrue(callable(undo_venue))
        self.assertEqual(Venue.get_long_term_situation_count(base, None),
                         (8, 8))
        self.assertEqual(Main.get_long_term_situation_count(base, None),
                         (6, 6))
        self.assertTrue(undo_venue())

    def test_missing_gate_or_wrong_owner_cannot_install(self):
        for missing in REQUIRED_LIVE_GATES:
            Day = fake_ea_schedule()[0]
            proof = all_gates()
            proof[missing] = False
            self.assertIsNone(
                install_offline_only(Day, session(), verified_context, proof))

        class BadDay(object):
            def get_long_term_situation_count(self, data, resolver):
                return (6, 6)
        self.assertIsNone(
            install_offline_only(BadDay, session(),
                                 verified_context, all_gates()))

    def test_existing_m96_or_m105_hook_stops_second_controller(self):
        for marker in ('_mhs96_count_hook', '_mhs105_schedule_audit',
                       '_mhs108_count_hook'):
            Day, _, _, _, _, _ = fake_ea_schedule()
            original = Day.__dict__['get_long_term_situation_count']
            fn = original.__func__
            setattr(fn, marker, True)
            try:
                self.assertIsNone(
                    install_offline_only(Day, session(),
                                         verified_context, all_gates()))
            finally:
                delattr(fn, marker)

    def test_context_provider_error_fails_to_original_once(self):
        Day, Main, _, _, base, _ = fake_ea_schedule()
        def invalid():
            raise RuntimeError('Cannot verify EA schedule')
        undo = install_offline_only(Day, session(), invalid, all_gates())
        self.assertTrue(callable(undo))
        self.assertEqual(Main.get_long_term_situation_count(base, None),
                         (6, 6))
        self.assertEqual(Main.calls, 1)
        self.assertTrue(undo())

    def test_no_claim_that_eight_sims_are_spawned(self):
        s = session()
        self.assertEqual(
            propose_native_base_count((6, 6), MAIN, BASE_SITUATION,
                                      s, verified_context()), (8, 8))
        self.assertFalse(s.snapshot()['attendance_verified'])
        self.assertFalse(s.snapshot()['ea_job_assignment_verified'])
        self.assertFalse(s.snapshot()['class_8_plus_8_verified'])


if __name__ == '__main__':
    unittest.main()
