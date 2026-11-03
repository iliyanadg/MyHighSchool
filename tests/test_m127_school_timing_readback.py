"""M127 strict read-only source tests for timing and target observations."""
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'/'m127_timing'))
sys.path.insert(0,str(ROOT/'src'/'m124_behavior'))
sys.path.insert(0,str(ROOT/'src'/'m122_classrooms'))
sys.path.insert(0,str(ROOT/'src'/'m126_early'))
sys.path.insert(0,str(ROOT/'src'/'m123_class_repair'))
from mhs127_school_timing_readback import (
    game_clock,inspect_action_target,timed_roster_snapshot)
from tests.test_m124_lesson_action_readback import C1,C2,Infos,Manager


class Clock(object):
    def hour(self):return 9
    def minute(self):return 55
    def absolute_ticks(self):return 123456
    def __str__(self):return '09:55'


class TimeService(object):
    sim_now=Clock()


class ReadbackTests(unittest.TestCase):
    def test_in_game_hour_minute_and_ticks_are_observed(self):
        c=game_clock(TimeService())
        self.assertEqual(c['hour'],9)
        self.assertEqual(c['minute'],55)
        self.assertEqual(c['absolute_ticks'],123456)

    def test_unavailable_clock_does_not_change_game(self):
        self.assertIn('CLOCK_UNAVAILABLE',game_clock(None)['repr'])

    def test_running_target_is_not_seating_proof(self):
        sim=Infos().get(1)
        row=inspect_action_target(sim)
        self.assertEqual(row['state'],'RUNNING')
        self.assertFalse(row['physically_seated_verified'])

    def test_snapshot_covers_both_real_ea_class_rosters(self):
        r=timed_roster_snapshot((C1,C2),Infos(),Manager(),
            TimeService(),'TEEN','HUMAN')
        self.assertEqual(len(r['students']),16)
        self.assertEqual(r['school_job_count'],16)
        self.assertEqual(r['clock']['minute'],55)
        self.assertFalse(r['game_actions_modified'])
        self.assertFalse(r['auto_seating_claimed'])

    def test_none_sim_is_not_claimed_seated(self):
        r=inspect_action_target(None)
        self.assertEqual(r['state'],'NOT_INSTANCED')


if __name__=='__main__':
    unittest.main()
