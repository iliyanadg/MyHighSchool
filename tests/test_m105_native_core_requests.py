"""M105 school-wide native Core role filter policy tests, no gameplay."""
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for sub in ('m105_day_controller','m93_core'):
    sys.path.insert(0,str(ROOT/'src'/sub))
from mhs105_atomic_school_roster import plan_school_day,CORE_JOBS,BASE_JOB,ALL_JOBS
from mhs105_native_core_requests import core_request_arguments,FILTER_TO_CORE_JOB

CLASSES=(tuple(str(n) for n in range(1,9)),
         tuple(str(n) for n in range(9,17)))
PLAYED=('1','9','10')
NPCS=tuple(s for group in CLASSES for s in group if s not in PLAYED)
PINS=dict(zip(CORE_JOBS,('2','3','4','11','12')))
LIVE={job:NPCS for job in ALL_JOBS}
LIVE[BASE_JOB]=tuple(s for s in NPCS if s!='2')
GOOD=plan_school_day(CLASSES,PLAYED,LIVE,PINS)
VERIFIED={'verified_school':True,'verified_save':True,
          'verified_day':True,'original_bouncer':True}

def check(fid,plan=GOOD,args=(),kwargs=None,method='matching',**flags):
    conditions=dict(VERIFIED)
    conditions.update(flags)
    return core_request_arguments(plan,method,fid,args,
                                  {} if kwargs is None else kwargs,
                                  **conditions)

class NativeCoreRequestTests(unittest.TestCase):
    def test_all_five_real_ea_role_filters_choose_distinct_enrolled_teens(self):
        result={}
        for fid,job in FILTER_TO_CORE_JOB.items():
            action,args,kwargs,why=check(
                fid,args=(1,'EA_FILTER',None,None,None,
                          'PRIORITY','OTHER','STATE',True,True))
            self.assertEqual(action,'constrain')
            self.assertEqual(kwargs,{})
            self.assertEqual(args[4],(int(PINS[job]),))
            self.assertEqual(args[5:8],('PRIORITY','OTHER','STATE'))
            self.assertEqual(args[8:10],(False,False))
            result[job]=args[4][0]
        self.assertEqual(len(set(result.values())),5)
        self.assertEqual(set(result.values()),set(map(int,PINS.values())))

    def test_ea_callback_and_other_kwargs_unchanged(self):
        a=('callback_event','sim_filter')
        action,args,kw,_=check(276592,args=a,
            kwargs={'callback':'EA_CALLBACK','allow_yielding':False,
                    'priority':8,'custom_option':True})
        self.assertEqual(action,'constrain')
        self.assertEqual(args,a)
        self.assertEqual(kw['callback'],'EA_CALLBACK')
        self.assertEqual(kw['allow_yielding'],False)
        self.assertEqual(kw['priority'],8)
        self.assertIs(kw['custom_option'],True)
        self.assertEqual(kw['sim_constraints'],(2,))

    def test_staff_base_other_request_types_preserved(self):
        for fid in (280516,296396,300742,300744,303765,999999):
            action,a,kw,_=check(fid,args=(3,'EA'),
                kwargs={'priority':13})
            self.assertEqual(action,'preserve')
            self.assertEqual(kw,{'priority':13})
        self.assertEqual(check(276592,method='filter')[0],'preserve')

    def test_no_override_outside_verified_original_ea_bouncer(self):
        for flag in VERIFIED:
            action,_,_,_=check(276592,**{flag:False})
            self.assertEqual(action,'preserve')

    def test_missing_manual_confirmation_prohibits_core_override(self):
        suggestion=plan_school_day(CLASSES,PLAYED,LIVE,
                                    propose_missing_roles=True)
        self.assertEqual(check(276592,plan=suggestion)[0],'block')
        self.assertEqual(check(276592,plan=None)[0],'block')

    def test_do_not_overwrite_a_native_ea_explicit_target(self):
        action,args,kw,_=check(276592,args=(1,'EA',None,None,(555,)))
        self.assertEqual(action,'block')
        self.assertEqual(args[4],(555,))
        action,args,kw,_=check(
            276592,kwargs={'sim_constraints':(555,)})
        self.assertEqual(action,'block')
        self.assertEqual(kw['sim_constraints'],(555,))

    def test_changed_duplicate_or_partial_roster_is_blocked(self):
        bad=dict(GOOD)
        bad['core_role_assignments']=tuple(
            (j,'2') for j in CORE_JOBS)
        self.assertEqual(check(276592,plan=bad)[0],'block')
        bad=dict(GOOD)
        bad['normal_base_ids']=('3',)*8
        self.assertEqual(check(276592,plan=bad)[0],'block')
        bad=dict(GOOD)
        bad['base_invites_needed']=13
        self.assertEqual(check(276592,plan=bad)[0],'block')

    def test_never_claims_ea_binding_based_on_arguments_alone(self):
        self.assertFalse(GOOD['actual_ea_role_bindings_verified'])
        self.assertFalse(GOOD['core_roles_reserved_before_ea'])
        self.assertFalse(GOOD['attendance_verified'])
        self.assertEqual(check(276592)[0],'constrain')

if __name__=='__main__':
    unittest.main()
