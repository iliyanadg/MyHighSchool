"""M113 two-phase ORIGINAL EA school-count bootstrap (OFFLINE ONLY).

Fake EA methods and simulated gates do not authorize real The Sims hooks.
"""
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'/'m108_native_roster'))
sys.path.insert(0,str(ROOT/'src'/'m109_activation'))
sys.path.insert(0,str(ROOT/'src'/'m113_controller'))

from mhs113_early_school_entry import (
    M113EarlySchoolEntry, LATE_STAGES, _home_plan,
)
from mhs109_atomic_activation import REQUIRED_RUNTIME_EVIDENCE
from mhs108_native_invitation import (
    CORE_JOBS, SchoolNativeGuestSession,
)
from tests.test_m108_native_invitation import (
    CLASSES, PLAYABLE, CORE, EAInfo, JOBS, EAList,
)
from tests.test_m108_native_base_count import fake_ea_schedule
from tests.test_m108_native_precreate import (
    manager as fake_manager, all_proof as precreate_gates,
    Situation as BaseSituation, CoreSituation,
)
from mhs108_native_precreate import install as install_precreate


def rig(changes=None, failure=None, use_real_guest_adapter=True):
    """Return isolated fake EA environment with explicit synthetic proofs."""
    Day,Main,Venue,Other,base,staff=fake_ea_schedule((3,3))
    Day.__module__='venues.weekly_schedule_zone_director'
    context={
        'source':'EA_RUNTIME_OBSERVATION',  # SYNTHETIC FIXTURE ONLY
        'save_slot':'11', 'sim_day':12,
        'school_zone':'777','zone_id':'777',
        'schedule_guid':277657,
        'school_verified':True,
        'native_weekly_school_origin_verified':True,
        'before_school_schedule_verified':True,
        'ea_schedule_not_started':True,
        'native_origin_verified':True,
        'original_ea_school_guest_takeover_verified':True,
    }
    context.update({name:True for name in REQUIRED_RUNTIME_EVIDENCE})
    if changes:
        context.update(changes)
    state={'order':[],'undone':[],'guest_manager':None,
           'guest_undo':None,'session':None,'provenance_checks':0,
           'derive_schedule_from_ea':False}

    def ctx_provider(cls,data,resolver):
        state['provenance_checks']+=1
        result=dict(context)
        if state['derive_schedule_from_ea']:
            result['schedule_guid']=getattr(cls,'guid64',None)
        return result

    def session_factory(manifest):
        sess=SchoolNativeGuestSession(manifest,EAInfo,'INVITED',JOBS)
        state['session']=sess
        return sess

    def factory(session,trusted):
        graph={}
        for name in LATE_STAGES:
            def install(manifest,evidence,_name=name):
                state['order'].append(_name)
                if _name=='native_precreate' and use_real_guest_adapter:
                    Manager=fake_manager()
                    undo=install_precreate(
                        Manager,session,lambda:dict(trusted),
                        precreate_gates())
                    if undo is None:
                        return False
                    state['guest_undo']=undo
                    state['guest_manager']=Manager
                if failure==_name:
                    raise RuntimeError('partial stage failure in synthetic EA')
                return True
            def restore(_name=name):
                state['undone'].append(_name)
                if _name=='native_precreate' and use_real_guest_adapter:
                    if state['guest_undo'] is not None:
                        return state['guest_undo']()
                return True
            graph[name]={'install':install,'restore':restore}
        return graph

    controller=M113EarlySchoolEntry(
        CLASSES,PLAYABLE,CORE,11,12,111,
        ctx_provider,session_factory,factory)
    return controller, (Day,Main,Venue,Other,base,staff),state


