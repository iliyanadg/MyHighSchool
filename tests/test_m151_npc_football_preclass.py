"""M151: EA-native football NPC request; no bypass, mutation or extra guests."""
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'/'classroom_control'))
from mhs151_npc_school_priority import (
    eligible_football_preclass,native_prep_role)
from mhs151_npc_football_bridge import attempt_football_npcs


class Football:
    __name__='throwFootballMixers_Idle_Y'


class Sim:
    def __init__(self):
        self.pushes=[]
        self.cancellations=[]
    def push_super_affordance(self,affordance,target,context,picked_object=None):
        self.pushes.append((affordance,target,context,picked_object))
        return True


class Info:
    is_selectable=False
    def __init__(self,sim):self.sim=sim
    def get_sim_instance(self):return self.sim


class Manager:
    def __init__(self,ids):self.infos=ids
    def get(self,key):return self.infos.get(key)


class Runtime:
    active=True
    def __init__(self):
        self.lesson_classes=(('1','2'),('3','4'))
        self.prep_created={1:100,2:200}
        self.m151_npc_attempts={}
        self.m151_npc_accepted=set()
        self.m151_npc_reports=[]


class Board:
    def __init__(self,klass):self.klass=klass


class Affordance:
    guid64=297779
    def __init__(self,test_allowed=True):
        self.test_allowed=test_allowed
        self.test_calls=[]
    def test(self,board,context):
        self.test_calls.append((board,context))
        return self.test_allowed


class Tests(unittest.TestCase):
    def test_policy_only_registered_correct_npc_with_matching_ea_job(self):
        kwargs=dict(clock={'hour':9,'minute':40},klass=1,registered=True,
            selectable=False,native_role=True,board_verified=True,
            queue_available=True,running_name='throwFootballMixers_Idle_Y',
            queued_names=(),attempts=0)
        self.assertTrue(eligible_football_preclass(**kwargs)[0])
        for update in ({'clock':{'hour':10,'minute':0}},
                       {'registered':False},{'selectable':True},
                       {'klass':3},{'native_role':False},
                       {'board_verified':False},{'queue_available':False},
                       {'attempts':2},
                       {'running_name':'super_HighSchool_Active_AttendClass_NPC'},
                       {'queued_names':('super_HighSchool_Active_UseBook_Class',)},
                       {'queued_names':('Social_HighSchool_Active_Detention',)}):
            self.assertFalse(eligible_football_preclass(
                **dict(kwargs,**update))[0])

    def test_known_ea_preparation_roles_not_random_class(self):
        self.assertTrue(native_prep_role(1,[{
            'situation_guid':293815,'job_guid':277919}]))
        self.assertTrue(native_prep_role(2,[{
            'situation_guid':297774,'job_guid':277919}]))
        self.assertFalse(native_prep_role(1,[{
            'situation_guid':297774,'job_guid':277919}]))
        self.assertFalse(native_prep_role(2,[{
            'situation_guid':277733,'job_guid':277894}]))

    def run_bridge(self,game_allowed=True,job=True):
        runtime=Runtime()
        one=Sim()
        two=Sim()
        mgr=Manager({1:Info(one),3:Info(two)})
        affordance=Affordance(game_allowed)
        boards={1:[Board(1)],2:[Board(2)]}
        jobs=lambda sim,sit: {'available':True,'jobs':[{
            'situation_guid':293815 if sim is one else 297774,
            'job_guid':277919}] if job else []}
        reader=lambda sim: {'available':True,
                            'running':Football(),
                            'queued_names':()}
        context=lambda sim: ('native_context',sim)
        accepted=attempt_football_npcs(runtime,{'hour':9,'minute':40},
            mgr,object(),affordance,boards,reader,jobs,context)
        return accepted,runtime,one,two,affordance,boards

    def test_two_npcs_from_distinct_classes_native_test_and_push(self):
        accepted,runtime,one,two,affordance,boards=self.run_bridge()
        self.assertTrue(accepted)
        self.assertEqual(len(one.pushes),1)
        self.assertEqual(len(two.pushes),1)
        self.assertIs(one.pushes[0][1],boards[1][0])
        self.assertIs(two.pushes[0][1],boards[2][0])
        self.assertEqual(runtime.m151_npc_accepted,{'1','3'})
        self.assertTrue(all(x['native_ea_test_passed']
                            for x in runtime.m151_npc_reports))
        self.assertTrue(all(x['lesson_completion_unverified']
                            for x in runtime.m151_npc_reports))
        self.assertEqual(one.cancellations+two.cancellations,[])

    def test_native_ea_refusal_never_pushed_or_fabricated(self):
        accepted,runtime,one,two,affordance,boards=self.run_bridge(False)
        self.assertFalse(accepted)
        self.assertEqual(len(one.pushes)+len(two.pushes),0)
        self.assertEqual(runtime.m151_npc_attempts,{'1':1,'3':1})
        self.assertTrue(all(not x['native_ea_test_passed']
                            for x in runtime.m151_npc_reports))

    def test_missing_class_job_and_no_valid_board_never_push(self):
        accepted,runtime,one,two,affordance,_=self.run_bridge(True,False)
        self.assertFalse(accepted)
        self.assertFalse(runtime.m151_npc_attempts)
        self.assertFalse(affordance.test_calls)
        r=Runtime()
        accepted=attempt_football_npcs(r,{'hour':9,'minute':40},
            Manager({}),object(),Affordance(),{1:[],2:[]},
            lambda _:None,lambda *_:None,lambda _:None)
        self.assertFalse(accepted)

    def test_same_day_no_repeat_after_success(self):
        accepted,runtime,one,two,affordance,boards=self.run_bridge()
        again=attempt_football_npcs(runtime,{'hour':9,'minute':43},
            Manager({1:Info(one),3:Info(two)}),object(),affordance,boards,
            lambda _: {'available':True,'running':Football(),
                       'queued_names':()},
            lambda sim,sit: {'available':True,'jobs':[{
                'situation_guid':293815 if sim is one else 297774,
                'job_guid':277919}]},lambda sim:('ctx',sim))
        self.assertFalse(again)
        self.assertEqual(len(one.pushes),1)
        self.assertEqual(len(two.pushes),1)


if __name__=='__main__':
    unittest.main()
