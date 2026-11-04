"""M120 8-Base native EA classroom Beta, regression with fake EA runtime."""
import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
from tests.test_m119_one_base_live_trial import (
    environment as old_environment, GuestList, Guest, Job,
    OriginalManager, OriginalBouncerRequest,
)


def environment():
    mods,state,blank,base=old_environment()
    roles=types.ModuleType('mhs97_core_role_store')
    class CoreRoleStore(object):
        def __init__(self,folder):
            pass
        def load(self,slot):
            return types.SimpleNamespace(
                complete=True,
                chosen=lambda:{
                    278965:'3',278966:'4',278967:'5',
                    278968:'11',303765:'12'})
    roles.CoreRoleStore=CoreRoleStore
    mods['mhs97_core_role_store']=roles
    state['school_count_calls']=0
    class WeeklyScheduleDay(object):
        guid64=277657
        @classmethod
        def get_long_term_situation_count(cls,data,resolver):
            state['school_count_calls']+=1
            return (3,3)
    WeeklyScheduleDay.__module__='venues.weekly_schedule_zone_director'
    weekly=types.ModuleType('venues.weekly_schedule_zone_director')
    weekly.WeeklyScheduleDay=WeeklyScheduleDay
    venues=types.ModuleType('venues')
    venues.__path__=[]
    venues.weekly_schedule_zone_director=weekly
    mods['venues']=venues
    mods['venues.weekly_schedule_zone_director']=weekly
    return mods,state,blank,base,WeeklyScheduleDay


def load():
    mods,state,blank,base,day=environment()
    OriginalManager.calls=[]
    OriginalManager.req_calls=[]
    spec=importlib.util.spec_from_file_location(
        'mhs120_test_singleton',
        str(ROOT/'src'/'m120_base'/'mhs120_eight_base_live_trial.py'))
    obj=importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules,mods):
        spec.loader.exec_module(obj)
    native_arm=obj.arm_m120
    def wrapped_arm():
        with patch.dict(sys.modules,mods):
            return native_arm()
    obj.arm_m120=wrapped_arm
    return obj,mods,state,blank,base,day


def school(state):
    state['zone']=777
    state['schedule']=277657


class EightBaseLiveTests(unittest.TestCase):
    def test_home_arming_requires_five_manual_core_and_eight_base(self):
        obj,mods,state,blank,job,day=load()
        self.assertIn('PRONTA',obj.arm_m120())
        self.assertEqual(obj._RUNTIME.targets,('2','6','7','8','10','13','14','15'))
        self.assertTrue(obj._RUNTIME.stop())

    def test_ea_original_count_three_becomes_eight_only_for_school_base(self):
        obj,mods,state,blank,job,day=load()
        original=day.__dict__['get_long_term_situation_count']
        self.assertIn('PRONTA',obj.arm_m120())
        try:
            base=types.SimpleNamespace(
                situation=types.SimpleNamespace(guid64=277733))
            other=types.SimpleNamespace(
                situation=types.SimpleNamespace(guid64=2222))
            self.assertEqual(day.get_long_term_situation_count(base,None),
                             (3,3))
            school(state)
            self.assertEqual(day.get_long_term_situation_count(other,None),
                             (3,3))
            self.assertEqual(day.get_long_term_situation_count(base,None),
                             (8,8))
            self.assertEqual(obj._RUNTIME.base_count_overrides,1)
        finally:
            self.assertTrue(obj._RUNTIME.stop())
        self.assertIs(day.__dict__['get_long_term_situation_count'],original)

    def test_exact_eight_student_guest_lists_and_no_ninth_override(self):
        obj,mods,state,blank,job,day=load()
        self.assertIn('PRONTA',obj.arm_m120())
        school(state)
        originals=[]
        try:
            with patch.dict(sys.modules,mods):
                for i in range(9):
                    old=GuestList()
                    old.add_guest_info(Guest(7777+i,job))
                    originals.append(old)
                    OriginalManager().create_situation(
                        types.SimpleNamespace(guid64=277733),
                        guest_list=old)
            self.assertEqual(len(obj._RUNTIME.created),8)
            assigned=[list(c[1].guest_info_gen())[-1].sim_id
                      for c in OriginalManager.calls[:8]]
            self.assertEqual(assigned,[2,6,7,8,10,13,14,15])
            self.assertEqual(
                [list(x.guest_info_gen())[-1].sim_id for x in originals],
                [7777+i for i in range(9)])
            self.assertIs(OriginalManager.calls[-1][1],originals[-1])
            self.assertEqual(obj._RUNTIME.filter_hits,8)
        finally:
            self.assertTrue(obj._RUNTIME.stop())

    def test_no_change_to_other_school_situations_or_wrong_save(self):
        obj,mods,state,blank,job,day=load()
        obj.arm_m120()
        school(state)
        try:
            g=GuestList()
            g.add_guest_info(Guest(900,job))
            with patch.dict(sys.modules,mods):
                OriginalManager().create_situation(
                    types.SimpleNamespace(guid64=298052),guest_list=g)
                self.assertEqual(len(obj._RUNTIME.created),0)
                state['slot']='12'
                OriginalManager().create_situation(
                    types.SimpleNamespace(guid64=277733),guest_list=g)
            self.assertEqual(len(obj._RUNTIME.created),0)
            self.assertIs(OriginalManager.calls[-1][1],g)
        finally:
            obj._RUNTIME.stop()

    def test_eight_lookups_and_rollback_without_stale_ea_handlers(self):
        obj,mods,state,blank,job,day=load()
        owner=OriginalManager.__dict__['create_situation']
        request=OriginalBouncerRequest.__dict__['__init__']
        obj.arm_m120()
        school(state)
        try:
            with patch.dict(sys.modules,mods):
                for i in range(8):
                    g=GuestList()
                    g.add_guest_info(Guest(i+600,job))
                    OriginalManager().create_situation(
                        types.SimpleNamespace(guid64=277733),guest_list=g)
            report=obj._RUNTIME.report()
            self.assertIn('EA_base_created=8/8',report)
            self.assertIn('count_override=0',report)
        finally:
            self.assertTrue(obj._RUNTIME.stop())
        self.assertIs(OriginalManager.__dict__['create_situation'],owner)
        self.assertIs(OriginalBouncerRequest.__dict__['__init__'],request)

    def test_ambiguous_original_ea_guest_list_is_preserved(self):
        obj,mods,state,blank,job,day=load()
        obj.arm_m120()
        school(state)
        try:
            g=GuestList()
            g.add_guest_info(Guest(888,job))
            g.add_guest_info(Guest(889,job))
            with patch.dict(sys.modules,mods):
                OriginalManager().create_situation(
                    types.SimpleNamespace(guid64=277733),guest_list=g)
            self.assertEqual(len(obj._RUNTIME.created),0)
            self.assertEqual(obj._RUNTIME.refused,1)
            self.assertIs(OriginalManager.calls[-1][1],g)
        finally:
            obj._RUNTIME.stop()


if __name__=='__main__':
    unittest.main()
