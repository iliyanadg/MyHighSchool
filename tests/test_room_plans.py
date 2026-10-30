"""Offline tests for original v1.6 classroom-planning modules.

Neither these tests nor these modules make actual EA Sims attend a real class.
"""
from pathlib import Path
import importlib.util
import unittest

ROOT = Path(__file__).resolve().parents[1] / 'src' / 'legacy_v1_6'


def module_from_file(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / (name + '.py'))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


playable = module_from_file('mhs_playable_rooms')
seats = module_from_file('mhs_seat_planner')


class RoomTests(unittest.TestCase):
    def test_playable_student_counts_towards_max_eight(self):
        npc = {str(i): 1 for i in range(1, 9)}
        with self.assertRaises(playable.PlayablePlanError):
            playable.reserve_playable({}, npc, '9', 1, ['9'])

    def test_playable_student_can_be_assigned_to_room_three_in_plan(self):
        plan = playable.reserve_playable({}, {}, '123', 3, ['123'])
        self.assertEqual(plan, {'123': 3})

    def test_room_three_does_not_falsely_claim_ea_support(self):
        with self.assertRaises(playable.PlayablePlanError):
            playable.apply_original_ea_marker({'123': 3}, {}, None, None, None)

    def test_cannot_assign_npc_duplicate_as_playable(self):
        with self.assertRaises(playable.PlayablePlanError):
            playable.reserve_playable({}, {'123': 1}, '123', 2, ['123'])

    def test_seat_plan_keeps_unregistered_occupants_visible(self):
        plan = seats.seat_plan({'1': 1, '2': 1}, {1: ['1', '3', '4', '5', '6', '7', '8', '9']})
        self.assertEqual(plan[1]['status'], 'NEEDS_SAFE_REPLACEMENT')
        self.assertEqual(plan[1]['missing'], ['2'])
        self.assertEqual(plan[1]['free_seats'], 0)
        self.assertEqual(len(plan[1]['unregistered_occupants']), 7)

    def test_seat_plan_rejects_over_eight_enrolled(self):
        with self.assertRaises(seats.SeatPlanError):
            seats.seat_plan({str(i): 1 for i in range(1, 10)})


if __name__ == '__main__':
    unittest.main()
