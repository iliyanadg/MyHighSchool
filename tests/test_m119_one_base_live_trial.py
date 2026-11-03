"""M119 user-testable single EA Base intervention, mock game regression."""
import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]


class Job(object):
    def __init__(self,guid):
        self.guid64=guid
        self.filter=object()


class Guest(object):
    def __init__(self,sid,job,accept_alternate_sim=False):
        self.sim_id=sid
        self.job_type=job
        self.accept_alternate_sim=accept_alternate_sim
    def clone_for_guest_list(self):
        return Guest(self.sim_id,self.job_type,self.accept_alternate_sim)


class GuestInfo(Guest):
    @classmethod
    def construct_from_purpose(cls,sid,job,purpose):
        return cls(sid,job,False)


class GuestList(object):
    def __init__(self,invite_only=False,host_sim_id=7,
                 filter_requesting_sim_id=7):
        self.invite_only=invite_only
        self.host_sim_id=host_sim_id
        self.filter_requesting_sim_id=filter_requesting_sim_id
        self.guests=[]
    def add_guest_info(self,guest):
        self.guests.append(guest)
    def guest_info_gen(self):
        return iter(self.guests)


class SimInfo(object):
    def __init__(self,sid,selectable=False):
        self.sim_id=sid
        self.age='TEEN'
        self.species='HUMAN'
        self.is_selectable=selectable


class OriginalBouncerRequest(object):
    def __init__(self,situation,job,sid):
        self._situation=situation
        self._job_type=job
        self._requested_sim_id=sid
        self._constrained_sim_ids={sid}
        self._continue_if_constraints_fail=False
        self._for_persisted_sim=False
        self._sim_filter=job.filter
    def get_additional_filter_terms(self):
        return ('vanilla',)
    def clone_for_replace(self):
        return {'random':'vanilla'}


class OriginalManager(object):
    calls=[]
    req_calls=[]
    def create_situation(self,situation,guest_list=None):
        self.calls.append((situation,guest_list))
        if guest_list is not None:
            for guest in guest_list.guest_info_gen():
                if guest.job_type.guid64==277894:
                    req=OriginalBouncerRequest(
                        situation,guest.job_type,guest.sim_id)
                    self.req_calls.append((req,req.get_additional_filter_terms(),
                                            req.clone_for_replace()))
        return 101


