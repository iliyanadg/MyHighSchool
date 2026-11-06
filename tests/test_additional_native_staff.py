"""Supplemental school staff: exact identity, independent EA jobs, no guesses."""
import ast
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src/classroom_control'))
from mhs_additional_native_staff import (
    additional_staff_plan, count_verified_school_cafeteria_stations,
    supplemental_staff_window)
from mhs_native_staff_appointments import (
    project_native_staff_guests, projected_staff_ids)
from tests.test_native_staff_appointments import GuestList, Factory


class AdditionalStaffPolicyTests(unittest.TestCase):
    CLOCK={'hour':10,'minute':33}

    def test_one_missing_custodian_requires_one_real_native_job(self):
        selected={'custodians':('44','45'),'cafeteria':('46','47','48')}
        observed={'custodians':('45',),'cafeteria':('46',)}
        item,reason=additional_staff_plan(selected,observed,('47','48'),
            self.CLOCK,3)
        self.assertEqual((item['sim_id'],item['job_guid'],item['situation_guid']),
                         ('44',290196,298096))
        self.assertEqual(reason,'ONE_SELECTED_CUSTODIAN_MISSING')
        item,reason=additional_staff_plan(selected,observed,('47','48'),
            self.CLOCK,3,already_attempted=('44',))
        self.assertEqual((item['sim_id'],item['situation_guid']),('47',278011))

    def test_second_and_third_vendor_require_extra_stations(self):
        sel={'custodians':(),'cafeteria':('46','47','48')}
        obs={'custodians':(),'cafeteria':('46',)}
        item,reason=additional_staff_plan(sel,obs,('47','48'),
            self.CLOCK,1)
        self.assertIsNone(item)
        self.assertEqual(reason,'ADDITIONAL_CAFETERIA_STATION_REQUIRED')
        item,reason=additional_staff_plan(sel,obs,('47','48'),
            self.CLOCK,2)
        self.assertEqual(item['sim_id'],'47')
        item,reason=additional_staff_plan(sel,
            {'cafeteria':('46','47'), 'custodians':()},
            ('47','48'),self.CLOCK,2)
        self.assertIsNone(item)
        self.assertEqual(reason,'ADDITIONAL_CAFETERIA_STATION_REQUIRED')
        item,_=additional_staff_plan(sel,
            {'cafeteria':('46','47'), 'custodians':()},
            ('47','48'),self.CLOCK,3)
        self.assertEqual(item['sim_id'],'48')

    def test_primary_must_be_really_working_no_guest_receipts_as_evidence(self):
        sel={'custodians':(),'cafeteria':('46','47')}
        item,reason=additional_staff_plan(sel,{'cafeteria':()},('47',),
            self.CLOCK,2)
        self.assertIsNone(item)
        self.assertEqual(reason,'PRIMARY_CAFETERIA_WORKER_NOT_IN_NATIVE_JOB')
        for clock in (None,{}, {'hour':10,'minute':29},
                      {'hour':11,'minute':30}, {'hour':10,'minute':True}):
            self.assertFalse(supplemental_staff_window(clock))

    def test_workstation_detection_uses_distinct_real_objects(self):
        class Definition:
            def __init__(self,n,kind):
                self.id=n
                self.name=kind
        def item(oid,definition):
            return types.SimpleNamespace(id=oid,definition=definition)
        good=Definition(11,'object_CafeteriaStation_HighSchool')
        wrong=Definition(12,'object_SchoolDesk')
        objects=[item(1,good),item(2,good),item(2,good),item(3,wrong)]
        mgr=types.SimpleNamespace(get_all=lambda:objects)
        self.assertEqual(count_verified_school_cafeteria_stations(mgr),2)
        self.assertIsNone(count_verified_school_cafeteria_stations(None))
        self.assertIsNone(count_verified_school_cafeteria_stations(object()))

    def test_extra_guest_list_has_one_exact_employee_and_no_principal(self):
        job=types.SimpleNamespace(guid64=290196)
        old=GuestList()
        new,projection=project_native_staff_guests(old,298096,
            {'jobs':{290196:'44'},'job_groups':{290196:('44',)}},
            {290196:job},Factory,'INVITED')
        self.assertTrue(projection['applied'])
        self.assertEqual(tuple((g.sim_id,g.job_type.guid64)
            for g in new.guest_info_gen()),((44,290196),))
        self.assertEqual(projected_staff_ids(projection),{290196:('44',)})


