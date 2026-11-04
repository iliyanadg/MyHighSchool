"""M148: dual clock evidence and minimal observation overhead."""
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'/'m148_clock'))
from mhs148_clock_and_sampling import (
    dual_clock_from_services,should_capture_sim_snapshot,
    read_live_clocks)

class Clock(object):
    def __init__(self,ticks,hour,minute):
        self.absolute_ticks=ticks
        self.hour=hour
        self.minute=minute
    def __str__(self):
        return '%02d:%02d' % (self.hour,self.minute)
    def __sub__(self,other):
        return Span((self.absolute_ticks-other.absolute_ticks)/1500.0)

class Span(object):
    def __init__(self,m):self.minutes=m
    def in_minutes(self):return self.minutes

class TimeService(object):
    def __init__(self,t):self.sim_now=t

class GameClockService(object):
    def __init__(self,t):self.now=lambda:t

class Services(object):
    def __init__(self,s,g):self.s=s;self.g=g
    def time_service(self):return self.s
    def game_clock_service(self):return self.g

class ClockTests(unittest.TestCase):
    def test_detect_73_minute_real_difference(self):
        sim=Clock(1500*856,14,16)
        game=Clock(1500*929,15,29)
        got=read_live_clocks(Services(TimeService(sim),GameClockService(game)))
        self.assertEqual(got['lag_minutes'],73)
        self.assertEqual(got['state'],'SIMULATION_MORE_THAN_HOUR_BEHIND')
        self.assertEqual(got['game_time_displayed']['hour'],15)
        self.assertEqual(got['sim_time_processed']['hour'],14)
    def test_aligned_never_invents_difference(self):
        stamp=Clock(1500*605,10,5)
        got=dual_clock_from_services(TimeService(stamp),GameClockService(stamp))
        self.assertEqual(got['state'],'CLOCKS_ALIGNED')
        self.assertEqual(got['lag_minutes'],0)
    def test_missing_clock_fails_closed(self):
        got=dual_clock_from_services(TimeService(None),None)
        self.assertIsNone(got['lag_minutes'])
        self.assertEqual(got['state'],'UNAVAILABLE')
    def test_skip_16_student_full_poll_until_15_sim_minutes(self):
        start=1500*540
        self.assertTrue(should_capture_sim_snapshot(start,None))
        self.assertFalse(should_capture_sim_snapshot(start+1500*3,start))
        self.assertFalse(should_capture_sim_snapshot(start+1500*14,start))
        self.assertTrue(should_capture_sim_snapshot(start+1500*15,start))
        self.assertTrue(should_capture_sim_snapshot(start+1500*3,start,True))
        self.assertFalse(should_capture_sim_snapshot(None,start))
    def test_no_gameplay_mutation(self):
        sim=Clock(1500*500,8,20)
        game=Clock(1500*510,8,30)
        before=(sim.absolute_ticks,game.absolute_ticks)
        report=dual_clock_from_services(TimeService(sim),GameClockService(game))
        self.assertTrue(report['no_game_time_modification'])
        self.assertEqual(before,(sim.absolute_ticks,game.absolute_ticks))

if __name__=='__main__':
    unittest.main()
