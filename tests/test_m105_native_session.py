"""M105 one native EA school session: 5 pinned Core + 8 Base request guard."""
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for loc in ('m105_day_controller','m93_core','m104_native'):
    sys.path.insert(0,str(ROOT/'src'/loc))
from mhs105_atomic_school_roster import plan_school_day,ALL_JOBS,CORE_JOBS
from mhs105_native_session import SchoolSession,BASE_FILTER,CORE_FILTERS
from mhs105_native_core_requests import FILTER_TO_CORE_JOB
GROUPS=(tuple(str(i) for i in range(1,9)),
        tuple(str(i) for i in range(9,17)))
PLAYED=('1','9','10')
NPCS=tuple(sid for grp in GROUPS for sid in grp if sid not in PLAYED)
PINS=dict(zip(CORE_JOBS,('2','3','4','11','12')))
ELIG={job:tuple(NPCS) for job in ALL_JOBS}
PLAN=plan_school_day(GROUPS,PLAYED,ELIG,PINS)

def call(session,guid,day=24,zone='401',slot='11',bouncer=True,
         args=(1,'EA'),school_verified=True):
    return session.constrain('matching',guid,args,{},slot,day,zone,bouncer,
                             school_verified=school_verified)

class SchoolSessionTests(unittest.TestCase):
    def setUp(self):
        self.session=SchoolSession(PLAN,'11',24,'100')
    def test_exact_five_core_requests_and_eight_unique_base_originals(self):
        seen={}
        for fid,job in FILTER_TO_CORE_JOB.items():
            action,args,options=call(self.session,fid)
            self.assertEqual(action,'constrain')
            seen[job]=str(options['sim_constraints'][0])
        self.assertEqual(seen,PINS)
        bases=[]
        for i in range(8):
            action,args,options=call(self.session,BASE_FILTER)
            self.assertEqual(action,'constrain')
            bases.append(str(options['sim_constraints'][0]))
        self.assertEqual(tuple(bases),PLAN['normal_base_ids'])
        self.assertEqual(set(bases)&set(seen.values()),set())
        self.assertEqual(set(bases)|set(seen.values())|set(PLAYED),
                         set(GROUPS[0]+GROUPS[1]))
        stats=self.session.evidence()
        self.assertEqual(stats['core_requests_constrained'],5)
        self.assertEqual(stats['base_requests_constrained'],8)
        self.assertFalse(stats['ea_core_bindings_verified'])
        self.assertFalse(stats['base_schedule_count_overridden'])
        self.assertFalse(stats['attendance_verified'])
    def test_never_reapply_role_or_ninth_base_request(self):
        self.assertEqual(call(self.session,276592)[0],'constrain')
        self.assertEqual(call(self.session,276592)[0],'preserve')
        for _ in range(8):
            self.assertEqual(call(self.session,BASE_FILTER)[0],'constrain')
        self.assertEqual(call(self.session,BASE_FILTER)[0],'preserve')
    def test_unknown_school_and_other_mod_filters_never_touched(self):
        for guid in (999999,280457,2805160,300742):
            self.assertEqual(call(self.session,guid)[0],'preserve')
        self.assertEqual(self.session.evidence()['core_requests_observed'],0)
        self.assertEqual(self.session.evidence()['base_requests_observed'],0)
    def test_mismatched_save_day_zone_and_non_bouncer_are_untouched(self):
        for args in ({'slot':'12'},{'day':25},{'zone':'100'},
                     {'zone':None},{'bouncer':False},
                     {'school_verified':False}):
            self.assertEqual(call(self.session,276592,**args)[0],'preserve')
        self.assertEqual(call(self.session,276592)[0],'constrain')
        self.assertEqual(call(self.session,276596,zone='990')[0],'preserve')
        self.assertEqual(self.session.school_zone,'401')
    def test_no_override_ea_original_explicit_target(self):
        action,args,options=call(self.session,276592,
                                 args=(1,'EA',None,None,(999,)))
        self.assertEqual(action,'preserve')
        self.assertEqual(args[4],(999,))
        self.assertEqual(self.session.core_request_outcomes[278965]['decision'],
                         'block')
    def test_cancelling_blocks_new_school_requests(self):
        self.session.cancel()
        self.assertEqual(call(self.session,276592)[0],'preserve')
        self.assertEqual(call(self.session,BASE_FILTER)[0],'preserve')
    def test_unconfirmed_partial_or_invalid_day_plan_never_installs(self):
        bad=dict(PLAN,status='PROPOSAL_NEEDS_MANUAL_CONFIRMATION')
        with self.assertRaises(ValueError):
            SchoolSession(bad,'11',24,'100')
        with self.assertRaises(ValueError):
            SchoolSession(PLAN,'11','24','100')
        with self.assertRaises(ValueError):
            SchoolSession(PLAN,'11',24,'unavailable')
    def test_isolated_core_filters_are_exact_five_expected(self):
        self.assertEqual(set(CORE_FILTERS),
                         set((276592,276596,276594,276595,303766)))
    def test_no_new_game_situations_ever_created(self):
        source=(ROOT/'src'/'m105_day_controller'/
                'mhs105_native_session.py').read_text()
        self.assertNotIn('create_situation(',source)
        self.assertNotIn('spawn_sim(',source)
        self.assertNotIn('SituationGuestList',source)

if __name__=='__main__':
    unittest.main()
