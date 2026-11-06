"""M131 native playable routing safety / state-only boards."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'/'m131_playable'))
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'/'classroom_control'))
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
        self.queue=type('Queue',(),{'running':None,
            '__iter__':lambda self:iter(()) if self.running is None else iter((self.running,))})()
    def push_super_affordance(self,affordance,target,context,picked_object=None):
        self.received.append((affordance,target,context))
        return True


class Home:
    def __init__(self,infos):self.infos=infos
    def sim_info_gen(self):return iter(self.infos)


class TestM131(unittest.TestCase):
    def test_initial_request_does_not_interrupt_mixer_parent_lesson(self):
        info=Info(9);sim=Sim(info.received)
        parent=type('super_HighSchool_Active_Whiteboard_Attend_Art',(),{})()
        mixer=type('mixer_HighSchool_Active_UsePhone',(),{})()
        mixer.super_interaction=parent
        sim.queue.running=mixer
        info.get_sim_instance=lambda:sim
        result=queue_playable_class(
            ({'sim_id':'9','registered_class':2,'sim_info':info},),
            {2:[object_HighSchool_Active_Whiteboard(2)]},object(),lambda _:'EA_CONTEXT')
        self.assertEqual(result['results'][0]['reason'],'EXISTING_PROTECTED_ACTION')
        self.assertEqual(info.received,[])

    def test_initial_request_refuses_unknown_queue_without_pushing(self):
        info=Info(9);sim=Sim(info.received)
        sim.queue=object();info.get_sim_instance=lambda:sim
        result=queue_playable_class(
            ({'sim_id':'9','registered_class':2,'sim_info':info},),
            {2:[object_HighSchool_Active_Whiteboard(2)]},object(),lambda _:'EA_CONTEXT')
        self.assertEqual(result['results'][0]['reason'],'EA_QUEUE_UNAVAILABLE')
        self.assertEqual(info.received,[])

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

    def test_do_not_duplicate_early_subject_started_before_10(self):
        # M145d source shows playables already perform a native subject
        # Whiteboard_Attend_Art at 09:37. M146 preclass may make Class2
        # run at 09:37 too; the scheduled 10:00 push must not override it.
        for action in ('super_HighSchool_Active_Whiteboard_Attend_Art',
                       'super_HighSchool_Active_UseBook_Class',
                       'super_HighSchool_Active_CreateBook_Class',
                       'mixer_HighSchool_Active_WriteOnBook'):
            info=Info(9)
            sim=Sim(info.received)
            sim.queue.running=type(action,(),{})()
            info.get_sim_instance=lambda :sim
            target=object_HighSchool_Active_Whiteboard(2)
            result=queue_playable_class(
                ({'sim_id':'9','registered_class':2,'sim_info':info},),
                {2:[target]},object(),lambda _:'EA_CONTEXT')
            self.assertFalse(result['success'])
            self.assertEqual(result['results'][0]['reason'],
                             'EXISTING_PROTECTED_ACTION')
            self.assertEqual(info.received,[])

    def test_m149_manual_subject_queued_never_replaced_by_auto(self):
        # The player has clicked "Frequenta lezione" on Class2 board.
        # A queued EA Attend takes precedence over another MHS push.
        info=Info(9)
        sim=Sim(info.received)
        action=type('super_HighSchool_Active_Whiteboard_Attend_Art',
                    (),{})()
        class Queue:
            running=None
            def __iter__(self):
                return iter((action,))
        sim.queue=Queue()
        info.get_sim_instance=lambda:sim
        target=object_HighSchool_Active_Whiteboard(2)
        outcome=queue_playable_class(
            ({'sim_id':'9','registered_class':2,'sim_info':info},),
            {2:[target]},object(),lambda _:'EA_CONTEXT')
        self.assertEqual(outcome['results'][0]['reason'],
                         'EXISTING_PROTECTED_ACTION')
        self.assertEqual(info.received,[])

    def test_m149_ea_manual_go_to_own_board_preserves_choice(self):
        for klass,sid in ((1,1),(2,9)):
            info=Info(sid)
            sim=Sim(info.received)
            target=object_HighSchool_Active_Whiteboard(klass)
            action=type('super_HighSchool_Active_Ping_GoToObject',
                        (),{'target':target})()
            class Queue:
                running=None
                def __iter__(self):
                    return iter((action,))
            sim.queue=Queue()
            info.get_sim_instance=lambda sim=sim:sim
            result=queue_playable_class(
                ({'sim_id':str(sid),'registered_class':klass,
                  'sim_info':info},),
                {klass:[target]},object(),lambda _:'EA_CONTEXT')
            self.assertEqual(result['results'][0]['reason'],
                             'EXISTING_NATIVE_BOARD_NAVIGATION')
            self.assertEqual(info.received,[])

    def test_m149_zerbu_board_navigation_not_replaced(self):
        info=Info(1)
        sim=Sim(info.received)
        board=object_HighSchool_Active_Whiteboard(1)
        action=type('Zerbu_GTS5_WhiteboardGotoPing',
                    (),{'picked_object':board})()
        class Queue:
            running=action
            def __iter__(self):
                return iter((action,))
        sim.queue=Queue()
        info.get_sim_instance=lambda:sim
        result=queue_playable_class(
            ({'sim_id':'1','registered_class':1,'sim_info':info},),
            {1:[board]},object(),lambda _:'EA_CONTEXT')
        self.assertEqual(result['results'][0]['reason'],
                         'EXISTING_NATIVE_BOARD_NAVIGATION')
        self.assertEqual(info.received,[])

    def test_m149_unrelated_board_ping_does_not_suppress_auto(self):
        info=Info(9)
        sim=Sim(info.received)
        correct=object_HighSchool_Active_Whiteboard(2)
        unrelated=object_HighSchool_Active_Whiteboard(1)
        action=type('super_HighSchool_Active_Ping_GoToObject',
                    (),{'target':unrelated})()
        class Queue:
            running=None
            def __iter__(self):
                return iter((action,))
        sim.queue=Queue()
        info.get_sim_instance=lambda:sim
        result=queue_playable_class(
            ({'sim_id':'9','registered_class':2,'sim_info':info},),
            {2:[correct]},object(),lambda _:'EA_CONTEXT')
        self.assertTrue(result['results'][0]['queued'])
        self.assertIs(info.received[0][1],correct)

    def test_m149_targetless_generic_ping_not_assumed_manual_board(self):
        info=Info(9)
        sim=Sim(info.received)
        action=type('Zerbu_GTS5_WhiteboardGotoPing',
                    (),{'target':None})()
        class Queue:
            running=None
            def __iter__(self):
                return iter((action,))
        sim.queue=Queue()
        info.get_sim_instance=lambda:sim
        board=object_HighSchool_Active_Whiteboard(2)
        result=queue_playable_class(
            ({'sim_id':'9','registered_class':2,'sim_info':info},),
            {2:[board]},object(),lambda _:'EA_CONTEXT')
        self.assertTrue(result['results'][0]['queued'])

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
