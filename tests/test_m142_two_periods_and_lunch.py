"""M142 per-period school retry and passive lunch tests."""
import ast
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'/'m142_two_periods'))
from mhs142_school_policy import (
    period_for_clock, can_roll_to_afternoon,
    class_retry_decision, summarize_npc_lunch)

def clock(h,m):
    return {'hour':h,'minute':m, 'repr':'%02d:%02d'%(h,m)}

class PolicyTests(unittest.TestCase):
    def test_afternoon_reset_only_once_after_1325(self):
        self.assertFalse(can_roll_to_afternoon(clock(10,0),None,{1,2},False))
        self.assertTrue(can_roll_to_afternoon(clock(13,30),None,{1,2},False))
        self.assertFalse(can_roll_to_afternoon(clock(13,30),None,{1,2},True))
        self.assertFalse(can_roll_to_afternoon(clock(13,30),999,{1,2},False))
        self.assertEqual(period_for_clock(clock(13,30)),'afternoon')
    def test_second_lesson_native_job_required_for_retry(self):
        row={'sim_id':'7','registered_class':2}
        job={'situation_jobs':[{'situation_guid':304567,'job_guid':280777}]}
        self.assertEqual(class_retry_decision(
            clock(14,5),'afternoon',row,job,True,False,'stand_Passive')[0],True)
        self.assertEqual(class_retry_decision(
            clock(14,5),'afternoon',row,{'situation_jobs':[]},
            True,False,'stand_Passive')[1],'NATIVE_CLASS_JOB_MISSING')
        self.assertEqual(class_retry_decision(
            clock(14,5),'afternoon',row,job,False,False,'stand_Passive')[1],
            'NATIVE_CREATE_NOT_CONFIRMED')
    def test_single_retry_per_period_only_inside_lesson(self):
        row={'sim_id':'7','registered_class':2}
        job={'situation_jobs':[{'situation_guid':304567,'job_guid':280777}]}
        self.assertFalse(class_retry_decision(
            clock(11,5),'morning',row,job,True,False,'stand_Passive')[0])
        self.assertFalse(class_retry_decision(
            clock(14,5),'afternoon',row,job,True,True,'stand_Passive')[0])
        self.assertFalse(class_retry_decision(
            clock(14,5),'afternoon',row,job,True,False,
            'super_HighSchool_Active_UseBook_Class')[0])
        self.assertFalse(class_retry_decision(
            clock(14,5),'afternoon',row,job,True,False,
            'toilet-use-sitting-stall')[0])
        self.assertTrue(class_retry_decision(
            clock(10,7),'morning',row,job,True,False,'WorkoutMachine_Workout')[0])
    def test_lunch_npc_only_and_no_game_mutations(self):
        times=[clock(11,5),clock(11,8),clock(11,11)]
        samples=[]
        for tick in times:
            samples.append({'clock':tick,'students':[
                {'sim_id':'1','selectable':False,
                 'running_action':'sims4.tuning.instances.si_MarketStalls_OrderFood',
                 'action_target_id':42},
                {'sim_id':'2','selectable':True,
                 'running_action':'si_MarketStalls_OrderFood',
                 'action_target_id':42},
                {'sim_id':'3','selectable':False,
                 'running_action':'generic_consume_food',
                 'action_target_id':99}]})
        result=summarize_npc_lunch(samples,['1','2','3'])
        self.assertEqual(result['npc_students_in_trace'],2)
        self.assertEqual(result['students']['1']['longest_sampled_order_minutes_estimate'],9)
        self.assertTrue(result['students']['3']['food_eaten_observed'])
        self.assertNotIn('2',result['students'])
        self.assertEqual(result['game_mutations'],0)
    def test_controller_contains_both_period_and_single_retry(self):
        src=(ROOT/'src'/'m142_two_periods'/'mhs142_classroom_controller.py').read_text(encoding='utf-8')
        ast.parse(src)
        for marker in (
                '_m142_roll_period_if_due(self,',
                "runtime.lesson_attempted.clear()",
                "runtime.prep_attempted.clear()",
                "runtime.m140_auto_attempted.clear()",
                "_m142_retry_playables(runtime)",
                "runtime.m142_retry_attempted.add((runtime.m142_period,sid))",
                "self.m142_auto_accepted.add(",
                "class_retry_decision(",
                "mhs142.mensa",
                "mhs142.periodi"):
            self.assertIn(marker,src)

if __name__=='__main__':
    unittest.main()
