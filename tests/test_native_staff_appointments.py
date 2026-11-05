"""Exact native EA staffing and no invented additional job slots."""
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src/classroom_control'))
from mhs_native_staff_appointments import (
    ROLE_JOBS, load_native_staff_plan, project_native_staff_guests,
    projected_staff_ids)

class Stored(object):
    def __init__(self,values):self.values=values
    def members(self,role):return self.values.get(role,())

class Sims(object):
    def __init__(self,sims):self.sims=sims
    def get(self,sid):return self.sims.get(sid)

class Guest(object):
    def __init__(self,sid,job):
        self.sim_id=int(sid)
        self.job_type=SimpleNamespace(guid64=job)
        self.accept_alternate_sim=False
    def clone_for_guest_list(self):
        return Guest(self.sim_id,self.job_type.guid64)

class GuestList(object):
    def __init__(self,invite_only=True,host_sim_id=0,
                 filter_requesting_sim_id=0):
        self.host_sim_id=host_sim_id
        self.filter_requesting_sim_id=filter_requesting_sim_id
        self.guests=[]
    def add_guest_info(self,g):self.guests.append(g)
    def guest_info_gen(self):return iter(self.guests)

class Factory(object):
    @staticmethod
    def construct_from_purpose(sid,job,purpose):
        return Guest(sid,job.guid64)

def makeplan(multi=False):
    values={'teacher1':('41',),'teacher2':('42',),
            'principal':('43',),
            'custodians':('44','45') if multi else ('44',),
            'cafeteria':('46',)}
    infos={n:SimpleNamespace(age='ADULT',species='HUMAN')
           for n in range(41,47)}
    return load_native_staff_plan(Stored(values),Sims(infos),'HUMAN',
                                  ('YOUNGADULT','ADULT','ELDER'),
                                  enrolled_ids=('100', '101'))

JOBS={j:SimpleNamespace(guid64=j)
      for pairs in ROLE_JOBS.values() for _,j in pairs}

