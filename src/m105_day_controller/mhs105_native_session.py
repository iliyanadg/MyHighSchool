"""M105 early-loaded school NPC selection session; never creates situations.

One coherent instance carries a single PRE-TRAVEL six-filter verified plan
into the school-zone Bouncer's original matching requests. It reserves the
five user-confirmed Core IDs and eight Base IDs. There is NO global role
override, no arbitrary Sim spawning, no direct school situations.

This class is independent of Sims APIs: runtime wrapper must independently
prove save, day, zone, native Bouncer origin and live Sim eligibility. It
does NOT claim actual role binding or on-lot attendance from a filter call.

Do not use the Base count hook before the five early reservations, zone
capacity, and eight-per-class routing are all proven in game.
"""
from mhs105_atomic_school_roster import CORE_JOBS,BASE_JOB
from mhs105_native_core_requests import (
    FILTER_TO_CORE_JOB,core_request_arguments)
from mhs104_native_policy import native_base_arguments

BASE_FILTER=280516
CORE_FILTERS=frozenset(FILTER_TO_CORE_JOB)
EXPECTED_SCHOOL_FILTERS=frozenset(CORE_FILTERS|(frozenset((BASE_FILTER,))))

class SchoolSession(object):
    """Stateful, opt-in dispatch for exactly one save/zone/day."""

    def __init__(self,plan,save_slot,sim_day,home_zone):
        if not isinstance(plan,dict) or plan.get('status')!='PREPARED_NOT_EA_BOUND':
            raise ValueError('M105 plan not prepared')
        if not plan.get('all_core_appointments_confirmed') is True:
            raise ValueError('five early role choices not confirmed')
        if (plan.get('base_invites_needed')!=8
                or len(plan.get('all_16',()))!=16
                or len(plan.get('core_role_assignments',()))!=5):
            raise ValueError('M105 complete school day missing')
        if not str(save_slot).isdigit() or type(sim_day) is not int:
            raise ValueError('unverified save/day')
        if not str(home_zone).isdigit():
            raise ValueError('invalid home zone')
        self.plan=plan
        self.save_slot=str(save_slot)
        self.sim_day=sim_day
        self.home_zone=str(home_zone)
        self.school_zone=None
        self.attempted_core=set()
        self.attempted_base=0
        self.core_request_outcomes={}
        self.base_request_outcomes=[]
        self.invalidated=False

    def _scope(self,slot,day,zone,bouncer):
        if self.invalidated:
            return False
        if (str(slot)!=self.save_slot or type(day) is not int
                or day!=self.sim_day or zone is None
                or str(zone)==self.home_zone or bouncer is not True):
            return False
        if self.school_zone is not None and str(zone)!=self.school_zone:
            return False
        return True

    def constrain(self,method,filter_guid,args,kwargs,
                  slot,day,zone,bouncer):
        """Decide one genuine EA matching call.

        Outcome includes exact arguments and an explicit evidence state.
        If the incoming EA request already targeted a different Sim,
        preserve EA's arguments; do not claim a successful reservation.
        """
        unchanged=('preserve',tuple(args),dict(kwargs))
        if method!='matching' or filter_guid not in EXPECTED_SCHOOL_FILTERS:
            return unchanged
        if not self._scope(slot,day,zone,bouncer):
            return unchanged
        if filter_guid in CORE_FILTERS:
            job=FILTER_TO_CORE_JOB[filter_guid]
            if job in self.attempted_core:
                return unchanged
            action,newargs,newkwargs,reason=core_request_arguments(
                self.plan,method,filter_guid,args,kwargs,
                verified_school=True,verified_save=True,
                verified_day=True,original_bouncer=True)
            self.attempted_core.add(job)
            self.core_request_outcomes[job]={
                'decision':action,'reason':reason,
                'actual_ea_role_binding_verified':False}
            if action!='constrain':
                return unchanged
        else:
            if self.attempted_base>=8:
                return unchanged
            # One specific Base NPC per original EA request. The IDs are
            # stable in registration order, never replaced randomly.
            target=self.plan['normal_base_ids'][self.attempted_base]
            action,newargs,newkwargs,reason=native_base_arguments(
                method,args,kwargs,BASE_FILTER,(int(target),))
            self.attempted_base+=1
            self.base_request_outcomes.append({
                'sim_id':target,'decision':action,'reason':reason,
                'actual_ea_school_membership_verified':False})
            if action!='constrain':
                return unchanged
        if self.school_zone is None:
            self.school_zone=str(zone)
        return ('constrain',newargs,newkwargs)

    def evidence(self):
        return {
            'status':'SESSION_INSTALLED_NO_ATTENDANCE_PROOF',
            'save_slot':self.save_slot,
            'core_requests_observed':len(self.attempted_core),
            'core_requests_constrained':sum(
                row['decision']=='constrain'
                for row in self.core_request_outcomes.values()),
            'base_requests_observed':self.attempted_base,
            'base_requests_constrained':sum(
                row['decision']=='constrain'
                for row in self.base_request_outcomes),
            'school_zone':self.school_zone,
            'ea_core_bindings_verified':False,
            'attendance_verified':False,
            'eight_per_class_verified':False,
            'base_schedule_count_overridden':False,
        }

    def cancel(self):
        self.invalidated=True
