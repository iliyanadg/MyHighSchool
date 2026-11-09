"""Save-independent native roster partitions and daily lifecycle decisions."""
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src' / 'classroom_control'))
from mhs_school_session import (
    CORE_JOBS, SIM_TICKS_PER_DAY, SessionPolicyError, plan_roster,
    school_day_key, session_decision,
)


class RosterPlanTests(unittest.TestCase):
    def state(self, played_count, start=1000):
        enrolled = tuple(str(start + i) for i in range(16))
        groups = (enrolled[:8], enrolled[8:])
        played = enrolled[:played_count]
        pinned = dict(zip(CORE_JOBS, enrolled[played_count:played_count + 5]))
        infos = {int(sid): SimpleNamespace(
            age='TEEN', species='HUMAN', is_selectable=sid in played)
            for sid in enrolled}
        manager = SimpleNamespace(get=infos.get)
        return groups, played, pinned, manager, infos

    def test_native_base_count_comes_from_current_save_not_three_players(self):
        for start in (1000, 700000):
            for count in (0, 1, 2, 3, 4, 8, 11):
                with self.subTest(start=start, played=count):
                    groups, played, pinned, mgr, _ = self.state(count, start)
                    result = plan_roster(groups, played, pinned, mgr,
                                         'TEEN', 'HUMAN')
                    self.assertEqual(result['played'], played)
                    self.assertEqual(len(result['base']), 16 - 5 - count)
                    self.assertEqual(result['pinned'], pinned)
                    all_ids = result['played'] + result['base'] + tuple(
                        result['pinned'].values())
                    self.assertEqual(len(all_ids), len(set(all_ids)))
                    self.assertEqual(set(all_ids), set(groups[0] + groups[1]))

    def test_more_than_eleven_playables_refuses_without_replacing_anyone(self):
        groups, played, pinned, mgr, _ = self.state(12)
        original = (groups, played, dict(pinned))
        with self.assertRaisesRegex(SessionPolicyError,
                                    'INSUFFICIENT_NPC_FOR_NATIVE_CORE'):
            plan_roster(groups, played, pinned, mgr, 'TEEN', 'HUMAN')
        self.assertEqual((groups, played, pinned), original)

    def test_unregistered_household_teen_is_reported_not_auto_enrolled(self):
        groups, played, pinned, mgr, _ = self.state(2)
        result = plan_roster(groups, played + ('999999',), pinned, mgr,
                             'TEEN', 'HUMAN')
        self.assertEqual(result['played'], played)
        self.assertEqual(result['unregistered_played'], ('999999',))
        self.assertNotIn('999999', result['enrolled'])

    def test_core_appointments_must_be_manual_distinct_registered_npcs(self):
        groups, played, pinned, mgr, _ = self.state(2)
        missing = dict(pinned)
        del missing[CORE_JOBS[0]]
        duplicate = dict(pinned)
        duplicate[CORE_JOBS[1]] = duplicate[CORE_JOBS[0]]
        playable = dict(pinned)
        playable[CORE_JOBS[0]] = played[0]
        outside = dict(pinned)
        outside[CORE_JOBS[0]] = '999999'
        for appointments in ({}, missing, duplicate, playable, outside):
            with self.subTest(appointments=appointments):
                with self.assertRaises(SessionPolicyError):
                    plan_roster(groups, played, appointments, mgr,
                                'TEEN', 'HUMAN')

    def test_missing_aged_up_and_nonhuman_students_fail_closed(self):
        for field, value in (('age', 'YOUNGADULT'), ('species', 'DOG'),
                             ('missing', None)):
            groups, played, pinned, mgr, infos = self.state(1)
            sid = int(groups[1][-1])
            if field == 'missing':
                del infos[sid]
            else:
                setattr(infos[sid], field, value)
            with self.subTest(field=field):
                with self.assertRaises(SessionPolicyError):
                    plan_roster(groups, played, pinned, mgr, 'TEEN', 'HUMAN')

    def test_transient_selectability_never_replaces_registered_students(self):
        groups, played, pinned, mgr, infos = self.state(3)
        original_ids = groups[0] + groups[1]
        # EA can expose None for off-lot NPCs and True for Sims in other
        # played households. Only CURRENT active-household membership counts.
        for sid in original_ids:
            infos[int(sid)].is_selectable = None
        infos[int(groups[0][4])].is_selectable = True
        delattr(infos[int(groups[1][5])], 'is_selectable')
        for day in range(3):
            with self.subTest(day=day):
                result = plan_roster(groups, played, pinned, mgr,
                                     'TEEN', 'HUMAN')
                self.assertEqual(result['played'], played)
                self.assertEqual(set(result['base'] + tuple(
                    result['pinned'].values()) + result['played']),
                    set(original_ids))
                self.assertEqual(len(result['base']), 8)
                self.assertEqual(len(set(result['enrolled'])), 16)
                self.assertEqual(result['groups'], groups)

    def test_two_complete_distinct_classes_are_required(self):
        groups, played, pinned, mgr, _ = self.state(1)
        for malformed in ((groups[0][:-1], groups[1]),
                          (groups[0], groups[0]), (groups[0],)):
            with self.subTest(groups=malformed):
                with self.assertRaises(SessionPolicyError):
                    plan_roster(malformed, played, pinned, mgr,
                                'TEEN', 'HUMAN')


