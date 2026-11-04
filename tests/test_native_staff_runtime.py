"""Native staff Bouncer eligibility: exact selected Sim, job and situation.

This exercises the real extracted classroom controller method, rather than
only the pure guest-list projection in test_native_staff_appointments.
"""
import unittest
from types import SimpleNamespace
from tests.test_classroom_runtime import RuntimeTests

class StaffNativeRuntimeTests(unittest.TestCase):
    def make(self):
        runtime,_,_,_=RuntimeTests().load_controller()
        runtime.active=True
        runtime.school_ready=True
        runtime.bound_zone=20
        runtime.staff_plan={'jobs':{277895:'41'},'blocked':{}}
        runtime.staff_pending=298052
        fake_age=SimpleNamespace(TEEN='TEEN',YOUNGADULT='YA',
                                 ADULT='ADULT',ELDER='ELDER')
        fake_species=SimpleNamespace(HUMAN='HUMAN')
        selected=SimpleNamespace(age='ADULT',species='HUMAN',
                                 is_selectable=False)
        sims={41:selected,42:SimpleNamespace(age='TEEN',
                           species='HUMAN',is_selectable=False)}
        env=runtime.eligible.__func__.__globals__
        env.update({
            'ROLE_JOBS':{
                298052:(('teacher1',277895),('teacher2',278963)),
                298096:(('principal',278223),('custodians',290196)),
                278011:(('cafeteria',278010),)},
            'CORE_SITUATION':298052,
            'BASE_SITUATION':277733,
            'BASE_JOB':277894,
            'CORE_JOBS':(278965,278966,278967,278968,303765),
            'PREP_JOBS':{},'LESSON_JOBS':{},
            'zone_schedule':lambda:(20,277657),
            'services':SimpleNamespace(sim_info_manager=lambda:
                         SimpleNamespace(get=lambda sid:sims.get(sid))),
            'Age':fake_age,'Species':fake_species})
        native_filter=object()
        job=SimpleNamespace(guid64=277895,filter=native_filter)
        request=SimpleNamespace(
            _requested_sim_id=41,_situation=SimpleNamespace(guid64=298052),
            _job_type=job,_sim_filter=native_filter,
            _constrained_sim_ids={41},_for_persisted_sim=False,
            _continue_if_constraints_fail=False)
        return runtime,request,sims

    def test_selected_human_adult_in_exact_ea_job_eligible(self):
        runtime,request,_=self.make()
        self.assertTrue(runtime.eligible(request))
        runtime.staff_pending=None
        runtime.staff_created[298052]=12345
        self.assertTrue(runtime.eligible(request))

    def test_wrong_sim_job_venue_or_zone_cannot_get_blank_filter(self):
        runtime,request,_=self.make()
        request._requested_sim_id=42
        request._constrained_sim_ids={42}
        self.assertFalse(runtime.eligible(request))
        request._requested_sim_id=41
        request._constrained_sim_ids={41}
        request._job_type.guid64=278963
        self.assertFalse(runtime.eligible(request))
        request._job_type.guid64=277895
        request._situation.guid64=298096
        self.assertFalse(runtime.eligible(request))
        request._situation.guid64=298052
        runtime.bound_zone=21
        self.assertFalse(runtime.eligible(request))

    def test_pet_or_minor_does_not_receive_staff_exception(self):
        runtime,request,sims=self.make()
        sims[41].species='DOG'
        self.assertFalse(runtime.eligible(request))
        sims[41].species='HUMAN'
        sims[41].age='TEEN'
        self.assertFalse(runtime.eligible(request))

    def test_only_exact_nonpersistent_one_sim_request(self):
        runtime,request,_=self.make()
        request._constrained_sim_ids={41,42}
        self.assertFalse(runtime.eligible(request))
        request._constrained_sim_ids={41}
        request._for_persisted_sim=True
        self.assertFalse(runtime.eligible(request))


class StaffDailyPersistenceTests(unittest.TestCase):
    def test_staff_registry_is_snapshotted_once_per_school_day(self):
        runtime,_,_,groups=RuntimeTests().load_controller()
        selected={'id':'41'}
        calls=[]
        def staff_loader(slot,active_groups):
            calls.append((slot,active_groups))
            return {'jobs':{277895:selected['id']},'blocked':{}}
        runtime.staff_plan_loader=staff_loader
        runtime.begin_school_day(('1',1))
        self.assertEqual(runtime.staff_plan['jobs'][277895],'41')
        runtime.staff_created[298052]=999
        runtime.staff_filter_hits=3
        selected['id']='48'
        # A player changing the menu during school does not change the
        # active invitations while today's EA situation is in progress.
        runtime.begin_school_day(('1',1))
        self.assertEqual(runtime.staff_plan['jobs'][277895],'41')
        self.assertEqual(runtime.staff_created,{298052:999})
        self.assertEqual(len(calls),1)
        # The next school day loads the registry again, without reusing the
        # previous day's Bouncer receipts or stale Sim IDs.
        runtime.begin_school_day(('1',2))
        self.assertEqual(runtime.staff_plan['jobs'][277895],'48')
        self.assertEqual(runtime.staff_created,{})
        self.assertEqual(runtime.staff_filter_hits,0)
        self.assertEqual(runtime.lesson_classes,groups)
        self.assertEqual(len(calls),2)

    def test_invalid_new_day_staff_registry_does_not_touch_enrollment(self):
        runtime,_,_,groups=RuntimeTests().load_controller()
        def bad_loader(slot,active_groups):
            raise ValueError('BAD_STAFF_REGISTRY')
        runtime.staff_plan_loader=bad_loader
        self.assertTrue(runtime.begin_school_day(('1',4)))
        self.assertEqual(runtime.staff_plan['jobs'],{})
        self.assertEqual(runtime.staff_plan['blocked'],
                         {'all':'STAFF_PLAN_ValueError'})
        self.assertEqual(runtime.lesson_classes,groups)
        self.assertTrue(runtime.school_ready)


if __name__=='__main__':
    unittest.main()
