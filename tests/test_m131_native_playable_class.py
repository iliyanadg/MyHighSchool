"""M131 native playable routing safety / state-only boards."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'/'m131_playable'))
from mhs131_native_playable_class import (
    safe_class_board_candidates,find_playable_entry,queue_playable_class)


class object_HighSchool_Active_Whiteboard:
    def __init__(self,cls):
        self.cls=cls
    def state_value_active(self,state):
        return self.cls==state


class Info:
    is_selectable=True
    def __init__(self,sid):
        self.sim_id=sid
        self.received=[]
    def get_sim_instance(self):
        return Sim(self.received)


class Sim:
    def __init__(self,received):
        self.received=received
        self.queue=type('Queue',(),{'running':None})()
    def push_super_affordance(self,affordance,target,context,picked_object=None):
        self.received.append((affordance,target,context))
        return True


class Home:
    def __init__(self,infos):self.infos=infos
    def sim_info_gen(self):return iter(self.infos)


class TestM131(unittest.TestCase):
    def test_board_state_never_guesses(self):
        boards,status=safe_class_board_candidates(
            [object_HighSchool_Active_Whiteboard(1),
             object_HighSchool_Active_Whiteboard(2)],
            'object_HighSchool_Active_Whiteboard',1,2)
        self.assertEqual(status,'TWO_VALIDATED_EA_CLASS_BOARDS')
        self.assertEqual(len(boards[1]),1)
        self.assertEqual(len(boards[2]),1)

    def test_ambiguous_board_refuses(self):
        boards,status=safe_class_board_candidates(
            [object_HighSchool_Active_Whiteboard(1),
             object_HighSchool_Active_Whiteboard(1)],
            'object_HighSchool_Active_Whiteboard',1,2)
        self.assertEqual(status,'REQUIRE_EXACTLY_ONE_EA_BOARD_PER_CLASS')
        self.assertEqual(boards[2],[])

    def test_missing_state_tuning_refuses(self):
        _,status=safe_class_board_candidates(
            [object_HighSchool_Active_Whiteboard(1)],
            'object_HighSchool_Active_Whiteboard',None,2)
        self.assertEqual(status,'STATE_TUNING_NOT_LOADED')

    def test_playables_respect_saved_class_registration(self):
        groups=(tuple(str(i) for i in range(1,9)),
                tuple(str(i) for i in range(9,17)))
        home=Home([Info(3),Info(10),Info(40)])
        played=find_playable_entry(groups,None,home)
        self.assertEqual([r['sim_id'] for r in played],['3','10'])
        self.assertEqual([r['registered_class'] for r in played],[1,2])

    def test_native_ea_affordance_routed_to_own_board(self):
        one=object_HighSchool_Active_Whiteboard(1)
        two=object_HighSchool_Active_Whiteboard(2)
        infos=[Info(1),Info(9)]
        played=[{'sim_id':str(info.sim_id),
                 'registered_class':1 if info.sim_id==1 else 2,
                 'sim_info':info} for info in infos]
        result=queue_playable_class(
            played,{1:[one],2:[two]},object(),lambda sim:'EA_CONTEXT')
        self.assertTrue(result['success'])
        self.assertIs(infos[0].received[0][1],one)
        self.assertIs(infos[1].received[0][1],two)
        self.assertFalse(result['guaranteed_physically_seated'])

    def test_no_board_means_no_partial_player_mutation(self):
        infos=[Info(1),Info(9)]
        played=[{'sim_id':str(info.sim_id),
                 'registered_class':1 if info.sim_id==1 else 2,
                 'sim_info':info} for info in infos]
        result=queue_playable_class(
            played,{1:[object_HighSchool_Active_Whiteboard(1)],
                    2:[]},object(),lambda sim:'CONTEXT')
        self.assertFalse(result['success'])
        self.assertEqual(sum(len(info.received) for info in infos),0)


if __name__=='__main__':
    unittest.main()