class SchoolSessionTests(unittest.TestCase):
    def test_day_key_uses_absolute_simulation_ticks_and_save_slot(self):
        self.assertEqual(school_day_key('24', 0), ('24', 0))
        self.assertEqual(school_day_key('24', SIM_TICKS_PER_DAY - 1),
                         ('24', 0))
        self.assertEqual(school_day_key('24', SIM_TICKS_PER_DAY), ('24', 1))
        for invalid in (None, 1.0, -1, True):
            with self.subTest(ticks=invalid):
                with self.assertRaises(SessionPolicyError):
                    school_day_key('24', invalid)
        for invalid in ('unknown', '', '01', 0, True, 0xFFFFFFFE):
            with self.subTest(slot=invalid):
                with self.assertRaises(SessionPolicyError):
                    school_day_key(invalid, 0)

    def test_same_roster_resets_the_second_day_even_at_same_school(self):
        first = school_day_key('24', SIM_TICKS_PER_DAY * 8 + 10)
        second = school_day_key('24', SIM_TICKS_PER_DAY * 9 + 10)
        self.assertEqual(session_decision(first, first, True, True),
                         ('KEEP', 'ACTIVE_SCHOOL_DAY_PRESERVED'))
        self.assertEqual(session_decision(first, second, True, True),
                         ('RESET', 'NEW_SCHOOL_DAY'))

    def test_midday_transfer_is_deferred_but_next_day_refreshes(self):
        key = ('24', 8)
        self.assertEqual(session_decision(key, key, True, True,
                                          roster_changed=True),
                         ('DEFER', 'ROSTER_CHANGES_APPLY_NEXT_SCHOOL_DAY'))
        self.assertEqual(session_decision(key, ('24', 9), True, True,
                                          roster_changed=True),
                         ('RESET', 'NEW_SCHOOL_DAY'))
        self.assertEqual(session_decision(key, key, True, False,
                                          roster_changed=True),
                         ('RESET', 'HOME_ROSTER_CHANGED'))

    def test_disable_stops_without_deleting_a_saved_roster(self):
        key = ('24', 8)
        self.assertEqual(session_decision(key, key, False, True),
                         ('STOP', 'MANAGEMENT_DISABLED'))
        self.assertEqual(key, ('24', 8))

    def test_save_change_cannot_reuse_old_invitation_state(self):
        self.assertEqual(session_decision(('24', 8), ('25', 8), True, False),
                         ('RESET', 'SAVE_SLOT_CHANGED'))
        self.assertEqual(session_decision(('24', 8), ('25', 8), True, True),
                         ('STOP', 'SAVE_CHANGED_DURING_SCHOOL'))

    def test_home_load_zone_change_and_school_reload_are_explicit(self):
        key = ('24', 8)
        self.assertEqual(session_decision(None, key, True, False),
                         ('START', 'VERIFIED_HOME_ACTIVATION'))
        self.assertEqual(session_decision(None, key, True, True),
                         ('BLOCK', 'INITIAL_ACTIVATION_REQUIRES_HOME'))
        self.assertEqual(session_decision(key, key, True, False, reload=True),
                         ('RESET', 'HOME_RELOAD'))
        self.assertEqual(session_decision(key, key, True, False,
                                          zone_changed=True),
                         ('RESET', 'HOME_ZONE_CHANGED'))
        self.assertEqual(session_decision(key, key, True, True, reload=True),
                         ('STOP', 'SCHOOL_RELOAD_REQUIRES_HOME'))

    def test_unknown_time_or_invalid_context_never_starts_runtime(self):
        self.assertEqual(session_decision(None, None, True, False)[0], 'BLOCK')
        self.assertEqual(session_decision(None, ('24', 8), 'yes', False)[0],
                         'BLOCK')


if __name__ == '__main__':
    unittest.main()
