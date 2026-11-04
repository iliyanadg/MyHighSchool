"""M121: real EA Base+Core native intervention, mock-game tests only."""
import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
from tests.test_m120_eight_base_live_trial import (
    environment as base_environment, school, GuestList, Guest, Job,
    OriginalManager, OriginalBouncerRequest,
)

PINNED={278965:'3',278966:'4',278967:'5',278968:'11',303765:'12'}
CORE=298052
BASE=277733


def environment():
    mods,state,blank,base,day=base_environment()
    job_by_id={i:Job(i) for i in PINNED}
    original_get=mods['services'].get_instance_manager
    mods['services'].get_instance_manager=lambda t:types.SimpleNamespace(
        get=lambda guid:job_by_id.get(guid,base if guid==277894 else None))
    state['job_by_id']=job_by_id
    state['native_situations']={}
    state['core_requests']=[]
    mods['services'].get_zone_situation_manager=lambda:types.SimpleNamespace(
        get=lambda ident:state['native_situations'].get(ident))
    return mods,state,blank,base,day


def load():
    mods,state,blank,base,day=environment()
    OriginalManager.calls=[]
    OriginalManager.req_calls=[]
    spec=importlib.util.spec_from_file_location(
        'mhs121_fake_runtime',
        str(ROOT/'src'/'m121_all_npc'/'mhs121_thirteen_npc_trial.py'))
    module=importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules,mods):
        spec.loader.exec_module(module)
    native_arm=module.arm_m121
    def with_native_imports():
        with patch.dict(sys.modules,mods):
            return native_arm()
    module.arm_m121=with_native_imports
    original_create=OriginalManager.__dict__['create_situation']

    def native_create(manager,kind,guest_list=None):
        OriginalManager.calls.append((kind,guest_list))
        if guest_list is None:
            return None
        jobs={}
        for guest in guest_list.guest_info_gen():
            j=guest.job_type.guid64
            jobs.setdefault(j,[]).append(guest.sim_id)
            req=OriginalBouncerRequest(kind,guest.job_type,guest.sim_id)
            if j in PINNED:
                state['core_requests'].append(req)
            OriginalManager.req_calls.append(
                (req,req.get_additional_filter_terms(),req.clone_for_replace()))
        assigned_id=812 if kind.guid64==CORE else 101+len([
            x for x in OriginalManager.calls if x[0].guid64==BASE])-1
        class NativeSituation(object):
            def __init__(self,guid,jobs):
                self.guid64=guid
                self.jobs=jobs
            def all_jobs_gen(self):
                return [state['job_by_id'].get(j,base if j==277894 else Job(j))
                        for j in self.jobs]
            def all_sims_in_job_gen(self,job):
                return [types.SimpleNamespace(id=sid,sim_id=sid)
                        for sid in self.jobs.get(job.guid64,())]
        state['native_situations'][assigned_id]=NativeSituation(kind.guid64,jobs)
        return assigned_id
    OriginalManager.create_situation=native_create
    return module,mods,state,blank,base,day,original_create,native_create


