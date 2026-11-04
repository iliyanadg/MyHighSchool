"""Behavioral contracts: correct board, native refusals and exact fallback."""
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src/classroom_control'))
sys.path.insert(0,str(ROOT/'src/m139_general_whiteboards'))
sys.path.insert(0,str(ROOT/'src/m145_class2_playable'))
from mhs_scoped_classroom import ScopedTestList, registered_board_context, install_native_board_guard
from mhs139_ea_zerbu_adapter import install_known_whiteboard_adapter
from mhs145_subject_picker_patch import install_subject_picker, SUBJECT_IDS
from tests import test_m139_ea_zerbu_adapter as picker_fixture
from tests import test_m145_subject_picker_patch as subject_fixture


class Result(object):
    def __init__(self,passed,reason=''):
        self.passed=passed
        self.reason=reason
    def __bool__(self):return self.passed


class TestList(tuple):
    def run_tests(self,resolver,skip_safe_tests=False,search_for_tooltip=False):
        resolver.calls.append((self,skip_safe_tests,search_for_tooltip))
        return resolver.native_result


class CompoundTestList(TestList):pass


class Board(object):
    def __init__(self,klass):self.klass=klass;self.id=100+klass
    def state_value_active(self,state):return self.klass==state


class Resolver(object):
    def __init__(self,sid='501',board=None,passed=True):
        self.actor=SimpleNamespace(sim_id=sid)
        self.board=board
        self.native_result=Result(passed,'native sentinel')
        self.calls=[]
    def get_participant(self,kind):
        return self.actor if kind=='ACTOR' else self.board


class ScopeTests(unittest.TestCase):
    def setUp(self):
        self.school=True
        self.membership={'501':1,'502':2}
        self.old=TestList(('original',))
        self.amended=TestList(('amended',))
        self.scope=lambda resolver:registered_board_context(
            resolver,'ACTOR','OBJECT',self.membership,1,2) if self.school else None
        self.failure=lambda reason:Result(False,reason)
        self.wrapped=ScopedTestList(self.old,self.amended,self.scope,self.failure)

    def test_wrong_npc_board_is_rejected_before_native_evaluation(self):
        resolver=Resolver('502',Board(1))
        self.assertFalse(self.wrapped.run_tests(resolver))
        self.assertEqual(resolver.calls,[])
        resolver.board=Board(2)
        self.assertIs(self.wrapped.run_tests(resolver),resolver.native_result)

    def test_correct_board_never_turns_native_refusal_into_success(self):
        resolver=Resolver('501',Board(1),passed=False)
        self.assertIs(self.wrapped.run_tests(resolver),resolver.native_result)
        self.assertFalse(resolver.native_result)

    def test_unregistered_and_elementary_keep_original_results_and_flags(self):
        for passed in (False,True):
            resolver=Resolver('999',Board(2),passed)
            self.assertIs(self.wrapped.run_tests(resolver,True,True),resolver.native_result)
            self.assertEqual(resolver.calls,[(self.old,True,True)])
            self.school=False
            resolver=Resolver('501',Board(2),passed)
            self.assertIs(self.wrapped.run_tests(resolver),resolver.native_result)
            self.assertIs(resolver.calls[0][0],self.old)
            self.school=True

    def test_targetless_early_resolver_retains_original_behavior(self):
        resolver=Resolver('502',None)
        self.assertIs(self.wrapped.run_tests(resolver),resolver.native_result)
        self.assertIs(resolver.calls[0][0],self.old)

    def test_transfer_mapping_is_read_fresh_without_cached_test_result(self):
        resolver=Resolver('501',Board(2))
        self.assertFalse(self.wrapped.run_tests(resolver))
        self.membership['501']=2
        self.assertIs(self.wrapped.run_tests(resolver),resolver.native_result)

    def test_ambiguous_board_cannot_authorize_registered_actor(self):
        class Ambiguous(Board):
            def state_value_active(self,state):return True
        resolver=Resolver('501',Ambiguous(1))
        self.assertFalse(self.wrapped.run_tests(resolver))

    def test_npc_guard_keeps_native_list_and_refuses_third_party_restore(self):
        npc=type('super_HighSchool_Active_AttendClass_NPC',(),{
            'guid64':297779,'test_globals':self.old})
        result,undo=install_native_board_guard(npc,self.scope,self.failure)
        self.assertTrue(result['applied'])
        wrapped=npc.test_globals
        self.assertIs(wrapped.original,self.old)
        self.assertIs(wrapped.amended,self.old)
        resolver=Resolver('501',Board(1),False)
        self.assertIs(wrapped.run_tests(resolver),resolver.native_result)
        npc.test_globals=TestList(('third party',))
        self.assertFalse(undo.can_restore())
        self.assertFalse(undo())
        npc.test_globals=wrapped
        self.assertTrue(undo())
        self.assertIs(npc.test_globals,self.old)

    def test_picker_and_all_subjects_use_scope_and_exact_original_fallback(self):
        for variant in ('EA_ORIGINAL','ZERBU'):
            start,subjects=subject_fixture.fixture(variant)
            original_picker=picker_fixture.setup(4 if variant=='ZERBU' else 3)
            start.test_globals[1].test=CompoundTestList(original_picker)
            before_picker=start.test_globals[1].test
            # Actual TestLists expose run_tests; the legacy structural fakes do not.
            for subject in subjects.values():subject.test_globals=TestList(subject.test_globals)
            before={guid:s.test_globals for guid,s in subjects.items()}
            result,undo_picker=install_known_whiteboard_adapter(start,self.scope,self.failure)
            self.assertTrue(result['applied'],result)
            result,undo_subjects=install_subject_picker(start,subjects,True,self.scope,self.failure)
            self.assertTrue(result['applied'],result)
            for guid,subject in subjects.items():
                resolver=Resolver('999',Board(2),False)
                self.assertIs(subject.test_globals.run_tests(resolver),resolver.native_result)
                self.assertIs(resolver.calls[0][0],before[guid])
                self.assertFalse(subject.test_globals.run_tests(Resolver('502',Board(1))))
            self.assertTrue(undo_subjects())
            self.assertTrue(undo_picker())
            self.assertIs(start.test_globals[1].test,before_picker)


if __name__=='__main__':unittest.main()
