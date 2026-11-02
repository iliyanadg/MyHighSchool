"""M106 native filter session tests -- no EA runtime or traits touched."""
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for folder in ('m93_core','m105_day_controller','m106_roster_first','m104_native'):
    sys.path.insert(0,str(ROOT/'src'/folder))
from mhs106_roster_first_policy import propose_roster_first
from mhs106_school_session import M106Session
from mhs105_atomic_school_roster import BASE_JOB

CLASSES=(tuple(str(i) for i in range(1,9)),tuple(str(i) for i in range(9,17)))
PLAYED=('1','9','10')
NPC=tuple(sid for g in CLASSES for sid in g if sid not in PLAYED)
ELIGIBLE={BASE_JOB:tuple(sid for sid in NPC if sid!='16'),
          278965:('2','16'),278966:('3',),278967:('4',),
          278968:('11',),303765:()}
PREF={278965:'16',278966:'3',278967:'4',278968:'11',303765:'12'}
PLAN=propose_roster_first(CLASSES,PLAYED,ELIGIBLE,PREF)
CORE_FILTERS=(276592,276596,276594,276595,303766)


class NativeSessionTests(unittest.TestCase):
    def session(self):
        return M106Session(PLAN,11,28,101)

    def run_one(self,session,guid,count=1,zone='202',school=True,
                day=28,slot=11,bouncer=True,args=None,kwargs=None):
        if args is None:
            args=(count,'CORE_TUNING' if guid!=280516 else 'BASE_TUNING')
        return session.decide(
            'matching',guid,args,kwargs or {},'BASE_TUNING',
            slot=slot,day=day,zone=zone,bouncer=bouncer,school=school)

    def test_entire_5_core_plus_8_base_requests_do_not_overlap(self):
        s=self.session()
        targets=[]
        for guid in CORE_FILTERS:
            action,args,kwargs=self.run_one(s,guid)
            self.assertEqual(action,'CONSTRAIN')
            targets.extend(kwargs['sim_constraints'])
            if guid==303766:
                self.assertEqual(args[1],'BASE_TUNING')
            else:
                self.assertEqual(args[1],'CORE_TUNING')
            self.assertFalse(kwargs['continue_if_constraints_fail'])
            self.assertFalse(kwargs['conform_if_constraints_fail'])
        for count in (3,2,3):
            action,args,kwargs=self.run_one(s,280516,count)
            self.assertEqual(action,'CONSTRAIN')
            self.assertEqual(len(kwargs['sim_constraints']),count)
            targets.extend(kwargs['sim_constraints'])
        proof=s.evidence()
        self.assertEqual(proof['core_requests_constrained'],5)
        self.assertEqual(proof['base_targets_constrained'],8)
        self.assertTrue(proof['all_thirteen_native_targets_requested'])
        self.assertEqual(len(set(targets)),13)
        self.assertEqual(set(targets),set(int(sid) for sid in NPC))
        self.assertFalse(proof['actual_attendance_verified'])
        self.assertFalse(proof['actual_core_role_binding_verified'])
        self.assertFalse(proof['ea_base_schedule_count_changed'])

    def test_duplicate_core_and_overflow_base_not_rewritten(self):
        s=self.session()
        self.assertEqual(self.run_one(s,276592)[0],'CONSTRAIN')
        self.assertEqual(self.run_one(s,276592)[0],'PRESERVE')
        self.assertEqual(self.run_one(s,280516,9)[0],'PRESERVE')
        self.assertEqual(s.evidence()['core_requests_bypassed'],0)
        self.assertGreater(s.evidence()['base_requests_bypassed'],0)
        self.assertFalse(s.evidence()['all_thirteen_native_targets_requested'])

    def test_never_intercept_unrelated_staff_or_unverified_context(self):
        for scope in (
            {'school':False},{'bouncer':False},{'day':29},
            {'slot':12},{'zone':'101'},{'zone':None},
        ):
            s=self.session()
            self.assertEqual(self.run_one(s,303766,**scope)[0],'PRESERVE')
            self.assertEqual(s.evidence()['core_requests_observed'],0)
        self.assertEqual(self.run_one(self.session(),280457)[0],'PRESERVE')

    def test_explicit_original_ea_target_is_preserved(self):
        s=self.session()
        response=self.run_one(s,303766,kwargs={'sim_constraints':(999,)})
        self.assertEqual(response[0],'PRESERVE')
        self.assertEqual(response[2],{'sim_constraints':(999,)})
        self.assertFalse(s.evidence()['all_thirteen_native_targets_requested'])

    def test_cancel_prevents_any_further_interception(self):
        s=self.session()
        s.off()
        self.assertEqual(self.run_one(s,303766)[0],'PRESERVE')

    def test_malformed_plans_are_not_allowed(self):
        bad=dict(PLAN,all_16=())
        with self.assertRaises(ValueError):
            M106Session(bad,11,28,101)


if __name__=='__main__':
    unittest.main()
