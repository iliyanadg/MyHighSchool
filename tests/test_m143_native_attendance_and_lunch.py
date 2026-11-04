"""M143 native EA Attend rescue + attendance proof + NPC lunch invariants.

All tests run offline on Python 3.7 with simple fake native situations.
They do not certify gameplay runtime behavior on Mac.
"""
import ast
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'/'m143_native_attendance'))
from mhs143_native_attendance_policy import (
  find_observed_attend, allowed_direct_attend, classroom_activity,
  job_matches_class, analyze_npc_dining, summarize_registered_attendance,
)

def time(h,m):
    return {'hour':h,'minute':m,'repr':'%02d:%02d'%(h,m)}

class super_HighSchool_Active_Whiteboard_Attend_Art:
    guid64=2411
    @classmethod
    def test(cls,target,context):
        return True
class super_HighSchool_Active_Whiteboard_Attend_ComputerScience:
    guid64=2412
    @classmethod
    def test(cls,target,context):
        return True
class stand_Passive:pass
class Queue:
    def __init__(self,run):self.running=run
class Sim:
    def __init__(self,run):self.queue=Queue(run)
class Info:
    def __init__(self,run):self.sim=Sim(run)
    def get_sim_instance(self):return self.sim

class M143(unittest.TestCase):
    def test_requires_native_job_and_original_request(self):
        self.assertEqual(allowed_direct_attend(
          time(10,7),2,'id',False,True,False,'stand_Passive',2),
          (False,'EA_NATIVE_JOB_NOT_PRESENT'))
        self.assertEqual(allowed_direct_attend(
          time(10,7),2,'id',True,False,False,'stand_Passive',2),
          (False,'NO_NATIVE_CLASS_START_REQUEST'))
        self.assertEqual(allowed_direct_attend(
          time(10,7),2,'id',True,True,True,'stand_Passive',2),
          (False,'ONE_DIRECT_ATTEMPT_PER_LESSON'))
        self.assertEqual(allowed_direct_attend(
          time(10,7),2,'id',True,True,False,'stand_Passive',1),
          (False,'WRONG_CLASS_TARGET_REFUSED'))
    def test_only_at_start_of_both_lessons(self):
        self.assertTrue(allowed_direct_attend(time(10,7),2,'7',
             True,True,False,'stand_Passive',2)[0])
        self.assertTrue(allowed_direct_attend(time(14,8),2,'7',
             True,True,False,'stand_Passive',2)[0])
        for h,m in [(9,59),(10,6),(10,25),(11,0),(13,59),(14,25)]:
            self.assertFalse(allowed_direct_attend(time(h,m),2,'7',
               True,True,False,'stand_Passive',2)[0])
    def test_never_interrupt_real_class_or_needs(self):
        for name in ['super_HighSchool_Active_Whiteboard_Attend_Art',
                     'super_HighSchool_Active_UseBook_Class',
                     'mixer_HighSchool_Active_Listen_Generic_Art',
                     'toilet-use-sitting-stall','Shower_Take']:
            self.assertFalse(allowed_direct_attend(
              time(10,10),2,'7',True,True,False,name,2)[0],name)
    def test_only_observed_real_native_ea_attend(self):
        one={'sim_info':Info(super_HighSchool_Active_Whiteboard_Attend_Art())}
        two={'sim_info':Info(stand_Passive())}
        obj,why=find_observed_attend([one,two])
        self.assertIs(obj,super_HighSchool_Active_Whiteboard_Attend_Art)
        self.assertEqual(why,'OBSERVED_ACTUAL_EA_CLASS_AFFORDANCE')
        empty,why=find_observed_attend([two])
        self.assertIsNone(empty)
        self.assertEqual(why,'NO_UNAMBIGUOUS_OBSERVED_NATIVE_ATTEND')
        both,why=find_observed_attend([one,{'sim_info':Info(
            super_HighSchool_Active_Whiteboard_Attend_ComputerScience())}])
        self.assertIsNone(both)
    def test_only_exact_job_for_registered_class(self):
        self.assertTrue(job_matches_class(2,[{
             'situation_guid':304567,'job_guid':280777}]))
        self.assertFalse(job_matches_class(1,[{
             'situation_guid':304567,'job_guid':280777}]))
        self.assertFalse(job_matches_class(2,[{
             'situation_guid':304565,'job_guid':277919}]))
    def test_npc_dining_never_controls_playable(self):
        samples=[{'clock':time(12,5),'students':[
             {'sim_id':'a','selectable':False,
              'running_action':'sims4.tuning.instances.Food_Eat_Active',
              'posture':'sims4.tuning.instances.posture_Stand',
              'position':{'x':10,'y':0,'z':20}},
             {'sim_id':'b','selectable':False,
              'running_action':'Food_Eat_Passive','posture':'posture_Sit'},
             {'sim_id':'c','selectable':True,
              'running_action':'Food_Eat_Active','posture':'posture_Sit'}]}]
        a=analyze_npc_dining(samples,['a','b'])
        self.assertEqual(a['npc_with_eating_samples'],2)
        self.assertEqual(a['npc_with_sitting_eating_samples'],1)
        self.assertEqual(a['npc_with_only_standing_eating_samples'],1)
        self.assertTrue(a['no_player_meals_automated'])
        self.assertEqual(a['npc_interactions_modified'],0)
    def test_class_seat_needs_correct_board_in_same_floor(self):
        anchors={1:{'id':'board1','position':{'x':10,'y':0,'z':30}},
                 2:{'id':'board2','position':{'x':45,'y':0,'z':30}}}
        snapshots=[{'clock':time(10,25),'students':[
          {'sim_id':'1','registered_class':1,
            'running_action':'mixer_HighSchool_Active_Listen_Generic_Art',
            'position':{'x':11,'y':0,'z':29},'posture':'posture_Sit'},
          {'sim_id':'2','registered_class':2,
            'running_action':'stand_Passive',
            'position':{'x':11,'y':0,'z':29},'posture':'posture_Sit'}]}]
        a=summarize_registered_attendance(snapshots,[('1',),('2',)],anchors)
        self.assertTrue(a['anchors_validated'])
        self.assertEqual(a['students']['1']['morning'][
                         'observed_seated_near_registered_board'],1)
        self.assertEqual(a['students']['2']['morning'][
                         'observed_seated_near_wrong_board'],1)
        self.assertEqual(a['students']['1']['morning'][
                         'actual_class_action_samples'],1)
        self.assertEqual(a['students']['1']['afternoon']['snapshots'],0)
    def test_main_controller_has_passive_and_native_only(self):
        ctrl=(ROOT/'src'/'m143_native_attendance'/
              'mhs143_classroom_controller.py').read_text(encoding='utf-8')
        ast.parse(ctrl)
        for piece in ("mhs143.arm","mhs143.monitor","mhs143.report",
           "_m143_direct_attend(runtime)","source.test(target,context)",
           "'NATIVE_EA_TEST_REFUSED'","runtime.m143_direct_attempted.add(key)",
           "classroom_activity","_m143_write_full_report(_RUNTIME)",
           "MHS_M143_PRESENZE_DUE_AULE.json",
           "MHS_M143_REPORT_COMPLETO.json",
           "native_original_ea_class_entry",
           "npc_lunch_posture",
           "physical_classroom_attendance"):
            # Name in tests is "subject" not "source".
            if piece=="source.test(target,context)":
                piece="subject.test(target,context)"
            self.assertIn(piece,ctrl)

if __name__=='__main__':
    unittest.main()