def environment():
    state={'zone':111,'schedule':999,'slot':'11','teen_count':3}
    base=Job(277894)
    services=types.ModuleType('services')
    services.current_zone=lambda:types.SimpleNamespace(id=state['zone'])
    services.venue_service=lambda:types.SimpleNamespace(
        get_zone_director=lambda:types.SimpleNamespace(_schedule=
            types.SimpleNamespace(guid64=state['schedule'])))
    infos={i:SimInfo(i,selectable=i in (1,9,16))
           for i in range(1,17)}
    services.sim_info_manager=lambda:types.SimpleNamespace(get=infos.get)
    services.active_household=lambda:types.SimpleNamespace(
        sim_info_gen=lambda:(infos[i] for i in (1,9,16)))
    services.get_instance_manager=lambda t:types.SimpleNamespace(
        get=lambda guid:base if guid==277894 else None)

    simtypes=types.ModuleType('sims.sim_info_types')
    simtypes.Age=type('Age',(),{'TEEN':'TEEN'})
    simtypes.Species=type('Species',(),{'HUMAN':'HUMAN'})
    sims=types.ModuleType('sims')
    sims.__path__=[]
    sims.sim_info_types=simtypes
    filterstunable=types.ModuleType('filters.tunable')
    blank=types.SimpleNamespace(get_filter_terms=lambda:())
    filterstunable.TunableSimFilter=type('TunableSimFilter',(),
                                        {'BLANK_FILTER':blank})
    filters=types.ModuleType('filters')
    filters.__path__=[]
    filters.tunable=filterstunable

    sims4=types.ModuleType('sims4')
    sims4.__path__=[]
    cmds=types.ModuleType('sims4.commands')
    cmds.CommandType=type('CommandType',(),{'Live':1})
    cmds.Command=lambda name,command_type:lambda fn:fn
    cmds.output=lambda s,connection=None:None
    sims4.commands=cmds
    resources=types.ModuleType('sims4.resources')
    resources.Types=type('Types',(),{'SITUATION_JOB':'EA_JOBS'})
    sims4.resources=resources

    bridge=types.ModuleType('mhs_m2_game_bridge')
    bridge.current_slot=lambda allow_travel=False:state['slot']
    roster_mod=types.ModuleType('mhs_m2_store')
    class RosterStore(object):
        def __init__(self,directory):
            pass
        def load(self,slot):
            return types.SimpleNamespace(class_members=lambda i:
                tuple(str(j) for j in range(1,9)) if i==1
                else tuple(str(j) for j in range(9,17)))
    roster_mod.RosterStore=RosterStore
    settings_mod=types.ModuleType('mhs34_settings')
    class SettingsStore(object):
        def __init__(self,directory):
            pass
        def load(self,slot):
            return types.SimpleNamespace(active=True,class_count=2)
    settings_mod.SettingsStore=SettingsStore

    sm=types.ModuleType('situations.situation_manager')
    sm.SituationManager=OriginalManager
    bouncer=types.ModuleType('situations.bouncer')
    bouncer.__path__=[]
    bouncer_req=types.ModuleType('situations.bouncer.bouncer_request')
    bouncer_req.BouncerRequest=OriginalBouncerRequest
    bouncer.bouncer_request=bouncer_req
    guests=types.ModuleType('situations.situation_guest_list')
    guests.SituationGuestInfo=GuestInfo
    guests.SituationGuestList=GuestList
    guests.SituationInvitationPurpose=type('Purpose',(),{'INVITED':'INVITED'})
    situations=types.ModuleType('situations')
    situations.__path__=[]
    situations.situation_manager=sm
    situations.situation_guest_list=guests
    situations.bouncer=bouncer
    modules={
        'services':services,
        'sims':sims,'sims.sim_info_types':simtypes,
        'filters':filters,'filters.tunable':filterstunable,
        'sims4':sims4,'sims4.commands':cmds,
        'sims4.resources':resources,
        'mhs_m2_game_bridge':bridge,
        'mhs_m2_store':roster_mod,'mhs34_settings':settings_mod,
        'situations':situations,'situations.situation_manager':sm,
        'situations.situation_guest_list':guests,
        'situations.bouncer':bouncer,
        'situations.bouncer.bouncer_request':bouncer_req,
    }
    return modules,state,blank,base


def load_trial():
    mods,state,blank,base=environment()
    OriginalManager.calls=[]
    OriginalManager.req_calls=[]
    spec=importlib.util.spec_from_file_location(
        'mhs119_unique_test',
        str(ROOT/'src'/'m119_live_trial'/'mhs119_one_base_live_trial.py'))
    obj=importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules,mods):
        spec.loader.exec_module(obj)
    return obj,mods,state,blank,base


