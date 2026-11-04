"""Offline M141 journal tests: inspect only, archive-safety invariants."""
import json
import tempfile
import unittest
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'/'m141_day_trace'))
from mhs141_day_trace import DayJournal,observe_student,MAX_SAMPLES,OUTPUT

class Position:
    x=42.75
    y=0.0
    z=80.25

class Target:
    id=123
    position=Position()

class Interaction:
    target=Target()

class Queue:
    running=Interaction()

class Sim:
    position=Position()
    posture=None
    queue=Queue()

class Info:
    sim_id=987
    is_selectable=True
    def get_sim_instance(self):
        return Sim()

class Tests(unittest.TestCase):
    def test_read_action_position_without_mutating(self):
        row=observe_student(Info(),2)
        self.assertTrue(row['sim_present'])
        self.assertEqual(row['registered_class'],2)
        self.assertTrue(row['running_action'].endswith('Interaction'))
        self.assertEqual(row['action_target_id'],'123')
        self.assertEqual(row['position']['x'],42.75)
        self.assertFalse(row['queue_details_available'])
        self.assertTrue(row['running_action_completion_unknown'])
    def test_absent_sim_stays_observed_as_absent(self):
        row=observe_student(None,1)
        self.assertEqual(row['diagnostic'],'SIM_INFO_MISSING')
        self.assertFalse(row['sim_present'])
    def test_snapshot_bound_and_save(self):
        groups=(tuple(str(i) for i in range(1,9)),
                tuple(str(i) for i in range(9,17)))
        with tempfile.TemporaryDirectory() as d:
            j=DayJournal(d,'11',groups)
            for i in range(MAX_SAMPLES):
                self.assertTrue(j.append({'hour':9,'minute':i},
                    [{'sim_id':str(k)} for k in range(1,17)]))
            self.assertFalse(j.append({},[{}]*16))
            self.assertTrue(j.flush())
            payload=json.loads(Path(d,OUTPUT).read_text(encoding='utf-8'))
            self.assertEqual(len(payload['snapshots']),MAX_SAMPLES)
            self.assertEqual(payload['game_state_mutations_by_journal'],0)
            self.assertTrue(payload['missing_events_between_samples_possible'])
    def test_bad_registry_fails_closed(self):
        with self.assertRaises(ValueError):
            DayJournal('/tmp','11',(['a']*8,['b']*8))
    def test_invalid_incomplete_sample_not_saved(self):
        with tempfile.TemporaryDirectory() as d:
            j=DayJournal(d,'11',(range(1,9),range(9,17)))
            self.assertFalse(j.append({},[{}]*15))
            self.assertEqual(len(j.samples),0)

if __name__=='__main__':
    unittest.main()
