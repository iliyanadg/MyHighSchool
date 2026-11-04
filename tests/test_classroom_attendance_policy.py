"""Actual state sequences around the missed-first-request attendance defect."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src' / 'classroom_control'))
from mhs_attendance_policy import (
    LessonRequestLedger, classify_attendance, protected_gameplay,
)


def clock(hour=10, minute=0):
    return {'hour': hour, 'minute': minute}


class RequestSequenceTests(unittest.TestCase):
    def setUp(self):
        self.ledger = LessonRequestLedger()

    def ready(self, **overrides):
        values = dict(period='morning', sid='91001', registered_class=2,
                      clock=clock(), has_native_job=True, correct_board=True,
                      instanced=True, running_action='', queued_actions=(),
                      native_phase_created=True, context_verified=True)
        values.update(overrides)
        return self.ledger.decision(**values)

    def test_delayed_instantiation_does_not_permanently_exclude_student(self):
        self.assertEqual(self.ready(instanced=False), (False, 'NOT_INSTANCED'))
        self.assertEqual(self.ledger.state('morning', '91001')['attempts'], 0)
        self.assertTrue(self.ready(clock=clock(minute=3))[0])
        self.ledger.record_result('morning', '91001', clock(minute=3),
                                  True, 'EA_ACCEPTED', True)
        self.assertTrue(self.ledger.state('morning', '91001')['accepted'])

    def test_initial_native_refusal_can_receive_bounded_later_request(self):
        self.assertTrue(self.ready()[0])
        self.ledger.record_result('morning', '91001', clock(),
                                  False, 'EA_REJECTED', False)
        self.assertFalse(self.ledger.state('morning', '91001')['accepted'])
        self.assertFalse(self.ready(clock=clock(minute=2))[0])
        self.assertTrue(self.ready(clock=clock(minute=3))[0])
        self.ledger.record_result('morning', '91001', clock(minute=3),
                                  True, 'EA_ACCEPTED', True)
        self.assertEqual(self.ledger.state('morning', '91001')['attempts'], 2)

    def test_accepted_then_disappeared_may_retry_only_with_clear_queue(self):
        self.ledger.record_result('morning', '91001', clock(),
                                  True, 'EA_ACCEPTED', True)
        self.assertFalse(self.ready(clock=clock(minute=3), queued_actions=(
            'super_HighSchool_Active_Whiteboard_Class_Start',))[0])
        self.assertTrue(self.ready(clock=clock(minute=3))[0])
        self.assertTrue(self.ledger.observe('morning', '91001',
            'super_HighSchool_Active_Whiteboard_Attend_Math'))
        self.assertFalse(self.ready(clock=clock(minute=6))[0])

    def test_no_request_loop_and_separate_afternoon_budget(self):
        for minute in (0, 3, 6):
            self.assertTrue(self.ready(clock=clock(minute=minute))[0])
            self.ledger.record_result('morning', '91001', clock(minute=minute),
                                      False, 'EA_REJECTED', False)
        self.assertEqual(self.ready(clock=clock(minute=9)),
                         (False, 'REQUEST_BUDGET_EXHAUSTED'))
        self.assertTrue(self.ready(period='afternoon', clock=clock(14, 0))[0])
        self.assertTrue(self.ready(sid='91002', clock=clock(minute=9))[0])

    def test_all_native_context_requirements_fail_closed(self):
        for key, value in (
                ('context_verified', False), ('has_native_job', False),
                ('correct_board', False), ('native_phase_created', False),
                ('clock', None), ('queued_actions', None),
                ('queued_actions', (object(),)), ('running_action', None),
                ('registered_class', 3), ('sid', '01'), ('sid', True)):
            with self.subTest(field=key, value=repr(value)):
                self.assertFalse(self.ready(**{key: value})[0])

    def test_discipline_and_needs_protected_running_and_queued(self):
        actions = (
            'super_HighSchool_Active_Detention',
            'Social_HighSchool_Active_Principal_CatchTruant',
            'TryToAvoidDetention', 'toilet_UseSitting', 'Sleep', 'Shower',
            'Food_Eat', 'generic_consume_food', 'si_MarketStalls_OrderFood',
            'super_HighSchool_Active_UseBook_Class',
        )
        for name in actions:
            with self.subTest(action=name):
                self.assertTrue(protected_gameplay(name))
                self.assertFalse(self.ready(running_action=name)[0])
                self.assertFalse(self.ready(queued_actions=(name,))[0])
        self.assertEqual(self.ledger.state('morning', '91001')['attempts'], 0)

    def test_preserves_native_times_and_requires_native_test_after_decision(self):
        for hour, minute in ((9, 59), (10, 25), (11, 0), (13, 59), (15, 0)):
            self.assertFalse(self.ready(clock=clock(hour, minute))[0])
        self.assertTrue(self.ready(clock=clock(9, 35), phase='preparation')[0])
        self.assertFalse(self.ready(clock=clock(10, 0), phase='preparation')[0])
        self.assertEqual(self.ready()[1], 'ORIGINAL_EA_INTERACTION_TEST_REQUIRED')
        with self.assertRaises(ValueError):
            self.ledger.record_result('morning', '91001', clock(),
                                      True, 'INCORRECT_BYPASS', False)
        self.assertEqual(self.ledger.state('morning', '91001')['attempts'], 0)

    def test_backward_clock_requires_new_day_state_not_silent_retry(self):
        self.ledger.record_result('morning', '91001', clock(minute=6),
                                  False, 'EA_REJECTED', False)
        self.assertEqual(self.ready(clock=clock(minute=3)),
                         (False, 'SCHOOL_DAY_RESET_REQUIRED'))
        before = self.ledger.state('morning', '91001')
        with self.assertRaises(ValueError):
            self.ledger.record_result('morning', '91001', clock(minute=3),
                                      False, 'INVALID_CLOCK', False)
        self.assertEqual(self.ledger.state('morning', '91001'), before)


class AttendanceFactTests(unittest.TestCase):
    def test_stages_do_not_collapse_invitation_into_presence(self):
        cases = (
            ({'invited': False}, 'NOT_INVITED'),
            ({'invited': True}, 'INVITED_ADMISSION_UNKNOWN'),
            ({'invited': True, 'has_native_job': False}, 'INVITED_NOT_ADMITTED'),
            ({'has_native_job': True, 'present': False}, 'ADMITTED_NOT_INSTANTIATED'),
            ({'present': True, 'has_native_job': False}, 'PRESENT_WITHOUT_CLASS_JOB'),
            ({'request_accepted': False}, 'REQUEST_REFUSED'),
            ({'request_accepted': True}, 'REQUEST_ACCEPTED_NOT_OBSERVED'),
            ({'running_class': True}, 'CLASS_ACTION_OBSERVED'),
            ({'running_class': True, 'seated_in_class': True},
             'CLASS_ACTION_AND_PHYSICAL_SEAT_OBSERVED'),
            ({'seated_in_class': True}, 'PHYSICAL_SEAT_WITHOUT_CLASS_ACTION'),
        )
        for facts, expected in cases:
            with self.subTest(stage=expected):
                result = classify_attendance(True, **facts)
                self.assertEqual(result['stage'], expected)
                self.assertIsNone(result['ea_completion_observed'])
                self.assertFalse(result['completion_known'])

    def test_unknown_invitation_is_not_fabricated_absence_or_success(self):
        result = classify_attendance(True)
        self.assertEqual(result['stage'], 'REGISTERED_INVITATION_UNKNOWN')
        self.assertIsNone(result['invited'])
        self.assertIsNone(result['present'])
        self.assertTrue(result['completion_not_inferred_from_queue_or_seat'])

    def test_only_independent_ea_evidence_provides_completion(self):
        result = classify_attendance(True, request_accepted=True,
                                     running_class=True, seated_in_class=True)
        self.assertFalse(result['completion_known'])
        result = classify_attendance(True, ea_completion_observed=True)
        self.assertEqual(result['stage'], 'EA_COMPLETION_OBSERVED')
        self.assertTrue(result['completion_known'])


if __name__ == '__main__':
    unittest.main()