class M119OneEAStudentTests(unittest.TestCase):
    def test_home_arming_installs_four_hooks_and_restores_on_stop(self):
        mod,mods,state,blank,base=load_trial()
        prior=OriginalManager.__dict__['create_situation']
        self.assertIn('PRONTA',mod._arm())
        self.assertEqual(mod._STATE.target,'2')
        self.assertIsNot(OriginalManager.__dict__['create_situation'],prior)
        self.assertEqual(mod._STATE.attempts,0)
        self.assertIn('RIPRISTINATA',mod._stop())
        self.assertIs(OriginalManager.__dict__['create_situation'],prior)

    def test_first_original_base_substitutes_registered_npc_and_blocks_random(self):
        mod,mods,state,blank,base=load_trial()
        self.assertIn('PRONTA',mod._arm())
        try:
            state['zone']=777
            state['schedule']=277657
            original=GuestList()
            original.add_guest_info(Guest(999,base))
            with patch.dict(sys.modules,mods):
                result=OriginalManager().create_situation(
                    types.SimpleNamespace(guid64=277733),guest_list=original)
            self.assertEqual(result,101)
            self.assertEqual(mod._STATE.attempts,1)
            self.assertEqual(mod._STATE.created_id,101)
            supplied=OriginalManager.calls[-1][1]
            self.assertEqual([g.sim_id for g in supplied.guest_info_gen()],[2])
            self.assertEqual([g.sim_id for g in original.guest_info_gen()],[999])
            req,terms,replacement=OriginalManager.req_calls[-1]
            self.assertIs(req._sim_filter,blank)
            self.assertEqual(terms,())
            self.assertIsNone(replacement)
            self.assertEqual(mod._STATE.filter_applied,1)
            self.assertEqual(mod._STATE.replacements_blocked,1)
        finally:
            self.assertIn('RIPRISTINATA',mod._stop())

    def test_other_situations_or_second_school_base_are_vanilla(self):
        mod,mods,state,blank,base=load_trial()
        mod._arm()
        try:
            state['zone']=777
            state['schedule']=277657
            other=GuestList()
            other.add_guest_info(Guest(999,base))
            with patch.dict(sys.modules,mods):
                OriginalManager().create_situation(
                    types.SimpleNamespace(guid64=12345),guest_list=other)
                self.assertEqual(mod._STATE.attempts,0)
                OriginalManager().create_situation(
                    types.SimpleNamespace(guid64=277733),guest_list=other)
                OriginalManager().create_situation(
                    types.SimpleNamespace(guid64=277733),guest_list=other)
            self.assertEqual(mod._STATE.attempts,1)
            self.assertIs(OriginalManager.calls[0][1],other)
            self.assertIs(OriginalManager.calls[-1][1],other)
        finally:
            mod._stop()

    def test_home_school_missing_guest_list_passes_original_and_reports(self):
        mod,mods,state,blank,base=load_trial()
        mod._arm()
        try:
            state['zone']=777
            state['schedule']=277657
            with patch.dict(sys.modules,mods):
                OriginalManager().create_situation(
                    types.SimpleNamespace(guid64=277733),
                    guest_list=None)
            self.assertEqual(mod._STATE.attempts,0)
            self.assertEqual(mod._STATE.request_refusal_count,1)
        finally:
            mod._stop()

    def test_wrong_save_or_wrong_zone_has_no_student_override(self):
        mod,mods,state,blank,base=load_trial()
        mod._arm()
        try:
            state['zone']=777
            state['schedule']=277657
            state['slot']='12'
            g=GuestList()
            g.add_guest_info(Guest(999,base))
            with patch.dict(sys.modules,mods):
                OriginalManager().create_situation(
                    types.SimpleNamespace(guid64=277733),guest_list=g)
            self.assertEqual(mod._STATE.attempts,0)
            self.assertIs(OriginalManager.calls[-1][1],g)
        finally:
            mod._stop()

    def test_third_party_changes_are_not_overwritten(self):
        mod,mods,state,blank,base=load_trial()
        mod._arm()
        orig=OriginalManager.__dict__['create_situation']
        def thirdparty(*args,**kwargs):
            return 7
        OriginalManager.create_situation=thirdparty
        try:
            self.assertIn('BLOCCATO',mod._stop())
            self.assertIs(OriginalManager.create_situation,thirdparty)
        finally:
            # Fixture cleanup only; in the game a safe restart restores.
            OriginalManager.create_situation=mod._STATE.saved[
                (OriginalManager,'create_situation')]
            for (cls,attr),method in mod._STATE.saved.items():
                setattr(cls,attr,method)
            mod._STATE.active=False


if __name__=='__main__':
    unittest.main()
