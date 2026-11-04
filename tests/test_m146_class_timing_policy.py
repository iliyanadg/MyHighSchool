"""M146 regression fixtures use the exact EA prep job and M145d observations."""
import unittest
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'/'m146_integrated'))
from mhs146_class_timing_policy import (
    can_early_request,preparation_period,validate_anchors,truant_evidence)
GOOD=[{'situation_guid':297774,'job_guid':277919,
       'is_preparation':True,'is_lesson':False}]
class Pos:
    x=395;y=151;z=515
class Board:
    def __init__(self,num):self.id=num;self.position=Pos()
class Cases(unittest.TestCase):
    def test_early_only_class2_with_native_role(self):
        for clock in ({'hour':9,'minute':37},{'hour':13,'minute':37}):
            self.assertTrue(can_early_request(2,GOOD,clock,'stand_Passive',False)[0])
            self.assertFalse(can_early_request(1,GOOD,clock,'stand_Passive',False)[0])
            self.assertFalse(can_early_request(2,GOOD,clock,'stand_Passive',True)[0])
    def test_no_guessing_jobs_or_time(self):
        self.assertFalse(can_early_request(2,[],{'hour':9,'minute':37},'',False)[0])
        self.assertFalse(can_early_request(2,[{'situation_guid':297774,'job_guid':277919}],
                                           {'hour':9,'minute':37},'',False)[0])
        self.assertFalse(can_early_request(2,GOOD,{'hour':10,'minute':15},'',False)[0])
        self.assertFalse(can_early_request(2,GOOD,{'hour':14,'minute':59},'',False)[0])
        self.assertFalse(can_early_request(2,GOOD,{'hour':15,'minute':0},'',False)[0])
    def test_protect_existing_class_actions_and_discipline(self):
        for action in ('super_HighSchool_Active_Whiteboard_Attend_Art',
                       'super_HighSchool_Active_CreateBook_Class',
                       'mixer_HighSchool_Active_WriteOnBook',
                       'super_Social_HighSchool_Active_NPC_Principal_CatchTruant',
                       'toilet-use-sitting'):
            ok,why=can_early_request(
                2,GOOD,{'hour':9,'minute':37},action,False)
            self.assertFalse(ok)
            self.assertEqual(why,'EXISTING_OR_PROTECTED_ACTION')
    def test_board_anchors_are_native_and_noninterchangeable(self):
        anchors,why=validate_anchors({1:[Board(11)],2:[Board(12)]})
        self.assertEqual(why,'TWO_DISTINCT_EA_CLASSROOM_ANCHORS')
        self.assertEqual(anchors[2]['id'],'12')
        self.assertIsNone(validate_anchors({1:[Board(11)],2:[Board(11)]})[0])
        self.assertIsNone(validate_anchors({1:[Board(11)],2:[]})[0])
    def test_truancy_incident_observed_not_silently_replaced(self):
        samples=[{'clock':{'hour':10,'minute':25,'repr':'10:25'},
                  'students':[{'sim_id':'255124','registered_class':2,
                               'selectable':False,
                               'running_action':'super_Social_HighSchool_Active_NPC_Principal_CatchTruant'}]}]
        data=truant_evidence(samples)
        self.assertEqual(data['students']['255124']['class'],2)
        self.assertTrue(data['npc_disruptions_not_overridden_by_mhs'])
        self.assertTrue(data['observed_incident_not_proof_of_official_detention'])
if __name__=='__main__':
    unittest.main()