class SupplementalRuntimeTests(unittest.TestCase):
    @staticmethod
    def extracted_function():
        path=ROOT/'src/m145_class2_playable/mhs145_classroom_controller.py'
        tree=ast.parse(path.read_text())
        node=next(n for n in tree.body if isinstance(n,ast.FunctionDef)
                  and n.name=='_maybe_additional_school_staff')
        code=compile(ast.Module(body=[node],type_ignores=[]),str(path),'exec')
        return code

    def exercise(self,station_count,role):
        # Only a subset of the actual controller is needed; the executed
        # function is extracted unmodified from the actual shipped source.
        from mhs_native_staff_appointments import ROLE_JOBS
        class Manager:
            def __init__(self):
                self.events=[]
            def create_situation(self,kind,guest_list=None):
                self.events.append((kind.guid64,tuple(
                    (g.sim_id,g.job_type.guid64)
                    for g in guest_list.guest_info_gen())))
                return 700+len(self.events)
        manager=Manager()
        staff={
            44:types.SimpleNamespace(sim_id=44),
            45:types.SimpleNamespace(sim_id=45),
            46:types.SimpleNamespace(sim_id=46),
            47:types.SimpleNamespace(sim_id=47)}
        infos={sid:types.SimpleNamespace(
            get_sim_instance=lambda s=sim:s)
            for sid,sim in staff.items()}
        native={'custodians':(45,), 'cafeteria':(46,)}
        memberships=lambda sim,mgr:{
            'available':True,
            'jobs':[{'situation_guid':298096,'job_guid':290196}]
                   if sim.sim_id in native['custodians'] else
                   ([{'situation_guid':278011,'job_guid':278010}]
                    if sim.sim_id in native['cafeteria'] else [])}
        services=types.SimpleNamespace(
            get_zone_situation_manager=lambda:manager,
            sim_info_manager=lambda:types.SimpleNamespace(get=infos.get),
            object_manager=lambda:types.SimpleNamespace(
                get_all=lambda:[types.SimpleNamespace(
                    id=i+1,definition=types.SimpleNamespace(
                    id=111,name='object_CafeteriaStation_HighSchool'))
                    for i in range(station_count)]),
            time_service=lambda:object(),
            get_instance_manager=lambda kind:types.SimpleNamespace(
                get=lambda guid:types.SimpleNamespace(guid64=guid)))
        runtime=types.SimpleNamespace(
            active=True,school_ready=True,in_school=lambda:True,
            staff_plan={'job_groups':{290196:('44','45')},
                        'jobs':{278010:'46'},
                        'pending_extra_staff':{'cafeteria':('47',)}},
            staff_created={278011:111,298096:112},
            staff_created_guests={
                278011:{278010:('46',)},298096:{290196:('44','45')}},
            staff_extra_attempted=set(),
            staff_extra_created={},staff_extra_receipts=[],
            staff_extra_last_status=None,
            staff_pending=None,staff_pending_guests={},
            staff_jobs={278010:types.SimpleNamespace(guid64=278010),
                        290196:types.SimpleNamespace(guid64=290196)},
            classroom_membership={},
            previous={(Manager,'create_situation'):Manager.create_situation},
            manager_owner=Manager,guest_cls=Factory,invited='INVITED',
            bound_zone=20)
        runtime.staff_created_guests[298096][290196]=('45',)
        env={
            'game_clock':lambda service:{'hour':10,'minute':33},
            'services':services,'VENUE_STAFF_SITUATION':298096,
            'CAFETERIA_STAFF_SITUATION':278011,
            'zone_schedule':lambda:(20,277657),
            'project_native_staff_guests':project_native_staff_guests,
            'projected_staff_ids':projected_staff_ids}
        exec(self.extracted_function(),env)
        fake_readback=types.ModuleType('mhs_school_readback')
        fake_readback.school_memberships=memberships
        guest_mod=types.ModuleType('situations.situation_guest_list')
        guest_mod.SituationGuestList=GuestList
        situ=types.ModuleType('situations')
        types_mod=types.ModuleType('sims4.resources')
        types_mod.Types=types.SimpleNamespace(SITUATION='SITUATION')
        sims4=types.ModuleType('sims4')
        with patch.dict(sys.modules,{
            'mhs_school_readback':fake_readback,
            'situations':situ,
            'situations.situation_guest_list':guest_mod,
            'sims4':sims4,
            'sims4.resources':types_mod}):
            if role=='cafeteria':
                native['custodians']=(44,45)
            returned=env['_maybe_additional_school_staff'](runtime)
        return returned,manager.events,runtime

    def test_missing_janitor_uses_new_venue_situation_without_principal(self):
        ok,events,rt=self.exercise(1,'janitor')
        self.assertTrue(ok,rt.staff_extra_last_status)
        self.assertEqual(events,[(298096,((44,290196),))])
        self.assertIn('44',rt.staff_extra_created)

    def test_vendor_uses_new_tend_situation_only_with_second_counter(self):
        ok,events,rt=self.exercise(2,'cafeteria')
        self.assertTrue(ok,rt.staff_extra_last_status)
        self.assertEqual(events,[(278011,((47,278010),))])
        self.assertEqual(rt.staff_created_guests[278011][278010],
                         ('46','47'))
        ok,events,rt=self.exercise(1,'cafeteria')
        self.assertFalse(ok)
        self.assertEqual(events,[])


if __name__=='__main__':
    unittest.main()
