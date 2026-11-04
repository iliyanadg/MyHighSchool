"""M113: single earliest EA school-count entry -> atomic 5-stage handoff.

One dormant, reversible WeeklyScheduleDay classmethod wrapper is installed
from HOME. Only the ORIGINAL EA school Base-count callback can bind a target
zone; the exact 16 registered Sim IDs and manually chosen five Core roles
are frozen before travel. The remaining original-EA stage wrappers must be
installed BEFORE the original school scheduler continues spawning NPCs.

This is a Python 3.7 OFFLINE controller contract, NOT a game entry point.
There is NO verified live stage graph/provider. Never ship as active mod or
treat synthetic proof flags as game evidence. No mutations on import.
"""
from mhs108_native_invitation import (
    CORE_JOBS, BASE_SITUATION, prepare_fixed_manifest, InvitationPlanError,
)
from mhs108_native_base_count import propose_native_base_count
from mhs109_atomic_activation import REQUIRED_RUNTIME_EVIDENCE
from mhs109_readonly_ea_probe import KNOWN_CONFLICT_MARKERS

SCHOOL_SCHEDULES = frozenset((277657,279958))
EA_OWNER = 'venues.weekly_schedule_zone_director.WeeklyScheduleDay'
LATE_STAGES = (
    'native_precreate',
    'school_filter_scope',
    'no_show_guard',
    'unified_lessons',
    'post_bouncer_observer',
)


def _id(raw):
    if type(raw) not in (str,int):
        return None
    value = str(raw)
    if not value.isdigit() or int(value)<1 or str(int(value)) != value:
        return None
    return value


def _home_plan(classes,playable,core,save_slot,sim_day,home_zone):
    """Freeze user choices. No implicit Core job assignment or NPC fill."""
    if (type(save_slot) not in (str,int) or
            _id(save_slot) is None or _id(home_zone) is None or
            type(sim_day) is not int or sim_day < 0 or
            not isinstance(classes,(list,tuple)) or len(classes)!=2 or
            not isinstance(core,dict) or set(core)!=set(CORE_JOBS)):
        return None
    try:
        groups=tuple(tuple(_id(x) for x in group) for group in classes)
        flat=groups[0]+groups[1]
        played=tuple(_id(x) for x in playable)
        roles=tuple((job,_id(core[job])) for job in CORE_JOBS)
        special=tuple(sid for _,sid in roles)
        if (any(len(c)!=8 for c in groups) or None in flat or
                len(set(flat))!=16 or len(played)!=3 or
                None in played or len(set(played))!=3 or
                not set(played)<=set(flat) or
                None in special or len(set(special))!=5 or
                not set(special)<=set(flat)-set(played) or
                len(set(flat)-set(played)-set(special)) != 8):
            return None
        return {
            'classes':groups,'playable':played,
            'core_assignments':roles,
            'save_slot':_id(save_slot),'sim_day':sim_day,
            'home_zone':_id(home_zone),
        }
    except (TypeError,AttributeError,ValueError,IndexError):
        return None


def _owner_for(class_obj):
    for owner in getattr(class_obj,'__mro__',()):
        descriptor=owner.__dict__.get('get_long_term_situation_count')
        if descriptor is not None:
            return owner,descriptor
    return None,None


