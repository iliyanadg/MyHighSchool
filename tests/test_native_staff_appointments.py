"""Exact native EA staffing and no invented additional job slots."""
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src/classroom_control'))
from mhs_native_staff_appointments import (
    ROLE_JOBS, load_native_staff_plan, project_native_staff_guests)

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

    def test_multi_workers_never_silently_select_only_one(self):
        p=makeplan(multi=True)
        self.assertNotIn(290196,p['jobs'])
        self.assertIn('custodians',p['blocked'])
        fixed,report=project_native_staff_guests(
            GuestList(),298096,p,JOBS,Factory,'INVITED')
        self.assertEqual([x.sim_id for x in fixed.guests],[43])
        self.assertIn('custodians',report['blocked'])

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

    def test_missing_native_tuning_does_not_guess(self):
        fixed,report=project_native_staff_guests(
            GuestList(),298052,makeplan(),{},Factory,'INVITED')
        self.assertIsNone(fixed)
        self.assertEqual(report['reason'],'NATIVE_STAFF_JOB_TUNING_UNAVAILABLE')

if __name__=='__main__':
    unittest.main()
