"""M144 conservatively reuse real original EA NPC Class2 attendance pathway.

This is an offline Python3.7 test of policy and code wiring, not an EA runtime
execution test. We never change EA tuning or fabricate an EA affordance ID.
"""
import ast
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'/'m144_class2_native'))
from mhs144_class2_policy import (
    classify_phase, valid_job_for_phase, can_attempt_class2,
    source_from_registered_class2_npcs,is_real_class2_npc_source,
)
class Board:
    def __init__(self,id):self.id=id
class super_HighSchool_Active_AttendClass_NPC:
    guid64=297779
    @classmethod
    def test(cls,target,context):
        return True
    def __init__(self,target):self.target=target
class WrongClassTuning:
    guid64=297779
    @classmethod
    def test(cls,target,context):return True
    def __init__(self,target):self.target=target
class Queue:
    def __init__(self,running):self.running=running
class Sim:
    def __init__(self,running):self.queue=Queue(running)
class Info:
    def __init__(self,running):self.sim=Sim(running)
    def get_sim_instance(self):return self.sim

class M144Tests(unittest.TestCase):
    def test_windows_match_real_ea_preparation_and_10_14(self):
        for h in (9,13):
            self.assertEqual(classify_phase({'hour':h,'minute':39}),
                             'preparation')
            self.assertIsNone(classify_phase({'hour':h,'minute':34}))
        for h in (10,14):
            self.assertEqual(classify_phase({'hour':h,'minute':9}),'lesson')
            self.assertIsNone(classify_phase({'hour':h,'minute':25}))
        self.assertIsNone(classify_phase({'hour':12,'minute':0}))
    def test_exact_ea_jobs_are_required(self):
        self.assertTrue(valid_job_for_phase([{
            'situation_guid':297774,'job_guid':277919}],'preparation'))
        self.assertTrue(valid_job_for_phase([{
            'situation_guid':304567,'job_guid':280777}],'lesson'))
        self.assertFalse(valid_job_for_phase([{
            'situation_guid':304565,'job_guid':277919}],'lesson'))
        self.assertFalse(valid_job_for_phase([], 'lesson'))
    def test_only_playable_class2_and_correct_board(self):
        row={'sim_id':'p2','registered_class':2,'sim_info':object()}
        job=[{'situation_guid':304567,'job_guid':280777}]
        self.assertTrue(can_attempt_class2(
            {'hour':10,'minute':9},row,job,False,set(),'stand_Passive')[0])
        self.assertFalse(can_attempt_class2(
            {'hour':10,'minute':9},dict(row,registered_class=1),
            job,False,set(),'stand_Passive')[0])
        self.assertFalse(can_attempt_class2(
            {'hour':10,'minute':9},row,job,False,set(),'stand_Passive',
            board_is_class2=False)[0])
    def test_never_push_again_or_during_critical_action(self):
        row={'sim_id':'p2','registered_class':2,'sim_info':object()}
        job=[{'situation_guid':304567,'job_guid':280777}]
        self.assertFalse(can_attempt_class2(
            {'hour':10,'minute':9},row,job,False,{('lesson','p2')},
            'stand_Passive')[0])
        self.assertFalse(can_attempt_class2(
            {'hour':10,'minute':9},row,job,False,set(),
            'super_HighSchool_Active_AttendClass_NPC')[0])
        self.assertFalse(can_attempt_class2(
            {'hour':10,'minute':9},row,job,False,set(),
            'Toilet_Use_Seat')[0])
    def test_exact_live_npc_target_must_be_same_board2(self):
        native=super_HighSchool_Active_AttendClass_NPC(Board(200))
        rows=[{'sim_info':Info(native),'selectable':False,
               'registered_class':2}]
        source,msg=source_from_registered_class2_npcs(rows,200)
        self.assertIs(source,super_HighSchool_Active_AttendClass_NPC)
        self.assertFalse(is_real_class2_npc_source(native,native.target,100))
        self.assertIsNone(source_from_registered_class2_npcs(rows,100)[0])
        self.assertIsNone(source_from_registered_class2_npcs([
            {'sim_info':Info(native),'selectable':True,
             'registered_class':2}],200)[0])
        self.assertIsNone(source_from_registered_class2_npcs([
            {'sim_info':Info(WrongClassTuning(Board(200))),
             'selectable':False,'registered_class':2}],200)[0])
    def test_controller_does_not_use_original_wrong_class1_fallback(self):
        ctrl=(ROOT/'src'/'m144_class2_native'/
              'mhs144_classroom_controller.py').read_text(encoding='utf-8')
        ast.parse(ctrl)
        for token in (
            'mhs144.arm','mhs144.monitor','mhs144.report',
            '_m144_class2_original_native_route(runtime)',
            'source_from_registered_class2_npcs(',
            'native.test(expected,ctx)',
            'runtime.m144_prep_queued.clear()',
            'runtime.m144_attempted.add(mark)',
            'runtime.m144_reports.append(result)',
            'real_class2_npc_path_attempts',
            'MHS_M144_REPORT_COMPLETO.json'):
            self.assertIn(token,ctrl)
        # M143 wrong Class1 action remains as an inactive helper only.
        self.assertNotIn('_m143_direct_attend(runtime)\\n',
                         ctrl.split('def sample(handle):')[1].split(
                         'handle=alarms.add_alarm')[0])
        self.assertIn('no_nonclass_player_actions_automated',ctrl)
    def test_native_refusal_keeps_original_ea_test_and_no_tuning_patch(self):
        ctrl=(ROOT/'src'/'m144_class2_native'/
              'mhs144_classroom_controller.py').read_text(encoding='utf-8')
        body=ctrl.split('def _m144_class2_original_native_route(runtime):')[1]
        self.assertIn("result['native_test_passed']=bool(native_test)",body)
        self.assertIn("result['reason']='EA_CLASS2_NATIVE_TEST_REFUSED'",body)
        self.assertIn('if not native_test:',body)
        self.assertNotIn('class1state=True',body)
        self.assertNotIn('.test_globals=',body)
        self.assertNotIn('target.set_state(',body)

if __name__=='__main__':unittest.main()