class NativeThirteenCoreTests(unittest.TestCase):
    def cleanup(self,module,original):
        if module._RUNTIME and module._RUNTIME.active:
            self.assertTrue(module._RUNTIME.stop())
        OriginalManager.create_situation=original

    def test_arm_keeps_eight_base_and_exact_five_user_core_ids(self):
        module,mods,state,blank,base,day,original,native=load()
        try:
            self.assertIn('PRONTA',module.arm_m121())
            self.assertEqual(len(module._RUNTIME.targets),8)
            self.assertEqual(module._RUNTIME.pinned,PINNED)
            self.assertEqual(set(module._RUNTIME.targets)&set(PINNED.values()),set())
        finally:
            self.cleanup(module,original)

    def test_eight_base_and_five_core_assignment_original_EA_jobs(self):
        module,mods,state,blank,base,day,original,native=load()
        try:
            self.assertIn('PRONTA',module.arm_m121())
            school(state)
            with patch.dict(sys.modules,mods):
                for ix in range(8):
                    guests=GuestList()
                    guests.add_guest_info(Guest(800+ix,base))
                    OriginalManager().create_situation(
                        types.SimpleNamespace(guid64=BASE),guest_list=guests)
                core_list=GuestList()
                core_list.add_guest_info(Guest(987,Job(277895)))
                for jobid in PINNED:
                    core_list.add_guest_info(
                        Guest(900+jobid,state['job_by_id'][jobid]))
                OriginalManager().create_situation(
                    types.SimpleNamespace(guid64=CORE),guest_list=core_list)
            controller=module._RUNTIME
            self.assertEqual(len(controller.created),8)
            self.assertEqual(controller.core_created,812)
            self.assertEqual(controller.core_filter_hits,5)
            self.assertEqual(controller.filter_hits,13)
            report=controller.report()
            self.assertIn('EA_base_present=8/8',report)
            self.assertIn('EA_core_present=5/5',report)
            self.assertEqual([j.sim_id for j in core_list.guest_info_gen()][1:],
                             [900+guid for guid in PINNED])
            actual_core=OriginalManager.calls[-1][1]
            new_guests=list(actual_core.guest_info_gen())
            self.assertEqual([x.sim_id for x in new_guests[:1]],[987])
            self.assertEqual([x.sim_id for x in new_guests[1:]],
                             [int(PINNED[j]) for j in PINNED])
            self.assertEqual(len(state['core_requests']),5)
        finally:
            self.cleanup(module,original)

    def test_duplicate_or_unknown_core_guests_are_not_edited(self):
        module,mods,state,blank,base,day,original,native=load()
        try:
            module.arm_m121()
            school(state)
            guests=GuestList()
            guests.add_guest_info(Guest(777,Job(278965)))
            guests.add_guest_info(Guest(778,Job(278965)))
            with patch.dict(sys.modules,mods):
                OriginalManager().create_situation(
                    types.SimpleNamespace(guid64=CORE),guest_list=guests)
            self.assertEqual(module._RUNTIME.core_refused,1)
            self.assertIsNone(module._RUNTIME.core_created)
            self.assertIs(OriginalManager.calls[-1][1],guests)
        finally:
            self.cleanup(module,original)

    def test_unsupported_core_job_tuning_blocks_home_arm(self):
        module,mods,state,blank,base,day,original,native=load()
        try:
            state['job_by_id'].pop(278966)
            self.assertIn('BLOCCATA',module.arm_m121())
        finally:
            self.cleanup(module,original)

    def test_restore_after_core_and_base_and_do_not_modify_unrelated_situation(self):
        module,mods,state,blank,base,day,original,native=load()
        prior=OriginalBouncerRequest.__dict__['__init__']
        try:
            module.arm_m121()
            school(state)
            original_guests=GuestList()
            original_guests.add_guest_info(Guest(999,base))
            with patch.dict(sys.modules,mods):
                OriginalManager().create_situation(
                    types.SimpleNamespace(guid64=5555),
                    guest_list=original_guests)
            self.assertIs(OriginalManager.calls[-1][1],original_guests)
        finally:
            self.cleanup(module,original)
        self.assertIs(OriginalBouncerRequest.__dict__['__init__'],prior)

    def test_wrong_zone_save_does_not_substitute_core(self):
        module,mods,state,blank,base,day,original,native=load()
        try:
            module.arm_m121()
            school(state)
            state['slot']='99'
            guests=GuestList()
            guests.add_guest_info(Guest(777,state['job_by_id'][278965]))
            with patch.dict(sys.modules,mods):
                OriginalManager().create_situation(
                    types.SimpleNamespace(guid64=CORE),guest_list=guests)
            self.assertIs(OriginalManager.calls[-1][1],guests)
            self.assertIsNone(module._RUNTIME.core_created)
        finally:
            self.cleanup(module,original)


if __name__=='__main__':
    unittest.main()
