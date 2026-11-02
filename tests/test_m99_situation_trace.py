"""M99: read-only EA situation tracing, independent of Sims 4 imports."""
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'/'m99_trace'))
from mhs99_situation_trace import snapshot

class Sim:
    def __init__(self,sid):
        self.sim_info=SimpleNamespace(sim_id=sid)

class Info:
    sim_id=31
    def __init__(self,sim=None):
        self.sim=sim
    def get_sim_instance(self):
        return self.sim

class SchoolSituation:
    guid64=277733
    id=701
    def __init__(self,member_ids=()):
        self.members=tuple(Sim(i) for i in member_ids)
    def get_sims_in_situation(self):
        return self.members

class Manager:
    def __init__(self,situation=None):
        self.situation=situation
    def get(self,sid):
        return self.situation if sid==701 else None
    def get_situations_sim_is_in(self,sim):
        return (self.situation,) if sim and self.situation and self.situation.members else ()

class TestSituationTrace(unittest.TestCase):
    def test_request_accepted_but_situation_no_longer_exists(self):
        report=snapshot(Manager(),Info(),701)
        self.assertEqual(report['created_situation_id'],701)
        self.assertEqual(report['situation_lookup'],'NOT_FOUND')
        self.assertEqual(report['phase'],'SITUATION_GONE_SIM_ABSENT')

    def test_situation_exists_but_sim_not_spawned(self):
        report=snapshot(Manager(SchoolSituation()),Info(),701)
        self.assertEqual(report['phase'],'SITUATION_ACTIVE_SIM_NOT_SPAWNED')
        self.assertFalse(report['on_lot'])
        self.assertEqual(report['situation_guid'],277733)
        self.assertEqual(report['situation_member_ids'],())

    def test_sim_present_and_member_of_correct_school_situation(self):
        sim=Sim(31)
        report=snapshot(Manager(SchoolSituation((31,))),Info(sim),701)
        self.assertEqual(report['phase'],'SIM_PRESENT_AND_IN_REQUESTED_SITUATION')
        self.assertTrue(report['in_school_situation'])
        self.assertEqual(report['situation_member_ids'],(31,))

    def test_sim_present_but_only_physical_not_confirmed_member(self):
        class NoMembers:
            id=701
        report=snapshot(Manager(NoMembers()),Info(Sim(31)),701)
        self.assertEqual(report['phase'],'SIM_PRESENT_MEMBERSHIP_UNVERIFIED')
        self.assertIsNone(report['situation_member_ids'])

    def test_no_situation_id_is_not_called_success(self):
        for candidate in (None,True,False,0,'701'):
            report=snapshot(Manager(SchoolSituation()),Info(),candidate)
            self.assertEqual(report['phase'],'INVALID_CREATE_RESULT')

    def test_ea_manager_without_lookup_keeps_unknown(self):
        result=snapshot(object(),Info(),701)
        self.assertEqual(result['situation_lookup'],'UNAVAILABLE')
        self.assertIsNone(result['situation_active'])

    def test_no_unverified_create_or_spawn_calls(self):
        class ReadOnlyManager(Manager):
            def create_situation(self,*args,**kwargs):
                self.fail('create')
            def destroy_situation_by_id(self,*args,**kwargs):
                self.fail('destroy')
            def fail(self,name):
                raise AssertionError('M99 must never call '+name)
        m=ReadOnlyManager(SchoolSituation())
        result=snapshot(m,Info(),701)
        self.assertEqual(result['phase'],'SITUATION_ACTIVE_SIM_NOT_SPAWNED')

if __name__=='__main__':
    unittest.main()