class M113EarlySchoolEntry(object):
    """The home-to-school latch and stage rollback for one school day."""

    def __init__(self,classes,playable,core,save_slot,sim_day,home_zone,
                 context_provider,session_factory,stage_graph_factory):
        self.home=_home_plan(classes,playable,core,
                             save_slot,sim_day,home_zone)
        self.context_provider=context_provider
        self.session_factory=session_factory
        self.stage_graph_factory=stage_graph_factory
        self.state='OFF' if self.home is not None else 'INVALID_HOME_PLAN'
        self.error=None
        self.school_zone=None
        self.session=None
        self.original_count=None
        self.native_call_count=0
        self._owner=None
        self._prior=None
        self._wrapped=None
        self._undos=[]

    def arm_at_home(self,weekly_day_class):
        """Install ONE dormant read-through hook; do not enable EA changes."""
        if (self.state!='OFF' or
                not callable(self.context_provider) or
                not callable(self.session_factory) or
                not callable(self.stage_graph_factory)):
            return False
        owner,descriptor=_owner_for(weekly_day_class)
        if (owner is None or owner.__module__+'.'+owner.__name__ != EA_OWNER
                or not isinstance(descriptor,classmethod)):
            return False
        original=descriptor.__func__
        if (not callable(original) or
                any(getattr(original,k,False)
                    for k in KNOWN_CONFLICT_MARKERS) or
                getattr(original,'_mhs113_entry',False)):
            return False
        self._owner=owner
        self._prior=descriptor

        def wrapped(cls,data,resolver):
            # Exactly once and BEFORE any proposal or other wrapper.
            native=original(cls,data,resolver)
            self.native_call_count+=1
            if self.state=='ACTIVE_LATE_STAGES':
                try:
                    return self._on_second_native_count(
                        cls,data,resolver,native)
                except Exception:
                    return native
            if self.state!='WAITING_FOR_EA_SCHOOL':
                return native
            try:
                return self._on_original_school_count(cls,data,resolver,native)
            except Exception as exc:
                self.error='ENTRY_CALLBACK_ERROR_'+type(exc).__name__
                if not self._rollback_late():
                    self.state='ROLLBACK_INCOMPLETE'
                else:
                    self.state='BLOCKED'
                return native

        wrapped._mhs113_entry=True
        self._wrapped=classmethod(wrapped)
        owner.get_long_term_situation_count=self._wrapped
        self.state='WAITING_FOR_EA_SCHOOL'
        return True

    def _on_second_native_count(self,cls,data,resolver,native):
        """Second EA schedule uses the SAME verified school-zone session.

        M110 observed both original weekly school schedule GUIDs. Do not
        modify non-Base calls, another save/day/zone, or later calls after
        the Base NPC invitation sequence has already begun.
        """
        schedule=getattr(cls,'guid64',None)
        kind=getattr(getattr(data,'situation',None),'guid64',None)
        if (schedule not in SCHOOL_SCHEDULES or kind!=BASE_SITUATION
                or native!=(3,3) or self.session is None):
            return native
        context=self.context_provider(cls,data,resolver)
        if (not isinstance(context,dict)
                or str(context.get('save_slot'))!=self.home['save_slot']
                or type(context.get('sim_day')) is not int
                or context['sim_day']!=self.home['sim_day']
                or str(context.get('school_zone'))!=self.school_zone
                or str(context.get('zone_id'))!=self.school_zone
                or context.get('schedule_guid')!=schedule
                or context.get('ea_schedule_not_started') is not True
                or context.get('native_weekly_school_origin_verified')
                    is not True
                or context.get('school_verified') is not True):
            return native
        trusted=dict(context)
        trusted['native_count_return_observed_in_current_callback']=True
        trusted['exact_original_base_count_observed']=native
        return propose_native_base_count(native,schedule,kind,
                                         self.session,trusted)

    def _on_original_school_count(self,cls,data,resolver,native):
        # Never identify a school by an untrusted string in an invocation
        # from another lot. Here the wrapper is around the actual EA
        # method, and caller class + tuned situation are checked.
        situation=getattr(data,'situation',None)
        kind=getattr(situation,'guid64',None)
        schedule=getattr(cls,'guid64',None)
        if (type(schedule) is not int or schedule not in SCHOOL_SCHEDULES
                or type(kind) is not int or kind!=BASE_SITUATION
                or native!=(3,3)):
            return native
        context=self.context_provider(cls,data,resolver)
        if not isinstance(context,dict):
            return native
        # These fields must come from an independent live adapter, not
        # hardcoded flags fabricated by this controller.
        if (str(context.get('save_slot'))!=self.home['save_slot']
                or type(context.get('sim_day')) is not int
                or context['sim_day']!=self.home['sim_day']
                or _id(context.get('school_zone')) is None
                or _id(context.get('zone_id')) is None
                or str(context['zone_id'])!=str(context['school_zone'])
                or str(context['school_zone'])==self.home['home_zone']
                or context.get('schedule_guid')!=schedule
                or context.get('native_weekly_school_origin_verified')
                    is not True
                or context.get('school_verified') is not True
                or context.get('ea_schedule_not_started') is not True
                or context.get('before_school_schedule_verified')
                    is not True
                or context.get('source')!='EA_RUNTIME_OBSERVATION'
                or any(context.get(key) is not True
                       for key in REQUIRED_RUNTIME_EVIDENCE)):
            return native
        # Original callback already ran. No guess of '3 = 6 - playables'.
        trusted=dict(context)
        trusted['native_count_return_observed_in_current_callback']=True
        trusted['exact_original_base_count_observed']=native
        trusted['schedule_guid']=schedule
        zone=str(context['school_zone'])
        manifest=prepare_fixed_manifest(
            self.home['classes'],self.home['playable'],
            dict(self.home['core_assignments']),
            self.home['save_slot'],self.home['sim_day'],zone)
        session=self.session_factory(manifest)
        if session is None or not callable(getattr(session,'reserve_core_before_schedule',None)):
            self.error='NO_NATIVE_GUEST_SESSION'
            self.state='BLOCKED'
            return native
        if not session.reserve_core_before_schedule(trusted):
            self.error='CORE_HOLDS_NOT_PREPARED_BEFORE_EA'
            self.state='BLOCKED'
            return native
        proposed=propose_native_base_count(
            native,schedule,kind,session,trusted)
        if proposed!=(8,8):
            self.error='NATIVE_COUNT_PROPOSAL_NOT_AUTHORIZED'
            self.state='BLOCKED'
            return native

        graph=self.stage_graph_factory(session,trusted)
        if (not isinstance(graph,dict) or set(graph)!=set(LATE_STAGES)
                or any(not isinstance(graph[key],dict)
                       or set(graph[key])!={'install','restore'}
                       or not callable(graph[key]['install'])
                       or not callable(graph[key]['restore'])
                       for key in LATE_STAGES)):
            self.error='INCOMPLETE_HOOK_GRAPH'
            self.state='BLOCKED'
            return native
        self.state='INSTALLING'
        for name in LATE_STAGES:
            stage=graph[name]
            # Record undo *before* install to survive a partial patch.
            self._undos.append((name,stage['restore']))
            try:
                if stage['install'](manifest,trusted) is not True:
                    raise RuntimeError('STAGE_REJECTED')
            except Exception as exc:
                self.error=name+':'+type(exc).__name__
                self.state=('BLOCKED' if self._rollback_late()
                            else 'ROLLBACK_INCOMPLETE')
                return native
        self.school_zone=zone
        self.session=session
        self.original_count=native
        self.state='ACTIVE_LATE_STAGES'
        return proposed

    def _rollback_late(self):
        kept=[]
        for name,restore in reversed(self._undos):
            try:
                if restore() is not True:
                    kept.append((name,restore))
            except Exception:
                kept.append((name,restore))
        self._undos=list(reversed(kept))
        return not self._undos

    def stop(self):
        """Restore late hooks first, earliest count classmethod last."""
        if self.state in ('OFF','INVALID_HOME_PLAN','STOPPED'):
            return False
        if not self._rollback_late():
            self.state='ROLLBACK_INCOMPLETE'
            return False
        if (self._owner is None or self._prior is None or
                self._owner.__dict__.get('get_long_term_situation_count')
                is not self._wrapped):
            self.state='RESTORE_CONFLICT'
            return False
        self._owner.get_long_term_situation_count=self._prior
        self.state='STOPPED'
        self.session=None
        return True

    def snapshot(self):
        return {
            'kind':'M113_TWO_PHASE_EA_SCHOOL_ENTRY_OFFLINE_ONLY',
            'state':self.state,'error':self.error,
            'native_count_calls':self.native_call_count,
            'late_stages_installed':tuple(name for name,_ in self._undos),
            'school_zone_bound':self.school_zone is not None,
            'original_base_count':self.original_count,
            'home_roster_valid':self.home is not None,
            'game_live_provider_implemented':False,
            'attendance_16_verified':False,
            'classroom_routing_verified':False,
            'save_modified':False,
        }
