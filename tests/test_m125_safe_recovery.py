"""M125 safe one-time EA lesson mirror recovery, offline tests."""
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'/'m125_recovery'))
sys.path.insert(0,str(ROOT/'src'/'m122_classrooms'))
from mhs125_safe_recovery import inspect_candidate,recover_one


class Job(object):
    def __init__(self,guid):self.guid64=guid


def _cancel_mirror(self,finish,reason):
    self.calls+=1


MirrorPractice=type('mirror_ResearchDebateSkill_Practice',(object,),{
    '__module__':'sims4.tuning.instances',
    'calls':0,'cancel':_cancel_mirror,
})


def _forbid_cancel(self,*args):
    raise AssertionError('MUST NOT TOUCH INTERACTION')


WritingLesson=type('mixer_HighSchool_Active_WriteOnBook',(object,),{
    '__module__':'sims4.tuning.instances',
    'cancel':_forbid_cancel,
})


class Sim(object):
    def __init__(self,action):self.queue=type('Queue',(),{'running':action})()


class Info(object):
    age='teen'
    species='human'
    is_selectable=False


class Situation(object):
    guid64=304565
    def get_current_job_for_sim(self,sim):return Job(277919)


class Manager(object):
    def get_situations_sim_is_in(self,sim):return (Situation(),)


class Tests(unittest.TestCase):
    def test_only_exact_known_mirror_with_correct_job(self):
        act=MirrorPractice()
        self.assertEqual(inspect_candidate(
            '1',1,Info(),Sim(act),Manager(),'teen','human',set())[:2],
            (True,'ELIGIBLE_OFF_TASK_MIRROR'))

    def test_cancel_once_and_does_not_claim_classroom_seating(self):
        act=MirrorPractice()
        tried=set()
        success,msg=recover_one(
            '1',1,Info(),Sim(act),Manager(),'teen','human',
            tried,'SITUATIONS')
        self.assertTrue(success)
        self.assertEqual(act.calls,1)
        self.assertIn('NOT_YET_VERIFIED',msg)
        success,msg=recover_one(
            '1',1,Info(),Sim(act),Manager(),'teen','human',
            tried,'SITUATIONS')
        self.assertFalse(success)
        self.assertEqual(msg,'ALREADY_ATTEMPTED')
        self.assertEqual(act.calls,1)

    def test_does_not_interrupt_school_lesson_action(self):
        tried=set()
        self.assertFalse(recover_one(
            '1',1,Info(),Sim(WritingLesson()),Manager(),
            'teen','human',tried,'SITUATIONS')[0])
        self.assertFalse(tried)

    def test_playable_sim_protected(self):
        info=Info()
        info.is_selectable=True
        act=MirrorPractice()
        success,reason=recover_one(
            '1',1,info,Sim(act),Manager(),
            'teen','human',set(),'SITUATIONS')
        self.assertFalse(success)
        self.assertEqual(reason,'PLAYABLE_PROTECTED')
        self.assertEqual(act.calls,0)

    def test_wrong_class_not_modified(self):
        act=MirrorPractice()
        success,reason=recover_one(
            '1',2,Info(),Sim(act),Manager(),
            'teen','human',set(),'SITUATIONS')
        self.assertFalse(success)
        self.assertEqual(reason,'NATIVE_LESSON_JOB_UNVERIFIED')
        self.assertEqual(act.calls,0)

    def test_situation_api_missing_preserves_action(self):
        act=MirrorPractice()
        success,_=recover_one(
            '1',1,Info(),Sim(act),object(),
            'teen','human',set(),'SITUATIONS')
        self.assertFalse(success)
        self.assertEqual(act.calls,0)

    def test_other_non_school_interaction_not_preempted(self):
        Toilet=type('super_Toilet_Use',(object,),{
            '__module__':'sims4.tuning.instances',
            'cancel':_forbid_cancel,
        })
        success,_=recover_one(
            '1',1,Info(),Sim(Toilet()),Manager(),
            'teen','human',set(),'SITUATIONS')
        self.assertFalse(success)


if __name__=='__main__':
    unittest.main()
