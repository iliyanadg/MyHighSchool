"""M140 original EA lesson event one-time routing safety tests."""
import unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'/'m140_auto_lesson'))
from mhs140_native_lesson_entry import launch_once_at_native_lesson
class Tests(unittest.TestCase):
    def setUp(self):
        self.boards={1:[object()],2:[object()]}
        self.rows=[{'sim_id':'a','registered_class':1},
                   {'sim_id':'b','registered_class':2},
                   {'sim_id':'c','registered_class':2}]
        self.calls=[]
        self.seen=set()
    def queue(self,rows,boards,aff,ctx):
        self.calls.append([x['sim_id'] for x in rows])
        return {'reason':'EA_PUSH_ATTEMPT_COMPLETE',
                'results':[{'sim_id':x['sim_id'],'queued':True,'reason':'EA_ACCEPTED'} for x in rows]}
    def execute(self,klass,boards=None,aff=None):
        return launch_once_at_native_lesson(klass,self.seen,self.rows,
            self.boards if boards is None else boards,
            object() if aff is None else aff,
            lambda sim:sim,self.queue)
    def test_event_only_enqueues_own_class(self):
        self.assertEqual(len(self.execute(1)['results']),1)
        self.assertEqual(len(self.execute(2)['results']),2)
        self.assertEqual(self.calls,[['a'],['b','c']])
    def test_does_not_duplicate_for_repeated_native_event(self):
        self.execute(2)
        out=self.execute(2)
        self.assertFalse(out['attempted'])
        self.assertEqual(len(self.calls),1)
    def test_never_routes_to_unvalidated_boards(self):
        out=self.execute(1,boards={1:[object()]})
        self.assertFalse(out['attempted'])
        self.assertFalse(self.seen)
        self.assertFalse(self.calls)
    def test_rejects_unknown_class(self):
        self.assertFalse(self.execute(3)['attempted'])
        self.assertFalse(self.calls)
    def test_queue_failure_is_observed_not_retried(self):
        def fail(*args):raise RuntimeError('REJECT')
        out=launch_once_at_native_lesson(1,self.seen,self.rows,self.boards,
                                        object(),lambda sim:sim,fail)
        self.assertEqual(out['reason'],'QUEUE_RuntimeError')
        self.assertEqual(self.seen,{1})
if __name__=='__main__':unittest.main()
