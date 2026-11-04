"""Read every EA bucket without invoking queue mutations or head selection."""
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src/classroom_control'))
from mhs_queue_readback import queue_snapshot


class EAQueue(object):
    def __init__(self,running,buckets):self.running=running;self.buckets=buckets
    def __iter__(self):
        if self.running is not None:yield self.running
        for bucket in self.buckets:
            for action in bucket:
                if action is not self.running:yield action
    def get_head(self):raise AssertionError('mutating head API must not run')
    def cancel_all(self):raise AssertionError('never cancel gameplay')


class QueueTests(unittest.TestCase):
    def test_phone_mixer_reports_active_lesson_parent_separately(self):
        lesson=type('super_HighSchool_Active_Whiteboard_Attend_Art',(),{})()
        mixer=type('mixer_HighSchool_Active_UsePhone',(),{})()
        mixer.super_interaction=lesson
        result=queue_snapshot(SimpleNamespace(queue=EAQueue(mixer,[])))
        self.assertTrue(result['available'])
        self.assertEqual(result['queued_names'],())
        self.assertEqual(result['active_parent_names'],
                         ('super_HighSchool_Active_Whiteboard_Attend_Art',))

    def test_reads_all_buckets_without_queue_list_or_cancels(self):
        running=type('stand_Passive',(),{})()
        lesson=type('super_HighSchool_Active_Whiteboard_Class_Start',(),{})()
        detention=type('super_HighSchool_Active_Detention',(),{})()
        queue=EAQueue(running,[[running,lesson],[detention]])
        result=queue_snapshot(SimpleNamespace(queue=queue))
        self.assertTrue(result['available'])
        self.assertEqual(result['waiting'],(lesson,detention))
        self.assertEqual(result['running_name'],'stand_Passive')
        self.assertIn('super_HighSchool_Active_Detention',result['queued_names'])

    def test_empty_real_queue_is_known_empty_and_unknown_queue_is_not(self):
        self.assertEqual(queue_snapshot(SimpleNamespace(queue=EAQueue(None,[])))['queued_names'],())
        result=queue_snapshot(SimpleNamespace(queue=SimpleNamespace(_queue=[])))
        self.assertFalse(result['available'])
        self.assertNotIn('queued_names',result)

    def test_interrupted_or_unbounded_iterator_fails_closed(self):
        class Broken(EAQueue):
            def __iter__(self):raise RuntimeError('changed while reading')
        self.assertFalse(queue_snapshot(SimpleNamespace(queue=Broken(None,[])))['available'])
        many=EAQueue(None,[[object() for _ in range(70)]])
        self.assertFalse(queue_snapshot(SimpleNamespace(queue=many))['available'])

    def test_duplicate_objects_do_not_create_duplicate_pending_requests(self):
        action=object()
        result=queue_snapshot(SimpleNamespace(queue=EAQueue(None,[[action],[action]])))
        self.assertEqual(result['waiting'],(action,))


if __name__=='__main__':unittest.main()
