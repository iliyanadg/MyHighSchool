"""Pure opt-in M106 native request session, with no EA imports.

A prepared selection is NOT proof that the Bouncer spawned its requested Sim.
EA's default count of six Base situations is NOT changed by this session.
All requests outside the verified EP12 Bouncer/zone/save/day are unchanged.
"""
from mhs106_bridge_arguments import (
    propose_school_only_filter_arguments,CORE_FILTER_TO_JOB,BASE_FILTER_GUID)
from mhs104_native_policy import native_base_arguments


def _request_count(args,kwargs):
    if args and 'number_of_sims_to_find' in kwargs:
        return None
    requested=args[0] if args else kwargs.get('number_of_sims_to_find')
    if type(requested) is not int or requested<1:
        return None
    return requested


class M106Session(object):
    def __init__(self,plan,save_slot,sim_day,home_zone):
        if (not isinstance(plan,dict)
                or plan.get('status')!='BRIDGE_CANDIDATE_ONLY_NOT_EA_BOUND'
                or plan.get('adapter_authorized') is not False
                or len(plan.get('all_16',()))!=16
                or len(plan.get('normal_base_ids',()))!=8
                or len(plan.get('core_role_assignments',()))!=5
                or len(plan.get('playable',()))!=3):
            raise ValueError('M106 16-student planning prerequisites unavailable')
        if (type(sim_day) is not int or sim_day<0
                or not str(save_slot).isdigit() or int(save_slot)<1
                or not str(home_zone).isdigit() or int(home_zone)<1):
            raise ValueError('M106 unverifiable save/day/home zone')
        self.plan=plan
        self.slot=str(save_slot)
        self.day=sim_day
        self.home_zone=str(home_zone)
        self.school_zone=None
        self.core_seen={}
        self.core_duplicates=0
        self.base_seen=[]
        self.base_target_count=0
        self.cancelled=False

    def _valid(self,slot,day,zone,bouncer,school):
        return (not self.cancelled and str(slot)==self.slot
                and type(day) is int and day==self.day
                and str(zone).isdigit() and str(zone)!=self.home_zone
                and bouncer is True and school is True
                and (self.school_zone is None or str(zone)==self.school_zone))

    def decide(self,mode,filter_guid,args,kwargs,ea_base_filter,
               slot,day,zone,bouncer,school=False):
        """(decision,args,kwargs) -- changes are proposed only for EA native matching.

        No implicit selection, no second chance random NPC on explicit target,
        and no claim the proposed constraints were honored by EA.
        """
        original=('PRESERVE',tuple(args),dict(kwargs))
        if mode!='matching' or filter_guid not in (
                frozenset(CORE_FILTER_TO_JOB)|frozenset((BASE_FILTER_GUID,))):
            return original
        if not self._valid(slot,day,zone,bouncer,school):
            return original
        count=_request_count(args,kwargs)
        if filter_guid in CORE_FILTER_TO_JOB:
            job=CORE_FILTER_TO_JOB[filter_guid]
            if job in self.core_seen:
                self.core_duplicates+=1
                return original
            if count!=1:
                self.core_seen[job]='COUNT_MISMATCH'
                return original
            action,changes,options,reason=propose_school_only_filter_arguments(
                self.plan,filter_guid,args,kwargs,ea_base_filter,
                school=True,same_save=True,same_day=True,native_bouncer=True)
            self.core_seen[job]=action
            if action!='PROPOSAL_ONLY':
                return original
        else:
            remaining=8-self.base_target_count
            if count is None or count>remaining:
                self.base_seen.append(('COUNT_MISMATCH',count))
                return original
            ids=self.plan['normal_base_ids'][
                self.base_target_count:self.base_target_count+count]
            action,changes,options,reason=native_base_arguments(
                mode,args,kwargs,BASE_FILTER_GUID,
                tuple(int(sid) for sid in ids))
            self.base_seen.append((action,count))
            if action!='constrain':
                return original
            self.base_target_count+=count
        if self.school_zone is None:
            self.school_zone=str(zone)
        return ('CONSTRAIN',changes,options)

    def evidence(self):
        return {
            'kind':'M106_NATIVE_SELECTION_PROPOSAL_NOT_ATTENDANCE',
            'core_requests_observed':len(self.core_seen),
            'core_duplicate_requests':self.core_duplicates,
            'core_requests_constrained':sum(
                val=='PROPOSAL_ONLY' for val in self.core_seen.values()),
            'base_request_calls_observed':len(self.base_seen),
            'base_targets_constrained':self.base_target_count,
            'base_requests_bypassed':sum(
                decision!='constrain' for decision,_ in self.base_seen),
            'core_requests_bypassed':sum(
                val!='PROPOSAL_ONLY' for val in self.core_seen.values()),
            'school_only_filter_bridges':len(
                self.plan.get('school_only_bridge_candidates',())),
            'school_zone':self.school_zone,
            'all_thirteen_native_targets_requested':(
                len(self.core_seen)==5
                and self.core_duplicates==0
                and all(v=='PROPOSAL_ONLY' for v in self.core_seen.values())
                and self.base_target_count==8
                and all(v=='constrain' for v,_ in self.base_seen)),
            'actual_core_role_binding_verified':False,
            'actual_attendance_verified':False,
            'class_8_plus_8_verified':False,
            'ea_base_schedule_count_changed':False
        }

    def off(self):
        self.cancelled=True
