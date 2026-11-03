"""M123 integrated 13-NPC school + real native two-classroom EA trial."""
import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'/'m122_classrooms'))
sys.path.insert(0,str(ROOT/'src'/'m123_class_repair'))
from tests.test_m121_thirteen_npc_trial import (
    environment, GuestList, Guest, Job, OriginalManager,
    OriginalBouncerRequest, PINNED
)


def load_trial():
    modules,state,blank,base,day=environment()
    original_create=OriginalManager.__dict__['create_situation']
    OriginalManager.calls=[]
    OriginalManager.req_calls=[]
    jobs=state['job_by_id']
    jobs[277919]=Job(277919)
    jobs[280777]=Job(280777)
    modules['services'].get_instance_manager=lambda t:types.SimpleNamespace(
        get=lambda guid:jobs.get(guid,base if guid==277894 else None))
    spec=importlib.util.spec_from_file_location(
        'mhs123_lesson_integration_test',
        str(ROOT/'src'/'m123_class_repair'/
            'mhs123_thirteen_npc_class_trial.py'))
    module=importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules,modules):
        spec.loader.exec_module(module)
    orig_arm=module.arm_m123
    def arm():
        with patch.dict(sys.modules,modules):
            return orig_arm()
    module.arm_m123=arm
    return module,modules,state,base,jobs,original_create


class M123OriginalEAClassroomIntegrationTests(unittest.TestCase):
    def tearDown(self):
        if hasattr(self,'mod'):
            if self.mod._RUNTIME is not None and self.mod._RUNTIME.active:
                self.assertTrue(self.mod._RUNTIME.stop())
            OriginalManager.create_situation=self.original_create

    def prepare(self):
        self.mod,self.modules,self.state,self.base,self.jobs,self.original_create=load_trial()
        self.assertIn('M123 PRONTA',self.mod.arm_m123())
        self.state['zone']=777
        self.state['schedule']=277657

    def test_class1_eight_registered_students_are_sent_in_single_original_EA_call(self):
        self.prepare()
        g=GuestList()
        g.add_guest_info(Guest(9001,Job(277918)))
        g.add_guest_info(Guest(999,Job(277919)))
        with patch.dict(sys.modules,self.modules):
            OriginalManager().create_situation(
                types.SimpleNamespace(guid64=304565),guest_list=g)
        self.assertEqual(len(OriginalManager.calls),1)
        altered=list(OriginalManager.calls[0][1].guest_info_gen())
        self.assertEqual([x.sim_id for x in altered[1:]],list(range(1,9)))
        self.assertEqual(len(list(g.guest_info_gen())),2)
        self.assertEqual(len(self.mod._RUNTIME.lesson_created),1)
        self.assertEqual(self.mod._RUNTIME.lesson_filter_hits,0)

    def test_second_alternative_class1_branch_left_original(self):
        self.prepare()
        with patch.dict(sys.modules,self.modules):
            first=GuestList()
            first.add_guest_info(Guest(999,self.jobs[277919]))
            OriginalManager().create_situation(
                types.SimpleNamespace(guid64=304565),guest_list=first)
            second=GuestList()
            second.add_guest_info(Guest(998,self.jobs[277919]))
            OriginalManager().create_situation(
                types.SimpleNamespace(guid64=304703),guest_list=second)
        self.assertIs(OriginalManager.calls[1][1],second)
        self.assertEqual(len(self.mod._RUNTIME.lesson_created),1)

    def test_other_ea_situation_never_rewritten(self):
        self.prepare()
        original=GuestList()
        original.add_guest_info(Guest(5555,self.base))
        with patch.dict(sys.modules,self.modules):
            OriginalManager().create_situation(
                types.SimpleNamespace(guid64=123123),guest_list=original)
        self.assertIs(OriginalManager.calls[-1][1],original)

    def test_class2_uses_separate_ea_student_job(self):
        self.prepare()
        original=GuestList()
        original.add_guest_info(Guest(4444,self.jobs[280777]))
        with patch.dict(sys.modules,self.modules):
            OriginalManager().create_situation(
                types.SimpleNamespace(guid64=304567),guest_list=original)
        ids=[g.sim_id for g in OriginalManager.calls[-1][1].guest_info_gen()]
        self.assertEqual(ids,list(range(9,17)))
        self.assertEqual(set(self.mod._RUNTIME.lesson_created),{2})

    def test_base_and_core_proven_behaviour_still_present(self):
        self.prepare()
        with patch.dict(sys.modules,self.modules):
            base=GuestList()
            base.add_guest_info(Guest(8888,self.base))
            OriginalManager().create_situation(
                types.SimpleNamespace(guid64=277733),guest_list=base)
            core=GuestList()
            for jobid in PINNED:
                core.add_guest_info(Guest(9999,self.jobs[jobid]))
            OriginalManager().create_situation(
                types.SimpleNamespace(guid64=298052),guest_list=core)
        self.assertEqual(len(self.mod._RUNTIME.created),1)
        self.assertIsNotNone(self.mod._RUNTIME.core_created)


if __name__=='__main__':
    unittest.main()