class EarlySchoolHandoffTests(unittest.TestCase):
    def test_home_plan_freezes_roster_without_assigning_special_roles(self):
        p=_home_plan(CLASSES,PLAYABLE,CORE,11,12,111)
        self.assertIsNotNone(p)
        self.assertEqual(len(p['classes'][0]),8)
        self.assertEqual(len(p['classes'][1]),8)
        self.assertEqual(len(p['core_assignments']),5)
        self.assertEqual(set(job for job,_ in p['core_assignments']),
                         set(CORE_JOBS))
        self.assertIsNone(_home_plan(CLASSES,PLAYABLE,{},11,12,111))
        bad={k:('1' if k==CORE_JOBS[0] else v)
             for k,v in CORE.items()}
        self.assertIsNone(_home_plan(CLASSES,PLAYABLE,bad,11,12,111))

    def test_home_arms_one_reversible_dormant_hook_no_npc_change(self):
        c,(Day,Main,Venue,Other,base,staff),state=rig()
        before=Day.__dict__['get_long_term_situation_count']
        self.assertTrue(c.arm_at_home(Day))
        self.assertEqual(c.state,'WAITING_FOR_EA_SCHOOL')
        self.assertEqual(state['order'],[])
        self.assertEqual(Main.calls,0)
        self.assertEqual(Other.get_long_term_situation_count(base,None),
                         (3,3))
        self.assertEqual(state['provenance_checks'],0)
        self.assertEqual(Main.get_long_term_situation_count(staff,None),
                         (3,3))
        self.assertEqual(state['order'],[])
        self.assertTrue(c.stop())
        self.assertIs(Day.__dict__['get_long_term_situation_count'],before)

    def test_first_real_school_count_latches_zone_and_installs_before_return(self):
        c,(Day,Main,Venue,Other,base,staff),state=rig()
        self.assertTrue(c.arm_at_home(Day))
        try:
            self.assertEqual(Main.get_long_term_situation_count(base,None),
                             (8,8))
            self.assertEqual(Main.calls,1)
            self.assertEqual(c.state,'ACTIVE_LATE_STAGES')
            self.assertEqual(c.school_zone,'777')
            self.assertEqual(c.original_count,(3,3))
            self.assertEqual(tuple(state['order']),LATE_STAGES)
            self.assertEqual(c.snapshot()['late_stages_installed'],
                             LATE_STAGES)
            self.assertFalse(c.snapshot()['attendance_16_verified'])
            self.assertFalse(c.snapshot()['game_live_provider_implemented'])
            # The concrete original EA precreate hook is now installed in
            # this MOCK environment. One vanilla Base is replaced in place.
            Manager=state['guest_manager']
            obj=Manager()
            old=EAList()
            created=obj.create_situation(BaseSituation(),guest_list=old)
            self.assertEqual(created,101)
            self.assertEqual([g.sim_id for g in
                              obj.calls[-1][1].guest_info_gen()],[5])
            self.assertEqual(list(old.guest_info_gen()),[])
            self.assertFalse(c.session.snapshot()['attendance_verified'])
        finally:
            self.assertTrue(c.stop())
        self.assertEqual(c.state,'STOPPED')
        self.assertEqual(tuple(state['undone']),tuple(reversed(LATE_STAGES)))

    def test_bad_zone_never_installs_late_stage_or_changed_count(self):
        for changes in (
                {'school_zone':'111','zone_id':'111'},
                {'school_zone':'777','zone_id':'999'},
                {'save_slot':'12'}, {'sim_day':13},
                {'school_verified':False},
                {'native_weekly_school_origin_verified':False},
                {'ea_schedule_not_started':False},
                {'source':'HAND_TYPED_GUESS'},
                {'original_ea_guestlist_and_school_filters_verified':False}):
            c,(Day,Main,Venue,Other,base,staff),state=rig(changes)
            self.assertTrue(c.arm_at_home(Day))
            try:
                self.assertEqual(Main.get_long_term_situation_count(base,None),
                                 (3,3),msg=str(changes))
                self.assertEqual(c.state,'WAITING_FOR_EA_SCHOOL')
                self.assertFalse(state['order'])
            finally:
                self.assertTrue(c.stop())

    def test_non_original_count_has_no_bypass_or_mutation(self):
        Day,Main,Venue,Other,base,staff=fake_ea_schedule((4,4))
        Day.__module__='venues.weekly_schedule_zone_director'
        c,(D,_,_,_,_,_),state=rig()
        self.assertTrue(c.arm_at_home(Day))
        try:
            self.assertEqual(Main.get_long_term_situation_count(base,None),
                             (4,4))
            self.assertEqual(state['provenance_checks'],0)
        finally:
            self.assertTrue(c.stop())

    def test_installer_exception_rolls_back_all_stages_no_ea_count_override(self):
        c,(Day,Main,Venue,Other,base,staff),state=rig(
            failure='no_show_guard')
        prior=Day.__dict__['get_long_term_situation_count']
        self.assertTrue(c.arm_at_home(Day))
        self.assertEqual(Main.get_long_term_situation_count(base,None),(3,3))
        self.assertEqual(c.state,'BLOCKED')
        self.assertEqual(state['order'][:3],
                         list(LATE_STAGES[:3]))
        self.assertEqual(state['undone'],
                         list(reversed(LATE_STAGES[:3])))
        self.assertFalse(c.snapshot()['attendance_16_verified'])
        self.assertTrue(c.stop())
        self.assertIs(Day.__dict__['get_long_term_situation_count'],prior)

    def test_third_party_descriptor_conflict_is_not_overwritten(self):
        c,(Day,Main,Venue,Other,base,staff),state=rig()
        self.assertTrue(c.arm_at_home(Day))
        @classmethod
        def another(cls,data,resolver):
            return (17,17)
        Day.get_long_term_situation_count=another
        self.assertFalse(c.stop())
        self.assertEqual(c.state,'RESTORE_CONFLICT')
        self.assertIs(Day.__dict__['get_long_term_situation_count'],another)

    def test_same_day_duplicate_activation_cannot_reinvite(self):
        c,(Day,Main,Venue,Other,base,staff),state=rig()
        self.assertTrue(c.arm_at_home(Day))
        try:
            self.assertEqual(Main.get_long_term_situation_count(base,None),
                             (8,8))
            self.assertEqual(Main.get_long_term_situation_count(base,None),
                             (8,8))
            self.assertEqual(state['order'],list(LATE_STAGES))
            self.assertEqual(state['provenance_checks'],2)
        finally:
            self.assertTrue(c.stop())

    def test_second_original_school_schedule_is_covered_before_invites(self):
        c,(Day,Main,Venue,Other,base,staff),state=rig()
        state['derive_schedule_from_ea']=True
        self.assertTrue(c.arm_at_home(Day))
        try:
            self.assertEqual(Main.get_long_term_situation_count(base,None),
                             (8,8))
            self.assertEqual(Venue.get_long_term_situation_count(base,None),
                             (8,8))
            self.assertEqual(len(state['order']),len(LATE_STAGES))
            # Once Base student invitations begin, never apply an
            # additional late count override to an active schedule.
            Manager=state['guest_manager']
            Manager().create_situation(BaseSituation(),guest_list=EAList())
            self.assertEqual(Venue.get_long_term_situation_count(base,None),
                             (3,3))
        finally:
            self.assertTrue(c.stop())

    def test_unrecognised_EA_owner_or_existing_wrapper_cannot_arm(self):
        c,(Day,Main,Venue,Other,base,staff),state=rig()
        Day.__module__='thirdparty'
        self.assertFalse(c.arm_at_home(Day))
        Day.__module__='venues.weekly_schedule_zone_director'
        fn=Day.__dict__['get_long_term_situation_count'].__func__
        fn._mhs108_count_hook=True
        try:
            self.assertFalse(c.arm_at_home(Day))
        finally:
            del fn._mhs108_count_hook

    def test_no_repeated_home_arm_and_no_double_stop(self):
        c,(Day,Main,Venue,Other,base,staff),state=rig()
        self.assertTrue(c.arm_at_home(Day))
        self.assertFalse(c.arm_at_home(Day))
        self.assertTrue(c.stop())
        self.assertFalse(c.stop())


if __name__=='__main__':
    unittest.main()