class StaffBridgeTests(unittest.TestCase):
    def test_day_start_snapshots_every_selected_role_even_when_ea_unsupported(self):
        r=Stored({'teacher1':('41',),'custodians':('44','45'),
                  'cafeteria':('46','47')})
        infos={n:SimpleNamespace(age='ADULT',species='HUMAN')
               for n in range(41,48)}
        p=load_native_staff_plan(r,Sims(infos),'HUMAN',('ADULT',))
        self.assertEqual(p['selected_roles']['teacher1'],('41',))
        self.assertEqual(p['selected_roles']['custodians'],('44','45'))
        self.assertEqual(p['selected_roles']['cafeteria'],('46','47'))
        self.assertEqual(p['job_groups'][278010],('46',))
        self.assertEqual(p['jobs'][278010],'46')
        self.assertEqual(p['pending_extra_staff']['cafeteria'],('47',))
        self.assertEqual(p['blocked']['cafeteria'],
                         'EXTRA_CAFETERIA_WORKERS_PENDING_NATIVE_STATIONS')

    def test_only_successfully_projected_staff_receive_bouncer_receipt(self):
        self.assertEqual(projected_staff_ids(None),{})
        self.assertEqual(projected_staff_ids({
            'applied':False,'appointed':{278223:'43'}}),{})
        receipt=projected_staff_ids({
            'applied':True,'appointed':{278223:'43',290196:['44','45']}})
        self.assertEqual(receipt,{278223:('43',),290196:('44','45')})
        # A bad ID, duplicate job entries or a forged unknown job
        # must not let a selected Sim bypass EA filter validation.
        self.assertEqual(projected_staff_ids({
            'applied':True,'appointed':{290196:['44','44']}}),{})
        self.assertEqual(projected_staff_ids({
            'applied':True,'appointed':{999999:'44'}}),{})

    def test_two_custodians_without_principal_still_project(self):
        values={'custodians':('44','45')}
        infos={n:SimpleNamespace(age='ADULT',species='HUMAN')
               for n in (44,45)}
        plan=load_native_staff_plan(Stored(values),Sims(infos),
                                    'HUMAN',('ADULT',))
        self.assertEqual(plan['jobs'],{})
        self.assertEqual(plan['job_groups'],{290196:('44','45')})
        projected,report=project_native_staff_guests(
            GuestList(),298096,plan,JOBS,Factory,'INVITED')
        self.assertTrue(report['applied'],report)
        self.assertEqual(tuple(x.sim_id for x in projected.guests),(44,45))

    def test_dynamic_sims_and_real_job_identifiers(self):
        p=makeplan()
        self.assertEqual(p['jobs'][277895],'41')
        self.assertEqual(p['jobs'][278963],'42')
        self.assertEqual(p['jobs'][278223],'43')
        self.assertEqual(p['jobs'][290196],'44')
        self.assertEqual(p['jobs'][278010],'46')

    def test_core_replaces_both_teachers_but_keeps_five_student_jobs(self):
        old=GuestList()
        for job in (278965,278966,278967,278968,303765):
            old.add_guest_info(Guest(1000+job,job))
        old.add_guest_info(Guest(10,277895))
        old.add_guest_info(Guest(11,278963))
        fixed,report=project_native_staff_guests(
            old,298052,makeplan(),JOBS,Factory,'INVITED',
            excluded_ids=('100','101'))
        self.assertTrue(report['applied'],report)
        self.assertEqual(len(old.guests),7)
        self.assertEqual([x.sim_id for x in old.guests[-2:]],[10,11])
        self.assertEqual([x.sim_id for x in fixed.guests[-2:]],[41,42])
        self.assertEqual([x.sim_id for x in fixed.guests[:5]],
                         [1000+j for j in (278965,278966,278967,278968,303765)])
        self.assertFalse(fixed.guests[-1].accept_alternate_sim)

    def test_venue_principal_and_one_janitor(self):
        old=GuestList()
        fixed,report=project_native_staff_guests(
            old,298096,makeplan(),JOBS,Factory,'INVITED')
        self.assertTrue(report['applied'])
        self.assertEqual([x.job_type.guid64 for x in fixed.guests],
                         [278223,290196])
        self.assertEqual([x.sim_id for x in fixed.guests],[43,44])

    def test_cafeteria_situation_requires_native_guest_form(self):
        fixed,report=project_native_staff_guests(
            None,278011,makeplan(),JOBS,Factory,'INVITED')
        self.assertIsNone(fixed)
        self.assertEqual(report['reason'],'NATIVE_GUEST_LIST_UNAVAILABLE')

    def test_two_custodians_exactly_selected_in_one_original_venue(self):
        p=makeplan(multi=True)
        self.assertNotIn(290196,p['jobs'])  # Not quietly truncating to one.
        self.assertEqual(p['job_groups'][290196],('44','45'))
        self.assertTrue(p['two_custodians_explicit_invites_beta'])
        fixed,report=project_native_staff_guests(
            GuestList(),298096,p,JOBS,Factory,'INVITED')
        self.assertTrue(report['applied'],report)
        self.assertTrue(report['two_custodians_explicit_invites_beta'])
        self.assertEqual([x.job_type.guid64 for x in fixed.guests],
                         [278223,290196,290196])
        self.assertEqual([x.sim_id for x in fixed.guests],[43,44,45])
        self.assertEqual(report['appointed'][290196],['44','45'])

    def test_two_custodians_replace_one_ea_original_without_duplicates(self):
        old=GuestList()
        old.add_guest_info(Guest(90,278223))
        old.add_guest_info(Guest(91,290196))
        fixed,report=project_native_staff_guests(
            old,298096,makeplan(multi=True),JOBS,Factory,'INVITED')
        self.assertTrue(report['applied'],report)
        self.assertEqual([x.sim_id for x in old.guests],[90,91])
        self.assertEqual([x.sim_id for x in fixed.guests],[43,44,45])
        self.assertEqual(len(fixed.guests),3)

    def test_two_janitors_are_all_or_nothing_when_one_is_unavailable(self):
        values={'custodians':('44','45')}
        infos={44:SimpleNamespace(age='ADULT',species='HUMAN'),
               45:SimpleNamespace(age='ADULT',species='DOG')}
        plan=load_native_staff_plan(Stored(values),Sims(infos),'HUMAN',
                                    ('ADULT',))
        self.assertNotIn(290196,plan['jobs'])
        self.assertNotIn(290196,plan['job_groups'])
        self.assertEqual(plan['blocked']['custodians'],'STAFF_NOT_ADULT_HUMAN')
        guest_list,report=project_native_staff_guests(
            GuestList(),298096,plan,JOBS,Factory,'INVITED')
        self.assertIsNone(guest_list)
        self.assertFalse(report['applied'])

    def test_duplicate_janitor_ids_never_become_two_guests(self):
        values={'custodians':('44','44')}
        infos={44:SimpleNamespace(age='ADULT',species='HUMAN')}
        plan=load_native_staff_plan(Stored(values),Sims(infos),'HUMAN',
                                    ('ADULT',))
        self.assertEqual(plan['blocked']['custodians'],
                         'DUPLICATED_SELECTED_STAFF')
        self.assertNotIn(290196,plan['job_groups'])

    def test_second_custodian_cannot_also_be_a_native_principal(self):
        p={'jobs':{278223:'45'},'job_groups':{
            278223:('45',),290196:('44','45')},'blocked':{}}
        fixed,report=project_native_staff_guests(
            GuestList(),298096,p,JOBS,Factory,'INVITED')
        self.assertIsNone(fixed)
        self.assertEqual(report['reason'],'DUPLICATED_APPOINTED_SIM')

    def test_cafeteria_three_names_stable_primary_and_two_explicitly_pending(self):
        values={'cafeteria':('46','45','47')}
        infos={n:SimpleNamespace(age='ADULT',species='HUMAN')
               for n in (45,46,47)}
        plan=load_native_staff_plan(Stored(values),Sims(infos),'HUMAN',
                                   ('ADULT',))
        self.assertEqual(plan['jobs'][278010],'46')
        self.assertEqual(plan['job_groups'][278010],('46',))
        self.assertEqual(plan['selected_roles']['cafeteria'],
                         ('46','45','47'))
        self.assertEqual(plan['pending_extra_staff']['cafeteria'],
                         ('45','47'))
        self.assertEqual(plan['cafeteria_service_mode'],
                         'ONE_STABLE_PRIMARY_PARTIAL_FALLBACK')
        self.assertEqual(plan['blocked']['cafeteria'],
                         'EXTRA_CAFETERIA_WORKERS_PENDING_NATIVE_STATIONS')
        guest_list,report=project_native_staff_guests(
            GuestList(),278011,plan,JOBS,Factory,'INVITED')
        self.assertTrue(report['applied'],report)
        self.assertEqual([(g.sim_id,g.job_type.guid64)
                          for g in guest_list.guests],[(46,278010)])
        self.assertEqual(projected_staff_ids(report),{278010:('46',)})

    def test_cafeteria_invalid_worker_does_not_silently_replace_selection(self):
        values={'cafeteria':('46','45','47')}
        infos={46:SimpleNamespace(age='ADULT',species='HUMAN'),
               45:SimpleNamespace(age='ADULT',species='DOG'),
               47:SimpleNamespace(age='ADULT',species='HUMAN')}
        plan=load_native_staff_plan(Stored(values),Sims(infos),'HUMAN',
                                   ('ADULT',))
        self.assertNotIn(278010,plan['job_groups'])
        self.assertEqual(plan['blocked']['cafeteria'],
                         'STAFF_NOT_ADULT_HUMAN')

    def test_teen_or_pet_invalid_without_any_modifications(self):
        r=Stored({'teacher1':('41',),'principal':('42',)})
        mgr=Sims({41:SimpleNamespace(age='TEEN',species='HUMAN'),
                  42:SimpleNamespace(age='ADULT',species='DOG')})
        p=load_native_staff_plan(r,mgr,'HUMAN',
                                 ('YOUNGADULT','ADULT','ELDER'))
        self.assertFalse(p['jobs'])
        self.assertEqual(set(p['blocked']),{'teacher1','principal'})

    def test_existing_student_cannot_become_staff(self):
        r=Stored({'teacher1':('100',)})
        mgr=Sims({100:SimpleNamespace(age='ADULT',species='HUMAN')})
        p=load_native_staff_plan(r,mgr,'HUMAN',('ADULT',),('100',))
        self.assertNotIn(277895,p['jobs'])

    def test_foreign_situation_not_changed(self):
        fixed,report=project_native_staff_guests(
            GuestList(),777111,makeplan(),JOBS,Factory,'INVITED')
        self.assertIsNone(fixed)
        self.assertEqual(report['reason'],'NOT_NATIVE_STAFF_SITUATION')

    def test_duplicate_original_teacher_refused(self):
        old=GuestList()
        old.add_guest_info(Guest(10,277895))
        old.add_guest_info(Guest(11,277895))
        fixed,report=project_native_staff_guests(
            old,298052,makeplan(),JOBS,Factory,'INVITED')
        self.assertIsNone(fixed)
        self.assertEqual(len(old.guests),2)
        self.assertEqual(report['reason'],'DUPLICATED_NATIVE_STAFF_JOB')

    def test_appointee_cannot_duplicate_a_retained_core_student(self):
        old=GuestList()
        old.add_guest_info(Guest(41,278965))
        old.add_guest_info(Guest(10,277895))
        fixed,report=project_native_staff_guests(
            old,298052,makeplan(),JOBS,Factory,'INVITED')
        self.assertIsNone(fixed)
        self.assertEqual(report['reason'],
                         'APPOINTED_SIM_ALREADY_HAS_OTHER_EA_JOB')
        self.assertEqual([x.sim_id for x in old.guests],[41,10])

    def test_appointee_cannot_duplicate_an_unmodified_native_staff_job(self):
        old=GuestList()
        old.add_guest_info(Guest(44,290196))
        # No requested custodians; principal ID 44 is already the janitor.
        plan={'jobs':{278223:'44'},'blocked':{}}
        fixed,report=project_native_staff_guests(
            old,298096,plan,JOBS,Factory,'INVITED')
        self.assertIsNone(fixed)
        self.assertEqual(report['reason'],
                         'APPOINTED_SIM_ALREADY_HAS_OTHER_EA_JOB')

    def test_duplicate_appointments_from_invalid_plan_are_refused(self):
        old=GuestList()
        invalid={'jobs':{277895:'41',278963:'41'},'blocked':{}}
        fixed,report=project_native_staff_guests(
            old,298052,invalid,JOBS,Factory,'INVITED')
        self.assertIsNone(fixed)
        self.assertEqual(report['reason'],'DUPLICATED_APPOINTED_SIM')

    def test_missing_native_tuning_does_not_guess(self):
        fixed,report=project_native_staff_guests(
            GuestList(),298052,makeplan(),{},Factory,'INVITED')
        self.assertIsNone(fixed)
        self.assertEqual(report['reason'],'NATIVE_STAFF_JOB_TUNING_UNAVAILABLE')

if __name__=='__main__':
    unittest.main()
