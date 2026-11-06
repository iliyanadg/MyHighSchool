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
    supplemental_staff_window, native_cafeteria_workstation)
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

    def test_missing_principal_and_second_teacher_use_verified_native_jobs(self):
        selected={'custodians':('44','45'),'principal':('43',),
                  'teacher1':('41',),'teacher2':('42',),
                  'cafeteria':('46',)}
        observed={'custodians':('45',),'principal':(),
                  'teacher1':('41',),'teacher2':(),
                  'cafeteria':('46',)}
        expected=(('44',290196,298096),('43',278223,298096),
                  ('42',278963,298052))
        for count,each in enumerate(expected):
            item,_=additional_staff_plan(selected,observed,(),
                self.CLOCK,1,already_attempted=tuple(x[0] for x in expected[:count]))
            self.assertEqual((item['sim_id'],item['job_guid'],
                              item['situation_guid']),each)
        item,_=additional_staff_plan(selected,observed,(),
            self.CLOCK,1,already_attempted=('44','43','42'))
        self.assertIsNone(item)
        observed['custodians']=()
        item,_=additional_staff_plan(selected,observed,(),
            self.CLOCK,1,already_attempted=('44',))
        self.assertEqual(item['role'],'teacher2')
        observed['teacher1']=()
        item,_=additional_staff_plan(selected,observed,(),
            self.CLOCK,1,already_attempted=('44',))
        self.assertIsNone(item)

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
        item,reason=additional_staff_plan(sel,obs,('47','48'),
            self.CLOCK,3,already_attempted=('47',))
        self.assertIsNone(item)
        self.assertEqual(reason,'EXTRA_CAFETERIA_NATIVE_JOB_PENDING_READBACK')
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
        for clock in (None,{}, {'hour':9,'minute':39},
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
        # When the game's native vendor exposes its real counter, match
        # definition IDs even if the object definition has no readable name.
        opaque=Definition(77,'opaque')
        obj=item(9,opaque)
        situation=types.SimpleNamespace(guid64=278011,
                                         get_tend_object=lambda:obj)
        self.assertIs(native_cafeteria_workstation(situation,mgr),obj)
        self.assertEqual(count_verified_school_cafeteria_stations(
            types.SimpleNamespace(get_all=lambda:[obj,item(10,opaque)]),
            obj),2)

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
                self.bouncer=types.SimpleNamespace(
                    submit_request=lambda req:self.events.append(
                        ('request',req._situation.guid64,
                         req._requested_sim_id,req._job_type.guid64)))
            def get(self,situation_id):
                guid={111:278011,112:298096,113:298052}.get(
                    situation_id,278011)
                def make_request(guest):
                    return types.SimpleNamespace(
                        _requested_sim_id=guest.sim_id,
                        _job_type=guest.job_type,
                        _situation=types.SimpleNamespace(guid64=guid))
                return types.SimpleNamespace(
                    guid64=guid,_create_request_from_guest_info=make_request)
            def create_situation(self,kind,guest_list=None):
                self.events.append((kind.guid64,tuple(
                    (g.sim_id,g.job_type.guid64)
                    for g in guest_list.guest_info_gen())))
                return 700+len(self.events)
        manager=Manager()
        staff={sid:types.SimpleNamespace(sim_id=sid)
               for sid in (41,42,43,44,45,46,47)}
        infos={sid:types.SimpleNamespace(
            get_sim_instance=lambda s=sim:s)
            for sid,sim in staff.items()}
        native={'custodians':(45,), 'cafeteria':(46,),
                'principal':(), 'teacher1':(41,), 'teacher2':()}
        native_jobs=(('custodians',298096,290196),
                     ('cafeteria',278011,278010),
                     ('principal',298096,278223),
                     ('teacher1',298052,277895),
                     ('teacher2',298052,278963))
        memberships=lambda sim,mgr:{
            'available':True,
            'jobs':[{'situation_guid':sguid,'job_guid':job}
                    for name,sguid,job in native_jobs
                    if sim.sim_id in native[name]]}
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
            staff_plan={'job_groups':{277895:('41',),
                         278963:('42',),278223:('43',),
                         290196:('44','45')},
                        'jobs':{278010:'46'},
                        'pending_extra_staff':{'cafeteria':('47',)}},
            staff_created={278011:111,298096:112,298052:113},
            staff_created_guests={
                278011:{278010:('46',)},
                298096:{290196:('44','45'),278223:('43',)},
                298052:{277895:('41',),278963:('42',)}},
            staff_extra_attempted=set(),
            staff_extra_created={},staff_extra_receipts=[],
            staff_extra_last_status=None,
            staff_pending=None,staff_pending_guests={},
            staff_jobs={guid:types.SimpleNamespace(guid64=guid)
                        for guid in (278010,290196,278223,277895,278963)},
            classroom_membership={},
            previous={(Manager,'create_situation'):Manager.create_situation},
            manager_owner=Manager,guest_cls=Factory,invited='INVITED',
            bound_zone=20)
        env={
            '_ea_native_cafeteria_tag':lambda:None,
            'game_clock':lambda service:{'hour':10,'minute':33},
            'services':services,'VENUE_STAFF_SITUATION':298096,
            'CORE_SITUATION':298052,
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
            if role in ('cafeteria','principal','teacher2'):
                native['custodians']=(44,45)
            if role in ('cafeteria','teacher2'):
                native['principal']=(43,)
            if role=='cafeteria':
                native['teacher2']=(42,)
            returned=env['_maybe_additional_school_staff'](runtime)
        return returned,manager.events,runtime

    def test_missing_janitor_reuses_existing_venue_situation(self):
        ok,events,rt=self.exercise(1,'janitor')
        self.assertTrue(ok,rt.staff_extra_last_status)
        self.assertEqual(events,[('request',298096,44,290196)])
        self.assertEqual(rt.staff_extra_created,{})
        self.assertIn('44',rt.staff_extra_attempted)

    def test_missing_principal_reuses_existing_venue_situation(self):
        ok,events,rt=self.exercise(1,'principal')
        self.assertTrue(ok,rt.staff_extra_last_status)
        self.assertEqual(events,[('request',298096,43,278223)])
        self.assertEqual(rt.staff_extra_created,{})

    def test_second_teacher_reuses_original_core_situation(self):
        ok,events,rt=self.exercise(1,'teacher2')
        self.assertTrue(ok,rt.staff_extra_last_status)
        self.assertEqual(events,[('request',298052,42,278963)])
        self.assertEqual(rt.staff_extra_created,{})

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
