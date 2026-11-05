"""Single school controller derived from M148 and its native EA hooks.

Two saved classes of eight; playable membership is read from the save.
Five manual Core appointments are retained; Base NPC capacity is derived
from the remaining enrollment. EA owns situations, schedule and completion.
Offline validation does not establish physical attendance in the game.
"""
import os
import services
import sims4.commands
from sims.sim_info_types import Age, Species
from filters.tunable import TunableSimFilter
from mhs_m2_game_bridge import current_slot
from mhs_m2_store import RosterStore
from mhs34_settings import SettingsStore
from mhs97_core_role_store import CoreRoleStore
from mhs122_classroom_job_readback import school_classroom_snapshot
from mhs123_lesson_guest_projection import project_original_lesson_guests, LESSON_JOBS
from mhs124_lesson_action_readback import inspect_sixteen_lesson_actions
from mhs125_safe_recovery import inspect_candidate,recover_one
from mhs126_early_preparation_projection import (
    project_early_preparation_guests, PREP_JOBS)
from mhs127_school_timing_readback import game_clock,timed_roster_snapshot
from mhs128_ea_class_trait_alignment import (CLASS1_TRAIT_ID,planned_changes,public_rows,align_roster_trait)
from mhs128_board_posture_audit import audit_classroom_targets
from mhs130_physical_seat_audit import derive_board_anchors,evaluate_physical_seats
from mhs132_native_player_test_audit import (PLAYER_ROLE_BUFF,inspect_native_player_tests)
from mhs134_native_player_job_audit import inspect_player_jobs
from mhs136_player_test_hierarchy import inspect_test_hierarchy
from mhs139_ea_zerbu_adapter import install_known_whiteboard_adapter
from mhs140_native_lesson_entry import launch_once_at_native_lesson
from mhs148_day_trace import DayJournal, observe_student
from mhs148_clock_and_sampling import (
    read_live_clocks, should_capture_sim_snapshot)
from mhs145_subject_picker_patch import (
    install_subject_picker, SUBJECT_IDS)
from mhs147_class_timing_policy import (
    can_early_request, preparation_period, validate_anchors, truant_evidence,
    roster_rearm_required)
from mhs_school_session import plan_roster, school_day_key
from mhs_native_staff_appointments import (
    ROLE_JOBS, ALL_NATIVE_JOBS, load_native_staff_plan,
    project_native_staff_guests)
from mhs_attendance_policy import LessonRequestLedger, protected_gameplay
from mhs_queue_readback import queue_snapshot
from mhs143_native_attendance_policy import (
    allowed_direct_attend, find_observed_attend, job_matches_class,
    analyze_npc_dining, summarize_registered_attendance,
    classroom_activity)
from mhs142_school_policy import (
    minute_of_day, can_roll_to_afternoon, class_retry_decision,
    summarize_npc_lunch)
from mhs131_native_playable_class import (
    CLASS1_WHITEBOARD_TRUE,CLASS2_WHITEBOARD_TRUE,PLAYER_CLASS_START,
    safe_class_board_candidates,find_playable_entry,queue_playable_class)

FOLDER=os.path.join(os.path.expanduser('~'),'Documents',
    'Electronic Arts','The Sims 4','MY_HIGH_SCHOOL_M25_TEST_DATA')
SCHOOL_SCHEDULES=frozenset((277657,279958))
BASE_SITUATION=277733
BASE_JOB=277894
CORE_JOBS=(278965,278966,278967,278968,303765)
CORE_SITUATION=298052
STAFF_JOBS=frozenset((277895,278963))
VENUE_STAFF_SITUATION=298096
CAFETERIA_STAFF_SITUATION=278011
_RUNTIME=None


def zone_schedule():
    zone=services.current_zone()
    venue=services.venue_service()
    director=venue.get_zone_director() if venue else None
    return (getattr(zone,'id',None),
            getattr(getattr(director,'_schedule',None),'guid64',None))


def registered_eight(allow_travel=False):
    slot=str(current_slot(allow_travel=allow_travel))
    setting=SettingsStore(FOLDER).load(slot)
    if not setting.active or setting.class_count!=2:
        raise ValueError('Attiva due classi MHS')
    roster=RosterStore(FOLDER).load(slot)
    groups=tuple(tuple(str(i) for i in roster.class_members(klass))
                 for klass in (1,2))
    household=services.active_household()
    if household is None:
        raise ValueError('Nessuna famiglia attiva')
    played=tuple(str(info.sim_id) for info in household.sim_info_gen()
                 if getattr(info,'age',None)==Age.TEEN
                 and getattr(info,'species',None)==Species.HUMAN)
    core=CoreRoleStore(FOLDER).load(slot)
    pinned=core.chosen() if core.complete else {}
    plan=plan_roster(groups,played,pinned,services.sim_info_manager(),
                     Age.TEEN,Species.HUMAN)
    return slot,plan['base'],plan['pinned']


def registered_for_school_travel(expected_slot):
    result=registered_eight(allow_travel=True)
    if result[0]!=str(expected_slot):
        raise ValueError('SAVE_SLOT_CHANGED')
    return result


def current_school_day(slot):
    now=services.time_service().sim_now
    ticks=getattr(now,'absolute_ticks',None)
    ticks=ticks() if callable(ticks) else ticks
    return school_day_key(str(slot),ticks)


def _install_school_adapters(runtime):
    if not runtime.active or not runtime.in_school():
        return False
    if runtime.m140_patch_checked:
        return bool((runtime.m140_patch_result or {}).get('applied') and
                    (runtime.m145_patch_result or {}).get('applied'))
    runtime.m140_patch_checked=True
    try:
        from sims4.resources import Types
        from interactions import ParticipantType
        from event_testing.results import TestResult
        from mhs_scoped_classroom import registered_board_context, install_native_board_guard
        manager=services.get_instance_manager(Types.INTERACTION)
        states=services.get_instance_manager(Types.OBJECT_STATE)
        state1=states.get(CLASS1_WHITEBOARD_TRUE) if states else None
        state2=states.get(CLASS2_WHITEBOARD_TRUE) if states else None
        if state1 is None or state2 is None:
            runtime.error='CLASSROOM_STATE_TUNING_UNAVAILABLE'
            return False
        def scope(resolver):
            if not runtime.active or not runtime.school_ready or not runtime.in_school():
                return None
            context=registered_board_context(resolver,ParticipantType.Actor,
                ParticipantType.Object,runtime.classroom_membership,state1,state2)
            if context is not None:
                runtime.classroom_scope_checks+=1
                if context['registered_class']!=context['board_class']:
                    runtime.classroom_scope_blocked+=1
                    runtime.classroom_scope_last[context['sim_id']]=context
            return context
        failure=lambda reason:TestResult(False,reason)
        source=manager.get(PLAYER_CLASS_START) if manager else None
        runtime.m140_patch_result,runtime.m140_patch_undo=(
            install_known_whiteboard_adapter(source,scope=scope,failure=failure))
        runtime.m145_patch_result,runtime.m145_patch_undo=(
            install_subject_picker(source,
                {guid:manager.get(guid) for guid in SUBJECT_IDS},
                picker_patch_applied=bool(
                    (runtime.m140_patch_result or {}).get('applied')),
                scope=scope,failure=failure))
        if not (runtime.m145_patch_result or {}).get('applied'):
            if runtime.m140_patch_undo is not None:
                if runtime.m140_patch_undo():
                    runtime.m140_patch_undo=None
                    runtime.m140_patch_result=dict(runtime.m140_patch_result,
                        applied=False,reason='SUBJECT_ADAPTER_ROLLED_BACK')
            return False
        runtime.classroom_guard_result,runtime.classroom_guard_undo=(
            install_native_board_guard(manager.get(297779),scope,failure))
        if not runtime.classroom_guard_result.get('applied'):
            if runtime.m145_patch_undo is not None and runtime.m145_patch_undo():
                runtime.m145_patch_undo=None
                runtime.m145_patch_result=dict(runtime.m145_patch_result,
                    applied=False,reason='NPC_GUARD_ROLLBACK')
            if runtime.m140_patch_undo is not None and runtime.m140_patch_undo():
                runtime.m140_patch_undo=None
                runtime.m140_patch_result=dict(runtime.m140_patch_result,
                    applied=False,reason='NPC_GUARD_ROLLBACK')
            return False
        return True
    except Exception as exc:
        runtime.error='CLASS_ADAPTER_'+type(exc).__name__
        for field in ('classroom_guard_undo','m145_patch_undo','m140_patch_undo'):
            callback=getattr(runtime,field,None)
            if callback is not None:
                try:
                    if callback():setattr(runtime,field,None)
                    else:runtime.error+=':RESTORE_CONFLICT'
                except Exception:
                    runtime.error+=':RESTORE_FAILED'
        runtime.m140_patch_result={'applied':False,'reason':runtime.error}
        runtime.m145_patch_result={'applied':False,'reason':runtime.error}
        return False


class ThirteenNPCController(object):
    def __init__(self,slot,targets,pinned,home_zone,manager_owner,bouncer_owner,
                 schedule_owner,job,core_jobs,blank,guest_cls,invited):
        self.slot=slot
        self.targets=tuple(targets)
        self.pinned=dict(pinned)
        self.core_jobs=dict(core_jobs)
        self.core_created=None
        self.core_pending=False
        self.core_refused=0
        self.core_failures=0
        self.core_filter_hits=0
        self.lesson_classes=None
        self.lesson_jobs={}
        self.lesson_attempted=set()
        self.lesson_created={}
        self.lesson_pending=None
        self.lesson_refused=0
        self.lesson_filter_hits=0
        self.prep_created={}
        self.prep_attempted=set()
        self.prep_pending=None
        self.prep_refused=0
        self.prep_jobs={}
        self.prep_filter_hits=0
        self.m127_timing_events=[]
        self.m131_sync_attempted=False
        self.m131_sync_result=None
        self.m140_auto_attempted=set()
        self.m140_auto_reports=[]
        self.m141_journal=None
        self.m141_timer=None
        self.m141_watcher_timer=None
        self.m141_trace_origin=None
        self.m141_start_error=None
        self.m141_last_tick_error=None
        self.m142_afternoon_rearmed=False
        self.m142_period='morning'
        self.m142_auto_accepted=set()
        self.m142_retry_attempted=set()
        self.m142_retry_reports=[]
        self.m142_afternoon_roll_events=[]
        self.m143_direct_attempted=set()
        self.m143_direct_reports=[]
        self.m143_board_anchors=None
        self.m143_policy_log=set()
        self.m147_anchors_status=None
        self.m147_preclass_attempted=set()
        self.m147_preclass_reports=[]
        self.m147_preclass_reported=set()
        self.m147_trace_end=None
        self.m148_last_sample_ticks=None
        self.m148_skipped_samples=0
        self.m140_patch_checked=False
        self.m140_patch_result=None
        self.m140_patch_undo=None
        self.m145_patch_result=None
        self.m145_patch_undo=None
        self.home_zone=home_zone
        self.manager_owner=manager_owner
        self.bouncer_owner=bouncer_owner
        self.schedule_owner=schedule_owner
        self.job=job
        self.blank=blank
        self.guest_cls=guest_cls
        self.invited=invited
        self.previous={}
        self.wrappers={}
        self.current=None
        self.created={}
        self.pending=None
        self._tracked={}
        self.base_count_calls=0
        self.base_count_overrides=0
        self.base_count_last=None
        self.filter_hits=0
        self.random_blocked=0
        self.refused=0
        self.error=''
        self.active=False
        self.bound_zone=None
        self.school_day=None
        self.school_ready=False
        self.lesson_requests=LessonRequestLedger()
        self.classroom_membership={}
        self.classroom_guard_result=None
        self.classroom_guard_undo=None
        self.classroom_scope_checks=0
        self.classroom_scope_blocked=0
        self.classroom_scope_last={}
        self.lesson_entry_samples=[]
        self.lesson_entry_last_ticks=None
        self.school_staff_samples=[]
        self.school_readback_errors=[]
        self.staff_plan_loader=None
        self.staff_plan={'jobs':{},'blocked':{},'roster_read_only':True}
        self.staff_jobs={}
        self.staff_pending=None
        self.staff_created={}
        self.staff_projection_reports=[]
        self.staff_filter_hits=0

    def begin_school_day(self, key):
        """Reset our bookkeeping before EA's first create on a new day.

        Do not destroy situations, alter their schedule or replay invitations.
        A changed/invalid roster refuses interception and leaves EA in charge.
        """
        if self.school_day == key:
            return True
        slot,targets,pinned=registered_for_school_travel(self.slot)
        roster=RosterStore(FOLDER).load(slot)
        groups=tuple(tuple(str(s) for s in roster.class_members(k))
                     for k in (1,2))
        _m141_stop_trace(self)
        for req,prior in tuple(self._tracked.items()):
            if getattr(req,'_sim_filter',None) is self.blank:
                req._sim_filter=prior
        self._tracked.clear()
        self.targets=tuple(targets)
        self.pinned=dict(pinned)
        self.lesson_classes=groups
        self.classroom_membership={sid:klass for klass,group in enumerate(groups,1)
                                   for sid in group}
        self.classroom_scope_checks=0
        self.classroom_scope_blocked=0
        self.classroom_scope_last.clear()
        self.lesson_entry_samples[:]=[]
        self.lesson_entry_last_ticks=None
        self.school_staff_samples[:]=[]
        self.school_readback_errors[:]=[]
        self.staff_pending=None
        self.staff_created.clear()
        self.staff_projection_reports[:]=[]
        self.staff_filter_hits=0
        if callable(self.staff_plan_loader):
            try:
                self.staff_plan=self.staff_plan_loader(self.slot,groups)
            except Exception as exc:
                self.staff_plan={'jobs':{},'blocked':{
                    'all':'STAFF_PLAN_'+type(exc).__name__},
                    'roster_read_only':True}
        for name in ('created','lesson_created','prep_created'):
            getattr(self,name).clear()
        for name in ('lesson_attempted','prep_attempted','m140_auto_attempted',
                     'm142_auto_accepted','m142_retry_attempted',
                     'm143_direct_attempted','m143_policy_log',
                     'm147_preclass_attempted','m147_preclass_reported'):
            getattr(self,name).clear()
        for name in ('m140_auto_reports','m142_retry_reports',
                     'm143_direct_reports','m147_preclass_reports',
                     'm127_timing_events','m142_afternoon_roll_events'):
            getattr(self,name)[:]=[]
        self.current=self.pending=self.core_created=None
        self.lesson_pending=self.prep_pending=None
        self.core_pending=False
        self.m131_sync_attempted=False
        self.m131_sync_result=None
        self.m141_journal=None
        self.m147_trace_end=None
        self.m148_last_sample_ticks=None
        self.m148_skipped_samples=0
        self.m142_afternoon_rearmed=False
        self.m142_period='morning'
        self.m143_board_anchors=None
        self.m147_anchors_status=None
        self.bound_zone=None
        self.error=''
        self.school_day=key
        self.school_ready=True
        # The request ledger is shared by the normal entry and bounded retries.
        self.lesson_requests=LessonRequestLedger()
        return True

    def in_school(self):
        try:
            zone,schedule=zone_schedule()
            return (zone is not None and zone!=self.home_zone
                    and schedule in SCHOOL_SCHEDULES
                    and str(current_slot(allow_travel=True))==self.slot)
        except Exception:
            return False

    def guest_clone(self,old,sim_id):
        if old is None:
            return None
        try:
            existing=tuple(old.guest_info_gen())
            others=[]
            base_count=0
            for guest in existing:
                guid=getattr(getattr(guest,'job_type',None),'guid64',None)
                if guid==BASE_JOB:
                    base_count+=1
                    if base_count>1:
                        return None
                elif guid in (277895,278963):
                    others.append(guest)
                else:
                    return None
            replacement=type(old)(
                invite_only=True,host_sim_id=old.host_sim_id,
                filter_requesting_sim_id=old.filter_requesting_sim_id)
            for guest in others:
                replacement.add_guest_info(guest.clone_for_guest_list())
            guest=self.guest_cls.construct_from_purpose(
                int(sim_id),self.job,self.invited)
            if (str(getattr(guest,'sim_id',None))!=sim_id
                    or getattr(guest,'accept_alternate_sim',None) is not False):
                return None
            replacement.add_guest_info(guest)
            actual=tuple(replacement.guest_info_gen())
            if (len(actual)!=len(others)+1
                    or str(actual[-1].sim_id)!=sim_id):
                return None
            return replacement
        except Exception:
            return None

    def core_guest_clone(self,old):
        """Preserve EA staff, replace only five distinct native Core jobs."""
        if old is None:
            return None
        try:
            existing=tuple(old.guest_info_gen())
            staff=[]
            seen=set()
            for guest in existing:
                guid=getattr(getattr(guest,'job_type',None),'guid64',None)
                if guid in CORE_JOBS:
                    if guid in seen:
                        return None
                    seen.add(guid)
                elif guid in STAFF_JOBS:
                    if str(getattr(guest,'sim_id',None)) in (
                            set(self.targets)|set(self.pinned.values())):
                        return None
                    staff.append(guest)
                else:
                    return None
            replacement=type(old)(
                invite_only=True,host_sim_id=old.host_sim_id,
                filter_requesting_sim_id=old.filter_requesting_sim_id)
            for guest in staff:
                replacement.add_guest_info(guest.clone_for_guest_list())
            for jobid in CORE_JOBS:
                sid=self.pinned[jobid]
                guest=self.guest_cls.construct_from_purpose(
                    int(sid),self.core_jobs[jobid],self.invited)
                if (str(getattr(guest,'sim_id',None))!=sid
                        or getattr(getattr(guest,'job_type',None),'guid64',None)
                            !=jobid
                        or getattr(guest,'accept_alternate_sim',None)
                            is not False):
                    return None
                replacement.add_guest_info(guest)
            actual=tuple(replacement.guest_info_gen())
            if (len(actual)!=len(staff)+5 or
                    tuple(str(g.sim_id) for g in actual[-5:]) !=
                    tuple(self.pinned[j] for j in CORE_JOBS)):
                return None
            return replacement
        except Exception:
            return None

    def eligible(self,request):
        if not self.active or not self.school_ready or not self.in_school():
            return False
        sid=str(getattr(request,'_requested_sim_id',None))
        situation=getattr(getattr(request,'_situation',None),'guid64',None)
        job=getattr(getattr(request,'_job_type',None),'guid64',None)
        native_base=(situation==BASE_SITUATION and job==BASE_JOB
                     and sid in self.targets and
                     (sid==self.pending or sid in self.created))
        native_core=(situation==CORE_SITUATION and job in CORE_JOBS
                     and self.pinned.get(job)==sid
                     and (self.core_pending or self.core_created is not None))
        prep_spec=PREP_JOBS.get(situation)
        native_prep=(prep_spec is not None and job==prep_spec[1]
                     and self.lesson_classes is not None
                     and sid in self.lesson_classes[prep_spec[0]-1]
                     and (self.prep_pending==prep_spec[0]
                          or prep_spec[0] in self.prep_created))
        spec=LESSON_JOBS.get(situation)
        native_lesson=(spec is not None
                       and job==spec[1]
                       and self.lesson_classes is not None
                       and sid in self.lesson_classes[spec[0]-1]
                       and (self.lesson_pending==spec[0]
                            or spec[0] in self.lesson_created))
        staff_ids=self.staff_plan.get('job_groups',{}).get(job)
        if staff_ids is None:
            one=self.staff_plan.get('jobs',{}).get(job)
            staff_ids=(one,) if one is not None else ()
        native_staff=(situation in ROLE_JOBS and
                      sid in staff_ids and
                      job in dict(ROLE_JOBS[situation]).values() and
                      (self.staff_pending==situation or
                       situation in self.staff_created))
        if not (native_base or native_core or native_lesson or native_prep
                or native_staff):
            return False
        zone,_=zone_schedule()
        if zone!=self.bound_zone:
            return False
        constrained=getattr(request,'_constrained_sim_ids',None)
        if (type(constrained) not in (set,frozenset,list,tuple)
                or set(constrained)!={int(sid)}
                or getattr(request,'_for_persisted_sim',None) is not False
                or getattr(request,'_continue_if_constraints_fail',None)
                   is not False
                or getattr(request,'_sim_filter',None) is not
                   getattr(getattr(request,'_job_type',None),'filter',None)):
            return False
        info=services.sim_info_manager().get(int(sid))
        if native_staff:
            return (info is not None and
                    getattr(info,'age',None) in
                    (Age.YOUNGADULT,Age.ADULT,Age.ELDER) and
                    getattr(info,'species',None)==Species.HUMAN and
                    sid not in self.classroom_membership)
        return (info is not None and getattr(info,'age',None)==Age.TEEN
                and getattr(info,'species',None)==Species.HUMAN
                and (native_lesson or native_prep or
                     getattr(info,'is_selectable',True) is False))

    def install(self):
        manager=self.manager_owner
        request=self.bouncer_owner
        day=self.schedule_owner
        methods=((manager,'create_situation'),
                 (request,'__init__'),
                 (request,'get_additional_filter_terms'),
                 (request,'clone_for_replace'),
                 (day,'get_long_term_situation_count'))
        if (not 0<=len(self.targets)<=11 or len(set(self.targets))!=len(self.targets)
                or set(self.pinned)!=set(CORE_JOBS)
                or len(set(self.pinned.values()))!=5
                or set(self.targets)&set(self.pinned.values())
                or set(self.core_jobs)!=set(CORE_JOBS)
                or any(getattr(self.core_jobs[j],'guid64',None)!=j
                       for j in CORE_JOBS)
                or any(name not in owner.__dict__
                       for owner,name in methods)):
            return False
        originals={(owner,name):owner.__dict__[name]
                   for owner,name in methods}
        descriptor=originals[(day,'get_long_term_situation_count')]
        if not isinstance(descriptor,classmethod):
            return False
        for original in originals.values():
            func=original.__func__ if isinstance(original,classmethod) else original
            if (not callable(func)
                    or getattr(func,'_mhs127_hook',False)
                    or getattr(func,'_mhs119_hook',False)):
                return False
        original_create=originals[(manager,'create_situation')]
        original_init=originals[(request,'__init__')]
        original_terms=originals[(request,'get_additional_filter_terms')]
        original_clone=originals[(request,'clone_for_replace')]
        original_count=descriptor.__func__

        def count(cls,data,resolver):
            result=original_count(cls,data,resolver)
            if (not self.active or not self.in_school()
                    or getattr(cls,'guid64',None) not in SCHOOL_SCHEDULES
                    or getattr(getattr(data,'situation',None),'guid64',None)
                       !=BASE_SITUATION):
                return result
            try:
                self.begin_school_day(current_school_day(self.slot))
                if not _install_school_adapters(self):
                    self.school_ready=False
                    self.error='UNSUPPORTED_CLASSROOM_ADAPTER'
                    return result
            except Exception as exc:
                self.school_ready=False
                self.error='DAY_PREFLIGHT_'+type(exc).__name__+':'+str(exc)[:100]
                return result
            self.base_count_calls+=1
            self.base_count_last=result
            # Both verified EA school schedules start with six Base slots,
            # reduced by household career participants. Three was one test
            # household's result, not a fixed native prerequisite.
            known_native=(type(result) is tuple and len(result)==2 and
                          type(result[0]) is int and type(result[1]) is int and
                          result[0]==result[1] and 0<=result[0]<=6)
            if (known_native and not self.created
                    and self.pending is None):
                self.base_count_overrides+=1
                return (len(self.targets),len(self.targets))
            return result

        def create(obj,kind,*args,**kwargs):
            guid=getattr(kind,'guid64',None)
            if self.active and self.in_school():
                try:
                    self.begin_school_day(current_school_day(self.slot))
                    if not _install_school_adapters(self):
                        self.school_ready=False
                        self.error='UNSUPPORTED_CLASSROOM_ADAPTER'
                        return original_create(obj,kind,*args,**kwargs)
                except Exception as exc:
                    self.school_ready=False
                    self.error='DAY_PREFLIGHT_'+type(exc).__name__+':'+str(exc)[:100]
                    return original_create(obj,kind,*args,**kwargs)
            # EA reuses the same classroom situations in the afternoon.
            # Re-arm our already-used class/prepare gates only once per day.
            if self.active and self.in_school():
                try:
                    _m142_roll_period_if_due(self,
                        game_clock(services.time_service()))
                except Exception as exc:
                    self.m141_last_tick_error='PERIOD_'+type(exc).__name__
            # EA creates the native 09:30 prep *before* selecting the
            # students/boards; synchronize the already registered 16 first.
            # A missing/invalid registry must leave original EA untouched.
            if (self.active and self.in_school() and guid in PREP_JOBS
                    and not self.m131_sync_attempted):
                self.m131_sync_attempted=True
                try:
                    from sims4.resources import Types
                    manager=services.get_instance_manager(Types.TRAIT)
                    trait=manager.get(CLASS1_TRAIT_ID) if manager else None
                    rows=planned_changes(
                        self.lesson_classes,services.sim_info_manager(),
                        trait,Age.TEEN,Species.HUMAN)
                    self.m131_sync_result=align_roster_trait(rows,trait)
                except Exception as exc:
                    self.m131_sync_result={
                        'success':False,'changed':0,
                        'reason':'PREFLIGHT_'+type(exc).__name__}
                if not self.m131_sync_result['success']:
                    self.error='M140_TRAIT_'+self.m131_sync_result['reason']
            
            if self.active and self.in_school() and (
                    guid in PREP_JOBS or guid in LESSON_JOBS):
                if len(self.m127_timing_events)<24:
                    try:
                        clock=game_clock(services.time_service())
                    except Exception:
                        clock={'repr':'TIME_SERVICE_UNAVAILABLE'}
                    self.m127_timing_events.append({
                        'situation_guid':guid,
                        'phase':'preparation' if guid in PREP_JOBS else 'lesson',
                        'clock':clock,
                        'original_ea_create_call_observed':True,
                    })
            # M142: observe on the FIRST school situation, not exclusively
            # at 09:30 preparation: some saves already missed that event.
            if self.active and self.in_school() and self.m141_timer is None:
                _m141_start_trace(self,'school_situation')
            # M142: invite the same eight registered SimIDs into EA's
            # PREPARATION phase, before the original class lesson begins.
            # Preserve EA schedule, teachers and original fallback.
            if (self.active and self.in_school()
                    and guid in PREP_JOBS
                    and self.lesson_classes is not None):
                klass,_job=PREP_JOBS[guid]
                if klass not in self.prep_attempted:
                    if 'guest_list' in kwargs and args:
                        self.prep_refused+=1
                        return original_create(obj,kind,*args,**kwargs)
                    old=kwargs.get('guest_list',args[0] if args else None)
                    projected,reason=project_early_preparation_guests(
                        guid,old,self.lesson_classes,self.prep_jobs,
                        self.guest_cls,self.invited,self.prep_attempted)
                    if projected is None:
                        self.prep_refused+=1
                    else:
                        self.prep_attempted.add(klass)
                        self.prep_pending=klass
                        self.bound_zone=zone_schedule()[0]
                        try:
                            if 'guest_list' in kwargs:
                                native=original_create(obj,kind,*args,
                                    **dict(kwargs,guest_list=projected))
                            elif args:
                                native=original_create(
                                    obj,kind,projected,*args[1:],**kwargs)
                            else:
                                self.prep_refused+=1
                                return original_create(obj,kind,*args,**kwargs)
                            if type(native) is int and native>0:
                                self.prep_created[klass]=native
                            else:
                                self.error='EA_PREP_NO_SITUATION_ID'
                            return native
                        finally:
                            self.prep_pending=None
            if (self.active and self.in_school()
                    and guid in LESSON_JOBS
                    and self.lesson_classes is not None):
                klass,_job=LESSON_JOBS[guid]
                if klass not in self.lesson_attempted:
                    if 'guest_list' in kwargs and args:
                        self.lesson_refused+=1
                        return original_create(obj,kind,*args,**kwargs)
                    old=kwargs.get('guest_list',args[0] if args else None)
                    projected,reason=project_original_lesson_guests(
                        guid,old,self.lesson_classes,self.lesson_jobs,
                        self.guest_cls,self.invited,self.lesson_attempted)
                    if projected is not None:
                        self.lesson_attempted.add(klass)
                        self.lesson_pending=klass
                        self.bound_zone=zone_schedule()[0]
                        try:
                            if 'guest_list' in kwargs:
                                native=original_create(
                                    obj,kind,*args,
                                    **dict(kwargs,guest_list=projected))
                            elif args:
                                native=original_create(
                                    obj,kind,projected,*args[1:],**kwargs)
                            else:
                                self.lesson_refused+=1
                                return original_create(obj,kind,*args,**kwargs)
                            if type(native) is int and native>0:
                                self.lesson_created[klass]=native
                                _m141_capture(self,'native_lesson_created_C{}'.format(klass))
                                # Run only after EA accepted native lesson
                                # creation and MHS registry-to-trait alignment.
                                if (self.m140_patch_result or {}).get('applied') and (
                                        self.m131_sync_result or {}).get('success'):
                                    try:
                                        slot=str(current_slot(allow_travel=True))
                                        if slot!=self.slot:
                                            raise ValueError('SAVE_SLOT_CHANGED')
                                        roster=RosterStore(FOLDER).load(slot)
                                        groups=tuple(tuple(str(sid)
                                            for sid in roster.class_members(k))
                                            for k in (1,2))
                                        if groups!=self.lesson_classes:
                                            raise ValueError('ROSTER_CHANGED')
                                        rows=find_playable_entry(
                                            groups,services.sim_info_manager(),
                                            services.active_household())
                                        boards,status=_m131_state_evidence()
                                        if status!='TWO_VALIDATED_EA_CLASS_BOARDS':
                                            raise ValueError(status)
                                        from sims4.resources import Types
                                        affordance=services.get_instance_manager(
                                            Types.INTERACTION).get(PLAYER_CLASS_START)
                                        from interactions.context import InteractionContext
                                        from interactions.priority import Priority
                                        def make_context(sim):
                                            return InteractionContext(sim,
                                                InteractionContext.SOURCE_SCRIPT_WITH_USER_INTENT,
                                                Priority.High)
                                        report=launch_once_at_native_lesson(
                                            klass,self.m140_auto_attempted,rows,
                                            boards,affordance,make_context,
                                            queue_playable_class)
                                        self.m140_auto_reports.append(report)
                                        for outcome in report.get('results',()):
                                            _record_native_entry(self,outcome,
                                                game_clock(services.time_service()))
                                            if outcome.get('queued'):
                                                self.m142_auto_accepted.add(
                                                    str(outcome.get('sim_id')))
                                        _m141_capture(self,'auto_request_C{}'.format(klass))
                                    except Exception as exc:
                                        self.m140_auto_reports.append({
                                            'attempted':False,
                                            'reason':type(exc).__name__,
                                            'class':klass})
                            else:
                                self.error='EA_LESSON_NO_SITUATION_ID'
                            return native
                        finally:
                            self.lesson_pending=None
                    else:
                        self.lesson_refused+=1
            # M53 native staff mapping: original EA venue and cafeteria
            # situations only. Keep original EA list on unsupported forms,
            # multi-worker capacity, or failed eligibility; never invent
            # additional situations or workers.
            if (self.active and self.school_ready and self.in_school()
                    and guid in (VENUE_STAFF_SITUATION,
                                 CAFETERIA_STAFF_SITUATION)
                    # Do not reuse the same Sim in a second naturally
                    # scheduled vendor/venue situation on this school day.
                    # We have verified just one native job per role.
                    and guid not in self.staff_created
                    and self.staff_pending is None
                    and self.staff_plan.get('jobs')):
                if not ('guest_list' in kwargs and args):
                    old=kwargs.get('guest_list',args[0] if args else None)
                    prepared,staff_result=project_native_staff_guests(
                        old,guid,self.staff_plan,self.staff_jobs,
                        self.guest_cls,self.invited,
                        excluded_ids=tuple(self.classroom_membership))
                    if len(self.staff_projection_reports)<40:
                        self.staff_projection_reports.append(staff_result)
                    if prepared is not None:
                        self.staff_pending=guid
                        self.bound_zone=zone_schedule()[0]
                        try:
                            if 'guest_list' in kwargs:
                                native=original_create(obj,kind,*args,
                                    **dict(kwargs,guest_list=prepared))
                            elif args:
                                native=original_create(obj,kind,prepared,
                                    *args[1:],**kwargs)
                            else:
                                return original_create(obj,kind,*args,**kwargs)
                            if type(native) is int and native>0:
                                self.staff_created[guid]=native
                            else:
                                self.error='EA_STAFF_NO_NATIVE_SITUATION_ID'
                            return native
                        finally:
                            self.staff_pending=None
            # No native staff placement if the original guest-list contract
            # is unavailable: leave EA untouched and report the reason.
            # Original EA Core situation: ONE situation, FIVE explicit
            # user-appointed teen guest IDs; preserve teacher guests.
            if (self.active and self.in_school()
                    and getattr(kind,'guid64',None)==CORE_SITUATION
                    and self.core_created is None
                    and not self.core_pending):
                if 'guest_list' in kwargs and args:
                    self.core_refused+=1
                    return original_create(obj,kind,*args,**kwargs)
                old=kwargs.get('guest_list',args[0] if args else None)
                prepared=self.core_guest_clone(old)
                if prepared is None:
                    self.core_refused+=1
                    return original_create(obj,kind,*args,**kwargs)
                staff_projected=False
                if self.staff_plan.get('jobs'):
                    with_staff,staff_result=project_native_staff_guests(
                        prepared,CORE_SITUATION,self.staff_plan,self.staff_jobs,
                        self.guest_cls,self.invited,
                        excluded_ids=tuple(self.classroom_membership))
                    if len(self.staff_projection_reports)<40:
                        self.staff_projection_reports.append(staff_result)
                    if with_staff is not None:
                        prepared=with_staff
                        staff_projected=True
                self.core_pending=True
                # Never loosen a staff Bouncer filter unless the exact
                # selected employee was actually added to the guest list.
                self.staff_pending=(CORE_SITUATION if staff_projected else None)
                self.bound_zone=zone_schedule()[0]
                try:
                    if 'guest_list' in kwargs:
                        native=original_create(
                            obj,kind,*args,**dict(kwargs,guest_list=prepared))
                    elif args:
                        native=original_create(
                            obj,kind,prepared,*args[1:],**kwargs)
                    else:
                        self.core_refused+=1
                        return original_create(obj,kind,*args,**kwargs)
                    if type(native) is int and native>0:
                        self.core_created=native
                        if staff_projected:
                            self.staff_created[CORE_SITUATION]=native
                    else:
                        self.core_failures+=1
                        self.error='EA_CORE_NO_SITUATION_ID'
                    return native
                finally:
                    self.core_pending=False
                    self.staff_pending=None
            if (not self.active or not self.in_school()
                    or getattr(kind,'guid64',None)!=BASE_SITUATION
                    or len(self.created)>=len(self.targets)
                    or self.pending is not None):
                return original_create(obj,kind,*args,**kwargs)
            if 'guest_list' in kwargs and args:
                return original_create(obj,kind,*args,**kwargs)
            old=kwargs.get('guest_list',args[0] if args else None)
            target=next((sid for sid in self.targets
                         if sid not in self.created),None)
            if target is None:
                return original_create(obj,kind,*args,**kwargs)
            prepared=self.guest_clone(old,target)
            if prepared is None:
                self.refused+=1
                return original_create(obj,kind,*args,**kwargs)
            self.pending=target
            self.bound_zone=zone_schedule()[0]
            try:
                if 'guest_list' in kwargs:
                    call=dict(kwargs,guest_list=prepared)
                    native=original_create(obj,kind,*args,**call)
                elif args:
                    native=original_create(obj,kind,prepared,*args[1:],
                                           **kwargs)
                else:
                    self.refused+=1
                    return original_create(obj,kind,*args,**kwargs)
                if type(native) is int and native>0:
                    self.created[target]=native
                else:
                    self.error='EA_NO_SITUATION_ID'
                    # Do not advance to a different Sim on the next call
                    # until the original create returned an ID.
                return native
            except Exception as exc:
                self.error='EA_CREATE_'+type(exc).__name__
                raise
            finally:
                self.pending=None

        def request_init(obj,*args,**kwargs):
            original_init(obj,*args,**kwargs)
            if self.eligible(obj):
                try:
                    prior=obj._sim_filter
                    self._tracked[obj]=prior
                    obj._sim_filter=self.blank
                    self.filter_hits+=1
                    situ=getattr(getattr(obj,'_situation',None),
                                 'guid64',None)
                    if (situ in ROLE_JOBS and
                            getattr(getattr(obj,'_job_type',None),
                                'guid64',None) in ALL_NATIVE_JOBS):
                        self.staff_filter_hits+=1
                    if situ==CORE_SITUATION:
                        self.core_filter_hits+=1
                    if situ in LESSON_JOBS:
                        self.lesson_filter_hits+=1
                    if situ in PREP_JOBS:
                        self.prep_filter_hits+=1
                except Exception:
                    self._tracked.pop(obj,None)

        def terms(obj):
            if obj in self._tracked:
                if self.in_school() and obj._sim_filter is self.blank:
                    return ()
                prior=self._tracked.pop(obj)
                if obj._sim_filter is self.blank:
                    obj._sim_filter=prior
            return original_terms(obj)

        def clone(obj,*args,**kwargs):
            if obj in self._tracked and self.in_school():
                self.random_blocked+=1
                return None
            return original_clone(obj,*args,**kwargs)

        functions=((manager,'create_situation',create),
                   (request,'__init__',request_init),
                   (request,'get_additional_filter_terms',terms),
                   (request,'clone_for_replace',clone),
                   (day,'get_long_term_situation_count',classmethod(count)))
        for _,_,fn in functions:
            f=fn.__func__ if isinstance(fn,classmethod) else fn
            f._mhs127_hook=True
        changed=[]
        try:
            for owner,name,fn in functions:
                setattr(owner,name,fn)
                changed.append((owner,name))
        except Exception:
            for owner,name in reversed(changed):
                setattr(owner,name,originals[(owner,name)])
            return False
        self.previous=originals
        self.wrappers={(owner,name):fn for owner,name,fn in functions}
        self.active=True
        return True

    def stop(self):
        _m141_stop_trace(self)
        if not self.active:
            return False
        callbacks=(self.classroom_guard_undo,self.m145_patch_undo,self.m140_patch_undo)
        if any(callable(getattr(fn,'can_restore',None)) and not fn.can_restore()
               for fn in callbacks if fn is not None):
            self.school_ready=False
            self.error='CLASSROOM_ADAPTER_RESTORE_CONFLICT'
            return False
        if any(owner.__dict__.get(name) is not fn
               for (owner,name),fn in self.wrappers.items()):
            self.error='THIRD_PARTY_RESTORE_CONFLICT'
            return False
        for req,prior in tuple(self._tracked.items()):
            if getattr(req,'_sim_filter',None) is self.blank:
                req._sim_filter=prior
        self._tracked.clear()
        if self.classroom_guard_undo is not None:
            if not self.classroom_guard_undo():
                self.error='NPC_BOARD_GUARD_RESTORE_CONFLICT'
                return False
            self.classroom_guard_undo=None
        # Undo M145 subject changes before M139 restores the snippet.
        if self.m145_patch_undo is not None:
            try:
                if not self.m145_patch_undo():
                    self.error='M145_SUBJECT_RESTORE_CONFLICT'
                    return False
                self.m145_patch_undo=None
            except Exception as exc:
                self.error='M145_SUBJECT_RESTORE_'+type(exc).__name__
                return False
        if self.m140_patch_undo is not None:
            try:
                if not self.m140_patch_undo():
                    self.error='BOARD_TEST_RESTORE_CONFLICT'
                    return False
                self.m140_patch_undo=None
            except Exception as exc:
                self.error='BOARD_TEST_RESTORE_'+type(exc).__name__
                return False
        for (owner,name),prior in self.previous.items():
            setattr(owner,name,prior)
        self.active=False
        return True

    def native_job_status(self,sid,situation_id):
        if not self.in_school():
            return 'FUORI_LICEO'
        try:
            manager=services.get_zone_situation_manager()
            situation=manager.get(situation_id) if manager else None
            if situation is None:
                return 'SITUAZIONE_SCOMPARSA'
            if getattr(situation,'guid64',None)!=BASE_SITUATION:
                return 'SITUAZIONE_ERRATA'
            jobs=tuple(situation.all_jobs_gen())
            selected=[job for job in jobs
                      if getattr(job,'guid64',None)==BASE_JOB]
            if len(selected)!=1:
                return 'RUOLO_BASE_NON_UNICO'
            sims=tuple(situation.all_sims_in_job_gen(selected[0]))
            ids=set()
            for sim in sims:
                a=getattr(sim,'sim_id',None)
                b=getattr(sim,'id',None)
                if a is not None and b is not None and a!=b:
                    return 'ID_AMBIGUO'
                ident=a if a is not None else b
                if type(ident) is not int:
                    return 'ID_NON_VALIDO'
                ids.add(str(ident))
            if ids=={sid}:
                return 'PRESENTE'
            return 'ALTRO_SIM' if ids else 'VUOTO'
        except Exception as exc:
            return 'LETTURA_'+type(exc).__name__

    def core_job_status(self,jobid,sid):
        if self.core_created is None:
            return 'NON_CREATA'
        if not self.in_school():
            return 'FUORI_LICEO'
        try:
            manager=services.get_zone_situation_manager()
            situation=manager.get(self.core_created) if manager else None
            if situation is None:
                return 'SITUAZIONE_SCOMPARSA'
            if getattr(situation,'guid64',None)!=CORE_SITUATION:
                return 'SITUAZIONE_ERRATA'
            jobs=[job for job in tuple(situation.all_jobs_gen())
                  if getattr(job,'guid64',None)==jobid]
            if len(jobs)!=1:
                return 'RUOLO_CORE_NON_UNICO'
            ids=set()
            for sim in tuple(situation.all_sims_in_job_gen(jobs[0])):
                a=getattr(sim,'sim_id',None)
                b=getattr(sim,'id',None)
                if a is not None and b is not None and a!=b:
                    return 'ID_AMBIGUO'
                value=a if a is not None else b
                if type(value) is not int:
                    return 'ID_NON_VALIDO'
                ids.add(str(value))
            return ('PRESENTE' if ids=={sid}
                    else ('ALTRO_SIM' if ids else 'VUOTO'))
        except Exception as exc:
            return 'LETTURA_'+type(exc).__name__

    def lesson_report(self):
        observations=[]
        for klass in (1,2):
            situation_id=self.lesson_created.get(klass)
            if situation_id is None:
                observations.append('C{}:NON_INTERVENUTA'.format(klass))
                continue
            if not self.in_school():
                observations.append('C{}:FUORI_LICEO'.format(klass))
                continue
            try:
                situation=services.get_zone_situation_manager().get(
                    situation_id)
                if situation is None:
                    observations.append('C{}:SITUAZIONE_ASSENTE'.format(klass))
                    continue
                guid=getattr(situation,'guid64',None)
                expected=LESSON_JOBS.get(guid)
                if expected is None or expected[0]!=klass:
                    observations.append('C{}:SITUAZIONE_ERRATA'.format(klass))
                    continue
                jobs=[j for j in situation.all_jobs_gen()
                      if getattr(j,'guid64',None)==expected[1]]
                if len(jobs)!=1:
                    observations.append('C{}:JOB_MANCANTE'.format(klass))
                    continue
                ids=set(str(getattr(sim,'sim_id',getattr(sim,'id',None)))
                        for sim in situation.all_sims_in_job_gen(jobs[0]))
                chosen=set(self.lesson_classes[klass-1])
                observations.append('C{}:{}/8,extra={}'.format(
                    klass,len(ids&chosen),len(ids-chosen)))
            except Exception as exc:
                observations.append('C{}:LETTURA_{}'.format(
                    klass,type(exc).__name__))
        return '|'.join(observations)

    def report(self):
        checked=[(sid,self.native_job_status(sid,sit))
                 for sid,sit in self.created.items()]
        present=sum(status=='PRESENTE' for _,status in checked)
        core_checks=[(jobid,self.core_job_status(jobid,self.pinned[jobid]))
                     for jobid in CORE_JOBS]
        core_present=sum(status=='PRESENTE' for _,status in core_checks)
        missing=tuple(sid for sid,status in checked if status!='PRESENTE')
        core_missing=tuple(str(job) for job,status in core_checks
                           if status!='PRESENTE')
        return ('M142 active={} EA_base_created={}/8 EA_base_present={}/8 '
                'EA_core_created={}/1 EA_core_present={}/5 '
                'prep_create={}/2 prep_filter={} prep_refused={} '
                'lezioni_proiettate={}/2 lezione_job={} '
                'count_override={} native_count={} filter={} '
                'core_filter={} lesson_filter={} blocked_random={} '
                'refused_base={} refused_core={} refused_lessons={} '
                'missing_base={} missing_core_jobs={} '
                'error={}'.format(
                    self.active,len(self.created),present,
                    int(self.core_created is not None),core_present,
                    len(self.prep_created),self.prep_filter_hits,
                    self.prep_refused,
                    len(self.lesson_created),self.lesson_report(),
                    self.base_count_overrides,self.base_count_last,
                    self.filter_hits,self.core_filter_hits,
                    self.lesson_filter_hits,self.random_blocked,
                    self.refused,self.core_refused,self.lesson_refused,
                    ','.join(missing) or 'none',
                    ','.join(core_missing) or 'none',self.error or 'none'))


def arm_m127():
    global _RUNTIME
    # Changing class members must NEVER require changing Python code or
    # restarting the whole game. On the next pre-school arm, re-read the
    # current save registry and pinned Core roles and refresh the hook
    # session only if its entire verified enrollment really changed.
    # Never rebuild native situations during an active school day.
    try:
        zone,schedule=zone_schedule()
        if zone is None or schedule in SCHOOL_SCHEDULES:
            return 'M147 BLOCCATA: armare da casa prima della scuola'
        slot,targets,pinned=registered_eight()
        roster=RosterStore(FOLDER).load(slot)
        selected=tuple(tuple(str(s) for s in roster.class_members(i))
                       for i in (1,2))
        if _RUNTIME is not None and _RUNTIME.active:
            if _RUNTIME.in_school():
                return 'M147 GIORNATA IN CORSO: iscrizioni dal prossimo giorno'
            if slot!=_RUNTIME.slot:
                return 'M147 BLOCCATA: cambiare salvataggio richiede nuovo avvio'
            required=roster_rearm_required(
                _RUNTIME.lesson_classes,_RUNTIME.targets,_RUNTIME.pinned,
                selected,targets,pinned,zone!=_RUNTIME.home_zone)
            if not required:
                return 'M147 GIA ATTIVA: registro corrente confermato'
            if not _RUNTIME.stop():
                return 'M147 RICARICA BLOCCATA: '+_RUNTIME.error
            _RUNTIME=None
        from situations.situation_manager import SituationManager
        from situations.bouncer.bouncer_request import BouncerRequest
        from situations.situation_guest_list import (
            SituationGuestInfo,SituationInvitationPurpose)
        from venues.weekly_schedule_zone_director import WeeklyScheduleDay
        from sims4.resources import Types
        day=next((c for c in WeeklyScheduleDay.__mro__
                  if isinstance(c.__dict__.get(
                      'get_long_term_situation_count'),classmethod)),None)
        job_manager=services.get_instance_manager(Types.SITUATION_JOB)
        job=job_manager.get(BASE_JOB)
        core_jobs={guid:job_manager.get(guid) for guid in CORE_JOBS}
        blank=TunableSimFilter.BLANK_FILTER
        if (day is None or job is None
                or any(j is None or getattr(j,'guid64',None)!=guid
                       for guid,j in core_jobs.items())
                or getattr(job,'guid64',None)!=BASE_JOB
                or blank is None
                or not callable(getattr(blank,'get_filter_terms',None))):
            return 'M142 BLOCCATA: tuning EA non compatibile'
        trial=ThirteenNPCController(slot,targets,pinned,zone,SituationManager,
            BouncerRequest,day,job,core_jobs,blank,SituationGuestInfo,
            SituationInvitationPurpose.INVITED)
        if (len(selected[0])!=8 or len(selected[1])!=8
                or len(set(selected[0]+selected[1]))!=16):
            return 'M147 BLOCCATA: registro classi 1 e 2 non valido'
        trial.lesson_classes=selected
        def read_staff_plan(active_slot,active_groups):
            from mhs53_staff_store import StaffStore
            saved=StaffStore(FOLDER).load(active_slot)
            return load_native_staff_plan(
                saved,services.sim_info_manager(),Species.HUMAN,
                (Age.YOUNGADULT,Age.ADULT,Age.ELDER),
                enrolled_ids=tuple(sid for group in active_groups
                                   for sid in group))
        trial.staff_plan_loader=read_staff_plan
        try:
            trial.staff_plan=read_staff_plan(slot,selected)
        except Exception as exc:
            trial.staff_plan={'jobs':{},'blocked':{
                'all':'STAFF_PLAN_'+type(exc).__name__},
                'roster_read_only':True}
        job_mgr=services.get_instance_manager(Types.SITUATION_JOB)
        trial.staff_jobs={guid:job_mgr.get(guid) for guid in ALL_NATIVE_JOBS}
        trial.lesson_jobs={j:job_mgr.get(j)
                           for j in set(x[1] for x in LESSON_JOBS.values())}
        trial.prep_jobs={j:job_mgr.get(j)
                         for j in set(x[1] for x in PREP_JOBS.values())}
        if any(v is None or getattr(v,'guid64',None)!=j
               for j,v in tuple(trial.lesson_jobs.items())+tuple(trial.prep_jobs.items())):
            return 'M142 BLOCCATA: originali job lezione EA assenti'
        if not trial.install():
            return 'M142 BLOCCATA: owner EA modificato o non disponibile'
        # Global EA/Zerbu tuning must remain untouched outside high school.
        # Install transactionally at verified school entry, before preparation.
        trial.m140_patch_result={'applied':False,'reason':'WAITING_FOR_SCHOOL_ZONE'}
        trial.m145_patch_result={'applied':False,'reason':'WAITING_FOR_SCHOOL_ZONE'}
        _RUNTIME=trial
        _m141_start_watcher(trial)
        return 'M148 PRONTA: entrambe aule e monitor leggero doppio orologio'
    except Exception as exc:
        return 'M142 NON ATTIVA: '+type(exc).__name__+': '+str(exc)[:100]


@sims4.commands.Command('mhs148.arm',
    command_type=sims4.commands.CommandType.Live)
def m127arm(_connection=None):
    sims4.commands.output(arm_m127(),_connection)


@sims4.commands.Command('mhs148.status',
    command_type=sims4.commands.CommandType.Live)
def m127status(_connection=None):
    sims4.commands.output(
        _RUNTIME.report() if _RUNTIME is not None
        else 'M142 non attiva',_connection)


@sims4.commands.Command('mhs148.stop',
    command_type=sims4.commands.CommandType.Live)
def m127stop(_connection=None):
    sims4.commands.output(
        ('M142 RIPRISTINATA' if _RUNTIME.stop()
         else 'M142 RIPRISTINO BLOCCATO: '+_RUNTIME.error)
        if _RUNTIME is not None else 'M142 non attiva',_connection)

def _snapshot_classes(phase):
    if _RUNTIME is None or not _RUNTIME.active:
        return 'M142 CLASSI: attivare da casa prima della scuola'
    if not _RUNTIME.in_school():
        return 'M142 CLASSI: non sei al liceo nel salvataggio corretto'
    try:
        slot=str(current_slot(allow_travel=True))
        if slot!=_RUNTIME.slot:
            return 'M142 CLASSI: salvataggio diverso, controllo bloccato'
        roster=RosterStore(FOLDER).load(slot)
        groups=tuple(tuple(str(s) for s in roster.class_members(i))
                     for i in (1,2))
        household=services.active_household()
        playable=tuple(str(s.sim_id) for s in household.sim_info_gen()
                       if getattr(s,'age',None)==Age.TEEN
                       and getattr(s,'species',None)==Species.HUMAN)
        result=school_classroom_snapshot(
            groups,playable,services.sim_info_manager(),
            services.get_zone_situation_manager(),
            Age.TEEN,Species.HUMAN,phase)
        count1=result.get('native_class1_job_count',0)
        count2=result.get('native_class2_job_count',0)
        playable_count=len(result.get('playable_instanced_ids',()))
        missing1=len(result.get('missing_class1_job_ids',groups[0]))
        missing2=len(result.get('missing_class2_job_ids',groups[1]))
        wrong=len(result.get('wrong_class_memberships',()))
        extras=len(result.get('extra_nonregistered_native_class_memberships',()))
        # The word "lezioni" indicates native EA situation job
        # membership, never physical seats or teacher identity.
        return ('M142 CLASSI phase={} EA_classe1={}/8 EA_classe2={}/8 '
                'giocabili_istanziati={}/3 iscritti_istanziati={}/16 '
                'mancanti_C1={} mancanti_C2={} classe_sbagliata={} '
                'extra_nelle_lezioni={} stato={} seduti=NON_VERIFICATO'.format(
                    phase,count1,count2,playable_count,
                    result.get('enrolled_instanced_count',0),
                    missing1,missing2,wrong,extras,result['status']))
    except Exception as exc:
        return 'M142 CLASSI: LETTURA_EA_'+type(exc).__name__


@sims4.commands.Command('mhs148.classi',
    command_type=sims4.commands.CommandType.Live)
def m127classi(_connection=None):
    sims4.commands.output(_snapshot_classes('lesson'),_connection)


@sims4.commands.Command('mhs148.prepara',
    command_type=sims4.commands.CommandType.Live)
def m127prepara(_connection=None):
    sims4.commands.output(_snapshot_classes('prepare'),_connection)

def _capture_actions():
    if _RUNTIME is None or not _RUNTIME.active:
        return None,'M142: attivare da casa prima della scuola'
    if not _RUNTIME.in_school():
        return None,'M142: devi essere al liceo'
    try:
        slot=str(current_slot(allow_travel=True))
        if slot!=_RUNTIME.slot:
            return None,'M142: save slot diverso'
        roster=RosterStore(FOLDER).load(slot)
        classes=tuple(tuple(str(s) for s in roster.class_members(i))
                      for i in (1,2))
        result=inspect_sixteen_lesson_actions(
            classes,services.sim_info_manager(),
            services.get_zone_situation_manager(),
            Age.TEEN,Species.HUMAN)
        return result,None
    except Exception as exc:
        return None,'M142: errore lettura '+type(exc).__name__


@sims4.commands.Command('mhs148.azioni',
    command_type=sims4.commands.CommandType.Live)
def m127actions(_connection=None):
    report,error=_capture_actions()
    if error is not None:
        sims4.commands.output(error,_connection)
        return
    sims4.commands.output(
        'M142 AZIONI: job_classe={}/16 azioni_in_corso={} '
        'senza_azione={} stato={} NESSUN_SIM_MODIFICATO'.format(
            report.get('native_correct_class_job_count',0),
            report.get('with_running_action',0),
            len(report.get('no_running_action',())),
            report['status']),_connection)


@sims4.commands.Command('mhs148.dettagli',
    command_type=sims4.commands.CommandType.Live)
def m127details(_connection=None):
    report,error=_capture_actions()
    if error is not None:
        sims4.commands.output(error,_connection)
        return
    import json
    os.makedirs(FOLDER,exist_ok=True)
    filename=os.path.join(FOLDER,'MHS_CLASSROOM_CONTROL_LEZIONI_RUOLI_AZIONI.json')
    with open(filename,'w',encoding='utf-8') as file:
        json.dump(report,file,indent=2,ensure_ascii=False)
    sims4.commands.output(
        'M142: creato MHS_CLASSROOM_CONTROL_LEZIONI_RUOLI_AZIONI.json (16 Sim). '
        'Nessuna azione del Sim modificata.',_connection)

# M142 manual opt-in recovery: a single known off-task mirror interaction.
_M140_ATTEMPTED=set()
_M140_ZONE_KEY=None


def _m125_candidates(perform):
    global _M140_ZONE_KEY
    if _RUNTIME is None or not _RUNTIME.active:
        return 'M142 RECUPERO: attiva mhs148.arm a casa'
    if not _RUNTIME.in_school():
        return 'M142 RECUPERO: usa al liceo durante la lezione'
    try:
        current_zone=services.current_zone()
        zone_id=getattr(current_zone,'id',None)
        if _M140_ZONE_KEY is None:
            _M140_ZONE_KEY=(str(_RUNTIME.slot),zone_id)
        if _M140_ZONE_KEY!=(str(_RUNTIME.slot),zone_id):
            return 'M142 RECUPERO: zona cambiata; riavvio necessario'
        roster=RosterStore(FOLDER).load(_RUNTIME.slot)
        classes=tuple(tuple(str(s) for s in roster.class_members(klass))
                      for klass in (1,2))
        if (len(classes[0])!=8 or len(classes[1])!=8
                or len(set(classes[0]+classes[1]))!=16):
            return 'M142 RECUPERO: registro 2x8 non valido'
        manager=services.sim_info_manager()
        native=services.get_zone_situation_manager()
        from interactions.interaction_finisher import FinishingType
        rows=[]
        for klass,group in enumerate(classes,1):
            for sid in group:
                info=manager.get(int(sid))
                sim=info.get_sim_instance() if info is not None else None
                if perform:
                    success,reason=recover_one(
                        sid,klass,info,sim,native,Age.TEEN,Species.HUMAN,
                        _M140_ATTEMPTED,FinishingType.SITUATIONS)
                    if success or reason=='ALREADY_ATTEMPTED':
                        rows.append('{}:{}'.format(sid,reason))
                else:
                    eligible,reason,_=inspect_candidate(
                        sid,klass,info,sim,native,Age.TEEN,Species.HUMAN,
                        _M140_ATTEMPTED)
                    if eligible:
                        rows.append('{}:{}'.format(sid,reason))
        return ('M142 {} candidati={} {} — NON prova la seduta'.format(
            'RIPRESA' if perform else 'PRECONTROLLO',
            len(rows),'; '.join(rows) if rows else 'nessun candidato'))
    except Exception as exc:
        return 'M142 RECUPERO LETTURA_EA_'+type(exc).__name__


@sims4.commands.Command('mhs148.candidati',
    command_type=sims4.commands.CommandType.Live)
def m127candidates(_connection=None):
    sims4.commands.output(_m125_candidates(False),_connection)


@sims4.commands.Command('mhs148.rientro',
    command_type=sims4.commands.CommandType.Live)
def m127recover(_connection=None):
    sims4.commands.output(_m125_candidates(True),_connection)

_M140_TIMED_SNAPSHOTS=[]


def _m127_capture_timing():
    if _RUNTIME is None or not _RUNTIME.active:
        return None,'M142: attivare da casa'
    if not _RUNTIME.in_school():
        return None,'M142: comando solo al liceo'
    try:
        slot=str(current_slot(allow_travel=True))
        if slot!=_RUNTIME.slot:
            return None,'M142: save slot diverso'
        roster=RosterStore(FOLDER).load(slot)
        groups=tuple(tuple(str(s) for s in roster.class_members(i))
                      for i in (1,2))
        if (len(groups[0])!=8 or len(groups[1])!=8 or
                len(set(groups[0]+groups[1]))!=16):
            return None,'M142: registro 2x8 non valido'
        result=timed_roster_snapshot(
            groups,services.sim_info_manager(),
            services.get_zone_situation_manager(),
            services.time_service(),Age.TEEN,Species.HUMAN)
        result['observed_ea_situation_creations']=tuple(
            _RUNTIME.m127_timing_events)
        return result,None
    except Exception as exc:
        return None,'M142: errore '+type(exc).__name__


@sims4.commands.Command('mhs148.tempo',
    command_type=sims4.commands.CommandType.Live)
def m127tempo(_connection=None):
    import json
    result,error=_m127_capture_timing()
    if error is not None:
        sims4.commands.output(error,_connection)
        return
    if len(_M140_TIMED_SNAPSHOTS)>=8:
        sims4.commands.output(
            'M142: massimo 8 rilevazioni; file gia completo',_connection)
        return
    _M140_TIMED_SNAPSHOTS.append(result)
    os.makedirs(FOLDER,exist_ok=True)
    file=os.path.join(FOLDER,'MHS_CLASSROOM_CONTROL_ORARI_PERCORSI_EA.json')
    with open(file,'w',encoding='utf-8') as stream:
        json.dump({'kind':'M140_MULTI_TIME_SCHOOL_ROUTE',
                   'measurements':_M140_TIMED_SNAPSHOTS,
                   'ea_situation_creations':_RUNTIME.m127_timing_events,
                   'requires_visual_seating_verification':True,
                   'changes_to_school_times':False},
                  stream,indent=2,ensure_ascii=False)
    sims4.commands.output(
        'M142 TEMPO rilevazione={}/8 job_classe={}/16 '
        'creazioni_prep={} creazioni_lezione={} '
        'file=MHS_CLASSROOM_CONTROL_ORARI_PERCORSI_EA.json'.format(
            len(_M140_TIMED_SNAPSHOTS),result['school_job_count'],
            sum(x['phase']=='preparation'
                for x in _RUNTIME.m127_timing_events),
            sum(x['phase']=='lesson'
                for x in _RUNTIME.m127_timing_events)),
        _connection)

def _m128_trait_context():
    if _RUNTIME is None or not _RUNTIME.active:
        return None,None,'M142: eseguire mhs148.arm a casa'
    if not _RUNTIME.in_school():
        return None,None,'M142: utilizzare al liceo'
    try:
        slot=str(current_slot(allow_travel=True))
        if slot!=_RUNTIME.slot:
            return None,None,'M142: save slot cambiato'
        roster=RosterStore(FOLDER).load(slot)
        groups=tuple(tuple(str(s) for s in roster.class_members(i))
                     for i in (1,2))
        import sims4.resources
        trait_manager=services.get_instance_manager(sims4.resources.Types.TRAIT)
        trait=trait_manager.get(CLASS1_TRAIT_ID)
        rows=planned_changes(groups,services.sim_info_manager(),
                             trait,Age.TEEN,Species.HUMAN)
        return rows,trait,None
    except Exception as exc:
        return None,None,'M142: validazione fallita '+type(exc).__name__


@sims4.commands.Command('mhs148.verifica',
    command_type=sims4.commands.CommandType.Live)
def m128verifica(_connection=None):
    import json
    rows,trait,error=_m128_trait_context()
    if error:
        sims4.commands.output(error,_connection)
        return
    missing=[r for r in rows if r['requires_change']]
    try:
        os.makedirs(FOLDER,exist_ok=True)
        filepath=os.path.join(FOLDER,'MHS_CLASSROOM_CONTROL_TRATTI_EA.json')
        with open(filepath,'w',encoding='utf-8') as stream:
            json.dump({'kind':'M140_EA_CLASS1_TRAIT_AUDIT',
                'ea_trait_guid':CLASS1_TRAIT_ID,
                'student_count':len(rows),
                'mismatch_count':len(missing),
                'rows':public_rows(rows),
                'mutated':False,'seating_verified':False},
                stream,indent=2,ensure_ascii=False)
    except Exception as exc:
        sims4.commands.output('M142 errore report '+type(exc).__name__,
                             _connection)
        return
    sims4.commands.output(
        'M142 VERIFICA: iscritti=16 tratti_errati={} '
        'Classe1={} Classe2={} '
        'file=MHS_CLASSROOM_CONTROL_TRATTI_EA.json NESSUNA_MODIFICA'.format(
            len(missing),
            sum(1 for r in missing if r['registered_class']==1),
            sum(1 for r in missing if r['registered_class']==2)),
        _connection)


@sims4.commands.Command('mhs148.allinea',
    command_type=sims4.commands.CommandType.Live)
def m128allinea(_connection=None):
    rows,trait,error=_m128_trait_context()
    if error:
        sims4.commands.output(error,_connection)
        return
    result=align_roster_trait(rows,trait)
    sims4.commands.output(
        'M142 ALLINEA: successo={} corretti={} motivo={} '
        'rollback={}; NON GARANTISCE SEDUTA ALLE 10'.format(
            result['success'],result['changed'],result['reason'],
            result.get('rollback_verified','non_necessario')),
        _connection)


@sims4.commands.Command('mhs148.aula',
    command_type=sims4.commands.CommandType.Live)
def m128aula(_connection=None):
    """Read-only classroom target + posture export; no routing mutation."""
    import json
    if _RUNTIME is None or not _RUNTIME.active or not _RUNTIME.in_school():
        sims4.commands.output(
            'M142 AULA: attiva a casa e vai al liceo',_connection)
        return
    try:
        slot=str(current_slot(allow_travel=True))
        if slot!=_RUNTIME.slot:
            raise ValueError('SAVE_SLOT_CHANGED')
        roster=RosterStore(FOLDER).load(slot)
        groups=tuple(tuple(str(s) for s in roster.class_members(i))
                     for i in (1,2))
        import sims4.resources
        manager=services.get_instance_manager(sims4.resources.Types.TRAIT)
        trait=manager.get(CLASS1_TRAIT_ID) if manager else None
        report=audit_classroom_targets(
            groups,services.sim_info_manager(),trait)
        report['clock']=game_clock(services.time_service())
        report['note']='posture Sit alone does not prove classroom desk'
        os.makedirs(FOLDER,exist_ok=True)
        filename=os.path.join(FOLDER,'MHS_CLASSROOM_CONTROL_LAVAGNE_POSTURE_EA.json')
        with open(filename,'w',encoding='utf-8') as stream:
            json.dump(report,stream,indent=2,ensure_ascii=False)
        sims4.commands.output(
            'M142 AULA: studenti={} tratti_errati={} '
            'lavagne_condivise={} NESSUNA_MODIFICA '
            'file=MHS_CLASSROOM_CONTROL_LAVAGNE_POSTURE_EA.json'.format(
                report['count'],report['trait_mismatches'],
                len(report['board_ids_targeted_by_both_classes'])),
            _connection)
    except Exception as exc:
        sims4.commands.output(
            'M142 AULA: errore '+type(exc).__name__,_connection)

_M140_ANCHORS=None
_M140_READBACKS=[]


@sims4.commands.Command('mhs148.posti',
    command_type=sims4.commands.CommandType.Live)
def m130posti(_connection=None):
    """Read only. Compare current 16 real seats and live whiteboards."""
    import json
    global _M140_ANCHORS
    if _RUNTIME is None or not _RUNTIME.active or not _RUNTIME.in_school():
        sims4.commands.output('M142 POSTI: attiva a casa e vai al liceo',
                             _connection)
        return
    try:
        slot=str(current_slot(allow_travel=True))
        if slot!=_RUNTIME.slot:
            raise ValueError('SAVE_SLOT_CHANGED')
        roster=RosterStore(FOLDER).load(slot)
        groups=tuple(tuple(str(sid) for sid in roster.class_members(k))
                     for k in (1,2))
        import sims4.resources
        mgr=services.get_instance_manager(sims4.resources.Types.TRAIT)
        trait=mgr.get(CLASS1_TRAIT_ID) if mgr else None
        sims=services.sim_info_manager()
        audit=audit_classroom_targets(groups,sims,trait)
        for row in audit['students']:
            info=sims.get(int(row['sim_id']))
            row['is_selectable']=(
                getattr(info,'is_selectable',None) if info else None)
        anchors,source=derive_board_anchors(audit,_M140_ANCHORS)
        if source=='OBSERVED_SEPARATE_CLASS_BOARDS':
            _M140_ANCHORS=anchors
        result=evaluate_physical_seats(audit,anchors,source)
        result['clock']=game_clock(services.time_service())
        result['trait_mismatches']=audit['trait_mismatches']
        result['save_slot']=slot
        result['uses_situations_as_observed_no_early_seating_claim']=True
        if len(_M140_READBACKS)>=8:
            _M140_READBACKS.pop(0)
        _M140_READBACKS.append(result)
        os.makedirs(FOLDER,exist_ok=True)
        with open(os.path.join(
                FOLDER,'MHS_CLASSROOM_CONTROL_POSTI_AULE_EA.json'),
                'w',encoding='utf-8') as stream:
            json.dump({'kind':'M140_MULTI_TIME_PHYSICAL_SEAT_AUDIT',
                       'samples':_M140_READBACKS,
                       'game_mutations':0,
                       'classroom_8_plus_8_seated_not_guaranteed':True},
                      stream,indent=2,ensure_ascii=False)
        c=result['counts']
        sims4.commands.output(
            'M142 POSTI: misure={} tratti_errati={} '
            'posti_vicino_classe={} posti_in_altra_aula={} '
            'in_piedi={} incerti={} bersagli_sbagliati={} '
            'mappa={} NESSUNA_MODIFICA'.format(
                len(_M140_READBACKS),result['trait_mismatches'],
                c['seat_near_registered_board'],
                c['seat_near_other_class_board'],
                c['not_seated'],c['seat_ambiguous'],
                c['known_wrong_live_board'],source),
            _connection)
    except Exception as exc:
        sims4.commands.output(
            'M142 POSTI: errore '+type(exc).__name__,_connection)


def _m131_state_evidence():
    """No guessing: require both EA board states and exactly one object each."""
    from sims4.resources import Types
    state_type=getattr(Types,'OBJECT_STATE',None)
    mgr=services.get_instance_manager(state_type) if state_type else None
    state1=mgr.get(CLASS1_WHITEBOARD_TRUE) if mgr else None
    state2=mgr.get(CLASS2_WHITEBOARD_TRUE) if mgr else None
    manager=services.object_manager()
    objects=tuple(manager.values()) if manager else ()
    return safe_class_board_candidates(
        objects,'object_HighSchool_Active_Whiteboard',state1,state2)


@sims4.commands.Command('mhs148.giocabili',
    command_type=sims4.commands.CommandType.Live)
def m131giocabili(_connection=None):
    """Explicit experimental EA player lesson push; never teleport."""
    if _RUNTIME is None or not _RUNTIME.active or not _RUNTIME.in_school():
        sims4.commands.output('M142 GIOCABILI: attiva a casa e vai a scuola',
                             _connection)
        return
    try:
        if str(current_slot(allow_travel=True))!=_RUNTIME.slot:
            raise ValueError('SAVE_SLOT_CHANGED')
        roster=RosterStore(FOLDER).load(_RUNTIME.slot)
        groups=tuple(tuple(str(s) for s in roster.class_members(k))
                     for k in (1,2))
        played=find_playable_entry(
            groups,services.sim_info_manager(),services.active_household())
        boards,status=_m131_state_evidence()
        if status!='TWO_VALIDATED_EA_CLASS_BOARDS':
            sims4.commands.output(
                'M142 GIOCABILI: BLOCCATO '+status+'; NESSUNO SPOSTAMENTO',
                _connection)
            return
        from sims4.resources import Types
        interaction_manager=services.get_instance_manager(Types.INTERACTION)
        affordance=interaction_manager.get(PLAYER_CLASS_START)
        from interactions.context import InteractionContext
        from interactions.priority import Priority
        def context(sim):
            return InteractionContext(
                sim,InteractionContext.SOURCE_SCRIPT_WITH_USER_INTENT,
                Priority.High)
        result=queue_playable_class(played,boards,affordance,context)
        for row in result.get('results',()):
            sims4.commands.output(
                'M142 SIM {} classe={} '.format(
                    row['sim_id'],next((x['registered_class']
                    for x in played if x['sim_id']==row['sim_id']),'?'))+
                'accettata={} motivo={}'.format(
                    row['queued'],row['reason']),_connection)
        sims4.commands.output(
            'M142 GIOCABILI: EA accettati={}/{} '
            'NON GARANTISCE SEDUTA ALLE 10'.format(
                sum(x['queued'] for x in result.get('results',())),
                len(played)),_connection)
    except Exception as exc:
        sims4.commands.output(
            'M142 GIOCABILI: errore '+type(exc).__name__,_connection)


@sims4.commands.Command('mhs148.sync',
    command_type=sims4.commands.CommandType.Live)
def m131sync(_connection=None):
    """Read status of automatic class trait alignment on first EA prep."""
    if _RUNTIME is None or not _RUNTIME.active:
        sims4.commands.output('M142 SYNC: non attiva',_connection)
        return
    data=_RUNTIME.m131_sync_result
    sims4.commands.output(
        'M142 SYNC: preparazione_rilevata={} esito={} '
        'nessuna_ripetizione_manual_obbligatoria'.format(
            _RUNTIME.m131_sync_attempted,
            data if data else 'NON_ESEGUITO'),_connection)


@sims4.commands.Command('mhs148.causa',
    command_type=sims4.commands.CommandType.Live)
def m132causa(_connection=None):
    """Read-only diagnostic of EA player-class test and role buff."""
    import json
    if _RUNTIME is None or not _RUNTIME.active or not _RUNTIME.in_school():
        sims4.commands.output('M142 CAUSA: armare da casa e andare al liceo',
                             _connection)
        return
    try:
        if str(current_slot(allow_travel=True))!=_RUNTIME.slot:
            raise ValueError('SAVE_SLOT_CHANGED')
        roster=RosterStore(FOLDER).load(_RUNTIME.slot)
        groups=tuple(tuple(str(sid) for sid in roster.class_members(k))
                     for k in (1,2))
        played=find_playable_entry(groups,services.sim_info_manager(),
                                   services.active_household())
        boards,reason=_m131_state_evidence()
        if reason!='TWO_VALIDATED_EA_CLASS_BOARDS':
            sims4.commands.output('M142 CAUSA: impossibile mappare lavagne '+
                                 reason,_connection)
            return
        from sims4.resources import Types
        affordance=services.get_instance_manager(Types.INTERACTION).get(
            PLAYER_CLASS_START)
        buff=services.get_instance_manager(Types.BUFF).get(PLAYER_ROLE_BUFF)
        from interactions.context import InteractionContext
        from interactions.priority import Priority
        def context(sim):
            return InteractionContext(
                sim,InteractionContext.SOURCE_SCRIPT_WITH_USER_INTENT,
                Priority.High)
        report=inspect_native_player_tests(
            played,boards,affordance,buff,context)
        report['clock']=game_clock(services.time_service())
        report['save_slot']=_RUNTIME.slot
        os.makedirs(FOLDER,exist_ok=True)
        with open(os.path.join(
                FOLDER,'MHS_CLASSROOM_CONTROL_CAUSA_RIFIUTO_EA.json'),
                'w',encoding='utf-8') as stream:
            json.dump(report,stream,indent=2,ensure_ascii=False)
        for row in report['students']:
            sims4.commands.output(
                'M142 SIM {} classe={} buff={} esito={} test={} motivo={}'.format(
                row['sim_id'],row['registered_class'],
                row['player_role_buff'],row.get('status'),
                row.get('test_passed','NON_DISPONIBILE'),
                row.get('reason',row.get('test_error','n/d'))[:90]),
                _connection)
        sims4.commands.output(
            'M142 CAUSA: file=MHS_CLASSROOM_CONTROL_CAUSA_RIFIUTO_EA.json '
            'NESSUNA MODIFICA AL GIOCO',_connection)
    except Exception as exc:
        sims4.commands.output(
            'M142 CAUSA: errore '+type(exc).__name__,_connection)


@sims4.commands.Command('mhs148.ruoli',
    command_type=sims4.commands.CommandType.Live)
def m134ruoli(_connection=None):
    """Read-only native EA job membership for each playable class."""
    import json
    if _RUNTIME is None or not _RUNTIME.active or not _RUNTIME.in_school():
        sims4.commands.output('M142 RUOLI: attiva da casa e vai al liceo',
                             _connection)
        return
    try:
        slot=str(current_slot(allow_travel=True))
        if slot!=_RUNTIME.slot:
            raise ValueError('SAVE_SLOT_CHANGED')
        roster=RosterStore(FOLDER).load(slot)
        groups=tuple(tuple(str(sid) for sid in roster.class_members(i))
                     for i in (1,2))
        played=find_playable_entry(groups,services.sim_info_manager(),
                                   services.active_household())
        from sims4.resources import Types
        manager=services.get_instance_manager(Types.INTERACTION)
        interaction=manager.get(PLAYER_CLASS_START) if manager else None
        report=inspect_player_jobs(
            played,services.get_zone_situation_manager(),interaction)
        report['clock']=game_clock(services.time_service())
        report['save_slot']=slot
        os.makedirs(FOLDER,exist_ok=True)
        filename='MHS_CLASSROOM_CONTROL_RUOLI_EA_GIOCABILI.json'
        with open(os.path.join(FOLDER,filename),'w',
                  encoding='utf-8') as stream:
            json.dump(report,stream,indent=2,ensure_ascii=False)
        for row in report['students']:
            sims4.commands.output(
                'M142 SIM {} classe={} ruoli={} stato={}'.format(
                    row['sim_id'],row['registered_class'],
                    ','.join('{}:{}'.format(x['situation_guid'],x['job_guid'])
                             for x in row['situation_jobs']),
                    row['status']),_connection)
        sims4.commands.output(
            'M142 RUOLI: file='+filename+' NESSUNA_MODIFICA',
            _connection)
    except Exception as exc:
        sims4.commands.output(
            'M142 RUOLI: errore '+type(exc).__name__,_connection)


@sims4.commands.Command('mhs148.testgiocabili',
    command_type=sims4.commands.CommandType.Live)
def m136testgiocabili(_connection=None):
    """Inspect only EA tests applied to the three enrolled PLAYABLE teens."""
    import json
    if _RUNTIME is None or not _RUNTIME.active or not _RUNTIME.in_school():
        sims4.commands.output('M142: attiva a casa e vai al liceo',
                             _connection)
        return
    try:
        slot=str(current_slot(allow_travel=True))
        if slot!=_RUNTIME.slot:raise ValueError('SAVE_SLOT_CHANGED')
        roster=RosterStore(FOLDER).load(slot)
        groups=tuple(tuple(str(x) for x in roster.class_members(i))
                     for i in (1,2))
        played=find_playable_entry(groups,services.sim_info_manager(),
                                   services.active_household())
        if not played:raise ValueError('NO_REGISTERED_PLAYABLE_TEENS')
        boards,status=_m131_state_evidence()
        if status!='TWO_VALIDATED_EA_CLASS_BOARDS':
            sims4.commands.output('M142 TEST: BLOCCATO '+status,_connection)
            return
        from sims4.resources import Types
        manager=services.get_instance_manager(Types.INTERACTION)
        affordance=manager.get(PLAYER_CLASS_START) if manager else None
        if affordance is None:raise ValueError('EA_PLAYER_AFFORDANCE_MISSING')
        report=inspect_test_hierarchy(affordance,played,boards)
        report['clock']=game_clock(services.time_service())
        report['save_slot']=slot
        filename='MHS_CLASSROOM_CONTROL_TEST_EA_GIOCABILI.json'
        os.makedirs(FOLDER,exist_ok=True)
        with open(os.path.join(FOLDER,filename),'w',
                  encoding='utf-8') as stream:
            json.dump(report,stream,indent=2,ensure_ascii=False)
        sims4.commands.output(
            'M142 TEST: giocabili={} nodi={} troncato={} '
            'NESSUNA_MODIFICA file={}'.format(
                len(played),len(report['nodes']),report['truncated'],
                filename),_connection)
    except Exception as exc:
        sims4.commands.output(
            'M142 TEST: errore '+type(exc).__name__,_connection)


def m137compat(_connection=None):
    """Read-only report on the scoped Zerbu test branch replacement."""
    if _RUNTIME is None or not _RUNTIME.active:
        sims4.commands.output('M142 COMPAT: armare da casa',_connection)
        return
    sims4.commands.output(
        'M142 COMPAT: esaminato={} stato={} scuola={} '
        'NPC/Elementary preservati'.format(
            _RUNTIME.m140_patch_checked,
            _RUNTIME.m140_patch_result,
            _RUNTIME.in_school()),_connection)

@sims4.commands.Command('mhs148.auto',
    command_type=sims4.commands.CommandType.Live)
def m140_auto_status(_connection=None):
    """Read-only observations; auto-entry never needs a console command."""
    if _RUNTIME is None or not _RUNTIME.active:
        sims4.commands.output('M142 AUTO: non attiva',_connection)
        return
    sims4.commands.output(
        'M142 AUTO: classi={} compat={} sync={} risultati={}'.format(
            tuple(sorted(_RUNTIME.m140_auto_attempted)),
            _RUNTIME.m140_patch_result,
            _RUNTIME.m131_sync_result,
            _RUNTIME.m140_auto_reports),_connection)


# M142: passive, bounded observation. No EA interactions are inserted or ended.
def _m146_capture_board_anchors(runtime):
    """Read exclusive EA board states even if no M143 recovery is triggered."""
    if runtime.m143_board_anchors is not None:
        return True
    try:
        boards,status=_m131_state_evidence()
        runtime.m147_anchors_status=status
        if status!='TWO_VALIDATED_EA_CLASS_BOARDS':
            return False
        anchors,why=validate_anchors(boards)
        runtime.m147_anchors_status=why
        if anchors is None:
            return False
        runtime.m143_board_anchors=anchors
        return True
    except Exception as exc:
        runtime.m147_anchors_status='BOARD_'+type(exc).__name__
        return False


def _m147_early_playable_preparation(runtime):
    """Request native EA whiteboard START on both verified preparation jobs.

    EA Class1: 293815/304701 job277919.
    EA Class2: 297774 job277919.
    No direct student teleport, NPC action or discipline changes.
    Actual native 276774 interaction tests are required to pass.
    """
    if not runtime.active or not runtime.in_school():
        return False
    try:
        stamp=game_clock(services.time_service())
        period=preparation_period(stamp)
        if period is None:
            return False
        if not ((runtime.m140_patch_result or {}).get('applied') and
                (runtime.m145_patch_result or {}).get('applied') and
                (runtime.m131_sync_result or {}).get('success')):
            return False
        slot=str(current_slot(allow_travel=True))
        if slot!=runtime.slot:
            return False
        roster=RosterStore(FOLDER).load(slot)
        groups=tuple(tuple(str(s) for s in roster.class_members(k))
                     for k in (1,2))
        if groups!=runtime.lesson_classes:
            runtime.m141_last_tick_error='M147_PREP_REGISTRY_CHANGED'
            return False
        played=find_playable_entry(groups,services.sim_info_manager(),
                                   services.active_household())
        if not played:
            return False
        report=inspect_player_jobs(
            played,services.get_zone_situation_manager(),None)
        jobs={str(r.get('sim_id')):r for r in report.get('students',())}
        candidates=[]
        for row in played:
            sid=str(row['sim_id'])
            klass=row['registered_class']
            if klass not in (1,2):
                continue
            sim=row['sim_info'].get_sim_instance()
            if sim is None:
                continue
            running=getattr(getattr(sim,'queue',None),'running',None)
            action=type(running).__name__ if running else ''
            permitted,reason=can_early_request(
                row['registered_class'],jobs.get(sid,{}).get('situation_jobs'),
                stamp,action,(period,sid) in runtime.m147_preclass_attempted)
            if not permitted:
                if reason not in ('EXISTING_OR_PROTECTED_ACTION',
                                  'PRECLASS_ALREADY_REQUESTED'):
                    marker=(period,sid,reason)
                    if marker not in runtime.m147_preclass_reported:
                        runtime.m147_preclass_reported.add(marker)
                        if len(runtime.m147_preclass_reports)<64:
                            runtime.m147_preclass_reports.append({
                                'period':period,'clock':stamp,
                                'sim_id':sid,'class':klass,'queued':False,
                                'reason':reason,'native_game_test_passed':False})
                continue
            candidates.append((row,sim))
        if not candidates:
            return False
        boards,status=_m131_state_evidence()
        if status!='TWO_VALIDATED_EA_CLASS_BOARDS':
            runtime.m147_anchors_status=status
            return False
        from sims4.resources import Types
        affordance=services.get_instance_manager(Types.INTERACTION).get(
            PLAYER_CLASS_START)
        if affordance is None:
            return False
        from interactions.context import InteractionContext
        from interactions.priority import Priority
        accepted_any=False
        for row,sim in candidates:
            sid=str(row['sim_id'])
            klass=row['registered_class']
            running=getattr(getattr(sim,'queue',None),'running',None)
            allowed,policy_reason=runtime.lesson_requests.decision(
                period,sid,klass,stamp,has_native_job=True,
                correct_board=len(boards.get(klass,()))==1,instanced=True,
                running_action=type(running).__name__ if running else '',
                queued_actions=_queued_action_names(sim),
                native_phase_created=klass in runtime.prep_created,
                phase='preparation',context_verified=True)
            if not allowed:
                continue
            result={'period':period,'clock':stamp,'sim_id':sid,
                'class':row['registered_class'],
                'queued':False,'native_game_test_passed':False,
                'uses_original_ea_class_start_276774':True,
                'native_ea_prep_role_for_registered_class_verified':True}
            try:
                target=boards[row['registered_class']][0]
                context=InteractionContext(
                    sim,InteractionContext.SOURCE_SCRIPT_WITH_USER_INTENT,
                    Priority.High)
                tested=affordance.test(target,context)
                result['native_game_test_passed']=bool(tested)
                result['test_detail']=str(tested)[:160]
                if not tested:
                    result['reason']='EA_NATIVE_TEST_REFUSED'
                else:
                    # One early request per player per period. A successful
                    # push only means EA accepted the queue, NOT seated.
                    outcome=queue_playable_class(
                        (row,),boards,affordance,
                        lambda _:context)
                    items=outcome.get('results',())
                    actual=items[0] if items else {}
                    result['queued']=actual.get('queued') is True
                    if result['queued']:
                        runtime.m147_preclass_attempted.add((period,sid))
                        runtime.m142_auto_accepted.add(sid)
                    result['reason']='EA_EARLY_'+str(
                        actual.get('reason','NO_QUEUE_RESULT'))
                    accepted_any=accepted_any or result['queued']
                runtime.lesson_requests.record_result(period,sid,stamp,
                    result['queued'],result['reason'],
                    native_test_passed=result['native_game_test_passed'])
            except Exception as exc:
                result['reason']='EA_EARLY_'+type(exc).__name__
            if len(runtime.m147_preclass_reports)<64:
                runtime.m147_preclass_reports.append(result)
        if accepted_any:
            _m141_capture(runtime,'m147_early_playable_prep_requested')
        return accepted_any
    except Exception as exc:
        runtime.m141_last_tick_error='M147_PREP_'+type(exc).__name__
        return False


def _observe_lesson_entry(runtime,event='interval'):
    """Extra read-only samples during entry; never feed them to push policy."""
    if not runtime.active or not runtime.in_school():
        return False
    try:
        from mhs_school_readback import entry_window,entry_snapshot
        stamp=game_clock(services.time_service())
        ticks=stamp.get('absolute_ticks')
        if (entry_window(stamp) is None or type(ticks) is not int
                or ticks==runtime.lesson_entry_last_ticks
                or len(runtime.lesson_entry_samples)>=64):
            return False
        from sims4.resources import Types
        traits=services.get_instance_manager(Types.TRAIT)
        trait=traits.get(CLASS1_TRAIT_ID) if traits else None
        sample=entry_snapshot(stamp,runtime.lesson_classes,
            services.sim_info_manager(),services.get_zone_situation_manager(),trait)
        sample['event']=event
        sample['dual_clock']=read_live_clocks(services)
        runtime.lesson_entry_samples.append(sample)
        runtime.lesson_entry_last_ticks=ticks
        return True
    except Exception as exc:
        # Readback cannot interrupt EA creation, alarms or the lesson policy.
        if len(runtime.school_readback_errors)<16:
            runtime.school_readback_errors.append('ENTRY_READ_'+type(exc).__name__)
        return False


def _observe_school_staff(runtime,stamp,period):
    try:
        from mhs53_staff_store import StaffStore
        from mhs_school_readback import staff_snapshot
        from sims4.resources import Types
        roster=StaffStore(FOLDER).load(runtime.slot)
        report=staff_snapshot(roster,services.sim_info_manager(),
            services.get_zone_situation_manager(),
            services.get_instance_manager(Types.TRAIT),
            expected_roles=runtime.staff_plan.get('selected_roles'))
    except Exception as exc:
        report={'complete':False,'errors':['STAFF_READ_'+type(exc).__name__],
                'selection_bridge_implemented':False,'world_mutations':0}
    # A saved menu entry is not proof that EA staffed the selected Sim:
    # show both the attempted exact guests and the actual observed native job.
    report['clock']=stamp
    report['period']=period
    report['selection_bridge_implemented']='EXPERIMENTAL_NATIVE_EXACT_GUESTS'
    report['registry_is_not_native_assignment']=True
    report['native_guest_projection_applied']=any(
        item.get('applied') for item in runtime.staff_projection_reports)
    report['native_guest_projection_failures']=[
        item.get('reason') for item in runtime.staff_projection_reports
        if item.get('applied') is False][-8:]
    report['native_situation_creation_acknowledged']=bool(runtime.staff_created)
    report['staff_native_job_matches_only_when_observed']=True
    if len(runtime.school_staff_samples)<64:
        runtime.school_staff_samples.append(report)
    return report


def _m141_capture(runtime,event='interval'):
    journal=runtime.m141_journal
    if journal is None or not runtime.active or not runtime.in_school():
        return False
    try:
        stamp=game_clock(services.time_service())
        ticks=stamp.get('absolute_ticks')
        if not should_capture_sim_snapshot(
                ticks,runtime.m148_last_sample_ticks,
                forced=event!='interval',min_minutes=15):
            runtime.m148_skipped_samples+=1
            return False
        if str(current_slot(allow_travel=True))!=runtime.slot:
            runtime.m141_last_tick_error='SAVE_SLOT_CHANGED'
            return False
        manager=services.sim_info_manager()
        if manager is None:
            raise ValueError('NO_SIM_MANAGER')
        if runtime.m143_board_anchors is None:
            _m146_capture_board_anchors(runtime)
        rows=[]
        from sims4.resources import Types
        traits=services.get_instance_manager(Types.TRAIT)
        class_trait=traits.get(CLASS1_TRAIT_ID) if traits else None
        native=inspect_sixteen_lesson_actions(runtime.lesson_classes,manager,
            services.get_zone_situation_manager(),Age.TEEN,Species.HUMAN)
        native_by_id={str(item['sim_id']):item for item in native.get('rows',())}
        for klass,group in enumerate(runtime.lesson_classes,1):
            for sid in group:
                info=manager.get(int(sid))
                row=observe_student(info,klass)
                if row.get('sim_id') is None:
                    row['sim_id']=str(sid)
                # Read native jobs for ALL registered students, including NPCs.
                # Created situation IDs alone do not establish admission.
                row['native_lesson_evidence']=native_by_id.get(str(sid),{
                    'state':'NATIVE_JOB_OBSERVATION_UNAVAILABLE'})
                try:
                    row['ea_class1_trait_present']=(
                        bool(info.trait_tracker.has_trait(class_trait))
                        if info is not None and class_trait is not None else None)
                    snapshot=queue_snapshot(info.get_sim_instance()) if info is not None else {}
                    row['queue_details_available']=snapshot.get('available',False)
                    row['queue_read_reason']=snapshot.get('reason','SIM_INFO_MISSING')
                    row['queued_actions']=snapshot.get('queued_names')
                    row['running_parent_actions']=snapshot.get('active_parent_names')
                except Exception as exc:
                    row['queue_read_reason']='READ_'+type(exc).__name__
                rows.append(row)
        try:
            from mhs134_native_player_job_audit import inspect_player_jobs
            played=find_playable_entry(runtime.lesson_classes,manager,
                                       services.active_household())
            player_jobs=inspect_player_jobs(
                played,services.get_zone_situation_manager(),None
                ).get('students',[])
        except Exception as exc:
            player_jobs=[{'diagnostic':'JOB_READ_'+type(exc).__name__}]
        ok=journal.append(stamp,rows,
                          event,player_jobs,
                          runtime.m140_auto_reports[-4:]+
                          runtime.m142_retry_reports[-4:])
        if ok:
            runtime.m148_last_sample_ticks=ticks
            journal.samples[-1]['dual_clock']=read_live_clocks(services)
            # A world-wide EA staff scan is expensive with large saves.
            # Keep five phase snapshots (arrival, both lessons, lunch,
            # school end) instead of re-reading every 15 minutes.
            # The 16-student journal cadence remains unchanged.
            from mhs_school_readback import staff_sample_period
            staff_phase=staff_sample_period(stamp)
            if (staff_phase is not None and
                    not any(item.get('period')==staff_phase
                            for item in runtime.school_staff_samples)):
                _observe_school_staff(runtime,stamp,staff_phase)
        if not ok and len(journal.samples)>=200:
            _m141_stop_trace(runtime)
        return ok
    except Exception as exc:
        runtime.m141_last_tick_error=type(exc).__name__
        if journal is not None and len(journal.errors)<24:
            journal.errors.append('TICK_'+type(exc).__name__)
        return False


def _m141_cancel_alarm(handle):
    if handle is None:
        return
    try:
        import alarms
        alarms.cancel_alarm(handle)
    except Exception:
        pass


def _m141_stop_trace(runtime):
    handle=runtime.m141_timer
    watcher=runtime.m141_watcher_timer
    runtime.m141_timer=None
    runtime.m141_watcher_timer=None
    _m141_cancel_alarm(handle)
    _m141_cancel_alarm(watcher)
    if runtime.m141_journal is not None:
        runtime.m141_journal.flush()


def _m141_start_watcher(runtime):
    """Watch for school arrival independently of any EA class event."""
    if runtime.m141_watcher_timer is not None or not runtime.active:
        return
    try:
        import alarms
        import clock
        def watch(handle):
            if not runtime.active:
                _m141_cancel_alarm(handle)
                return
            if runtime.in_school():
                _m141_start_trace(runtime,'school_arrival_watcher')
        runtime.m141_watcher_timer=alarms.add_alarm(
            runtime,clock.interval_in_sim_minutes(2),watch,repeating=True)
        if runtime.m141_watcher_timer is None:
            raise ValueError('WATCHER_ALARM_UNAVAILABLE')
    except Exception as exc:
        runtime.m141_start_error='WATCHER_'+type(exc).__name__


def _m141_start_trace(runtime,origin='ea_event'):
    """Independent bootstrap: EA create, scheduled watcher, or monitor."""
    if not runtime.active or not runtime.in_school():
        return False
    if runtime.m141_timer is not None:
        return True
    try:
        runtime.begin_school_day(current_school_day(runtime.slot))
        if not _install_school_adapters(runtime):
            runtime.m141_start_error='UNSUPPORTED_CLASSROOM_ADAPTER'
            return False
        if runtime.lesson_classes is None:
            raise ValueError('ROSTER_UNAVAILABLE')
        if runtime.m141_journal is None:
            runtime.m141_journal=DayJournal(
                FOLDER,runtime.slot,runtime.lesson_classes,
                output='MHS_CLASSROOM_CONTROL_GIORNATA_LEZIONI_MENSA.json')
        import alarms
        import clock
        def sample(handle):
            if not runtime.active or not runtime.in_school():
                if runtime.m147_trace_end is None:
                    try:
                        runtime.m147_trace_end={
                            'reason':'SCHOOL_ZONE_OR_SCHEDULE_ENDED',
                            'clock':game_clock(services.time_service()),
                            'in_school':runtime.in_school()}
                    except Exception as exc:
                        runtime.m147_trace_end={
                            'reason':'SCHOOL_ZONE_OR_SCHEDULE_ENDED',
                            'clock_error':type(exc).__name__}
                _m141_stop_trace(runtime)
                return
            _m142_roll_period_if_due(runtime,
                                     game_clock(services.time_service()))
            _observe_lesson_entry(runtime)
            _m141_capture(runtime,'interval')
            _m147_early_playable_preparation(runtime)
            _m142_retry_playables(runtime)
            _m143_direct_attend(runtime)
        handle=alarms.add_alarm(
            runtime,clock.interval_in_sim_minutes(3),sample,repeating=True)
        if handle is None:
            raise ValueError('SIM_ALARM_UNAVAILABLE')
        runtime.m141_timer=handle
        runtime.m141_start_error=None
        runtime.m141_trace_origin=origin
        _m141_capture(runtime,'trace_started_'+origin)
        runtime.m141_journal.flush()
        watcher=runtime.m141_watcher_timer
        runtime.m141_watcher_timer=None
        _m141_cancel_alarm(watcher)
        return True
    except Exception as exc:
        runtime.m141_start_error='START_'+type(exc).__name__
        # Preserve the journal if a timer could not start, so monitor/log
        # can retry and report the real underlying API error.
        return False


@sims4.commands.Command('mhs148.log',
    command_type=sims4.commands.CommandType.Live)
def m141_log(_connection=None):
    if _RUNTIME is None or not _RUNTIME.active:
        sims4.commands.output('M143 LOG: non attiva, attivare da casa',_connection)
        return
    if _RUNTIME.m141_timer is None and _RUNTIME.in_school():
        _m141_start_trace(_RUNTIME,'log_fallback')
    if _RUNTIME.m141_journal is None:
        sims4.commands.output(
            'M143 LOG: registrazione non avviata; errore={}'.format(
                _RUNTIME.m141_start_error or 'nessuno'),_connection)
        return
    _m141_capture(_RUNTIME,'manual_status_snapshot')
    ok=_RUNTIME.m141_journal.flush()
    _m142_write_lunch_summary(_RUNTIME)
    _m143_write_full_report(_RUNTIME)
    sims4.commands.output(
        'M143 LOG: campioni={} salvato={} errore={} file={}'.format(
        len(_RUNTIME.m141_journal.samples),ok,
        _RUNTIME.m141_last_tick_error or
        _RUNTIME.m141_journal.write_error or 'nessuno',
        'MHS_CLASSROOM_CONTROL_GIORNATA_LEZIONI_MENSA.json'),_connection)


@sims4.commands.Command('mhs148.monitor',
    command_type=sims4.commands.CommandType.Live)
def m141_monitor(_connection=None):
    if _RUNTIME is None:
        sims4.commands.output('M148 MONITOR: non attiva',_connection)
        return
    if _RUNTIME.active and _RUNTIME.in_school() and _RUNTIME.m141_timer is None:
        _m141_start_trace(_RUNTIME,'monitor_fallback')
    j=_RUNTIME.m141_journal
    sims4.commands.output(
        'M148 MONITOR: scuola={} timer={} campioni={} periodo={} riprese={} origine={} errore={}'.format(
        _RUNTIME.in_school(),_RUNTIME.m141_timer is not None,
        len(j.samples) if j else 0,
        _RUNTIME.m142_period,
        len(_RUNTIME.m142_retry_reports),
        _RUNTIME.m141_trace_origin or 'nessuna',
        _RUNTIME.m141_start_error or _RUNTIME.m141_last_tick_error or
        (j.write_error if j else None) or 'nessuno'),_connection)


# M142: one daily 13:30 phase refresh and bounded 10:05/14:05 playable
# class retry. School original EA scheduling, NPC jobs and lunch remain EA-owned.
def _m142_roll_period_if_due(runtime,clock):
    if not runtime.active or not runtime.in_school():
        return False
    if not can_roll_to_afternoon(
            clock, None, PREP_JOBS,
            runtime.m142_afternoon_rearmed):
        return False
    runtime.m142_afternoon_rearmed=True
    runtime.m142_period='afternoon'
    runtime.prep_attempted.clear()
    runtime.lesson_attempted.clear()
    runtime.m140_auto_attempted.clear()
    runtime.m142_auto_accepted.clear()
    runtime.prep_created.clear()
    runtime.lesson_created.clear()
    runtime.m142_afternoon_roll_events.append({
        'clock':clock, 'reason':'AFTERNOON_EA_PERIOD_REARMED',
        'registration_unchanged':True,
        'ea_schedule_unchanged':True})
    _m141_capture(runtime,'m142_afternoon_rearmed')
    return True


def _record_native_entry(runtime, result, stamp):
    if result.get('reason') not in ('EA_ACCEPTED','EA_REJECTED'):
        return
    try:
        runtime.lesson_requests.record_result(
            runtime.m142_period,str(result['sim_id']),stamp,
            bool(result.get('queued')),result['reason'],
            native_test_passed=bool(result.get('queued')))
    except ValueError:
        # A phase callback can observe the same request twice; never expand
        # its budget or convert an observation into another request.
        pass


def _queued_action_names(sim):
    snapshot=queue_snapshot(sim)
    # A phone/listening mixer can be part of an already running EA lesson.
    # Include its active parent in duplicate/protection decisions, not in the
    # journal's separate list of genuinely pending actions.
    return (snapshot['queued_names']+snapshot['active_parent_names']
            if snapshot['available'] else None)


def _m142_retry_playables(runtime):
    """Bounded native requests also cover initially refused/missing Sims.

    Situation IDs and accepted requests are not proof of admission or seating.
    Unknown queue APIs refuse a retry instead of interrupting unseen actions.
    """
    if not runtime.active or not runtime.in_school():
        return False
    try:
        stamp=game_clock(services.time_service())
        minute=minute_of_day(stamp)
        if minute is None or not (600<=minute<=624 or 840<=minute<=864):
            return False
        slot=str(current_slot(allow_travel=True))
        if slot!=runtime.slot:
            return False
        groups=tuple(tuple(str(s) for s in RosterStore(FOLDER).load(slot).class_members(k))
                     for k in (1,2))
        if groups!=runtime.lesson_classes:
            return False
        played=find_playable_entry(groups,services.sim_info_manager(),
                                   services.active_household())
        detail=inspect_player_jobs(played,services.get_zone_situation_manager(),None)
        jobs={str(row['sim_id']):row for row in detail.get('students',())}
        boards,status=_m131_state_evidence()
        if status!='TWO_VALIDATED_EA_CLASS_BOARDS':
            return False
        from sims4.resources import Types
        affordance=services.get_instance_manager(Types.INTERACTION).get(PLAYER_CLASS_START)
        if affordance is None:
            return False
        from interactions.context import InteractionContext
        from interactions.priority import Priority
        attempted=False
        for row in played:
            sid=str(row['sim_id'])
            klass=row['registered_class']
            sim=row['sim_info'].get_sim_instance()
            running=getattr(getattr(sim,'queue',None),'running',None) if sim else None
            name=type(running).__name__ if running else ''
            allow,reason=runtime.lesson_requests.decision(
                runtime.m142_period,sid,klass,stamp,
                has_native_job=job_matches_class(klass,jobs.get(sid,{}).get('situation_jobs')),
                correct_board=len(boards.get(klass,()))==1,
                instanced=sim is not None,running_action=name,
                queued_actions=_queued_action_names(sim) if sim else None,
                native_phase_created=klass in runtime.lesson_created,
                context_verified=True)
            if not allow:
                marker=(runtime.m142_period,sid,reason)
                if marker not in runtime.m143_policy_log:
                    runtime.m143_policy_log.add(marker)
                    runtime.m142_retry_reports.append({
                        'period':runtime.m142_period,'clock':stamp,
                        'sim_id':sid,'registered_class':klass,
                        'reason':reason,'attempted':False})
                continue
            context=InteractionContext(sim,InteractionContext.SOURCE_SCRIPT_WITH_USER_INTENT,
                                       Priority.High)
            target=boards[klass][0]
            tested=affordance.test(target,context)
            result={'sim_id':sid,'queued':False,'reason':'EA_REJECTED'}
            if tested:
                report=queue_playable_class((row,),boards,affordance,lambda _:context)
                rows=report.get('results',())
                if rows:
                    result=rows[0]
            runtime.lesson_requests.record_result(
                runtime.m142_period,sid,stamp,bool(result.get('queued')),
                result.get('reason','EA_REJECTED'),native_test_passed=bool(tested))
            if result.get('queued'):
                runtime.m142_auto_accepted.add(sid)
            runtime.m142_retry_reports.append({
                'period':runtime.m142_period,'clock':stamp,'sim_id':sid,
                'registered_class':klass,'results':[result],
                'attempted':True,'native_job_required':True,
                'does_not_prove_action_completed':True})
            attempted=True
        if attempted:
            _m141_capture(runtime,'bounded_registered_playable_retry')
        return attempted
    except Exception as exc:
        runtime.m141_last_tick_error='RETRY_'+type(exc).__name__
        return False


def _m142_write_lunch_summary(runtime):
    if runtime.m141_journal is None:
        return False
    try:
        import json
        groups=runtime.lesson_classes or ()
        if not groups:
            return False
        ids=tuple(sid for group in groups for sid in group)
        summary=summarize_npc_lunch(
            runtime.m141_journal.samples,ids,sample_minutes=3)
        path=os.path.join(FOLDER,'MHS_CLASSROOM_CONTROL_MENSA_NPC_ATTESE.json')
        with open(path,'w',encoding='utf-8') as output:
            json.dump(summary,output,indent=2,ensure_ascii=False)
        return True
    except Exception as exc:
        runtime.m141_last_tick_error='LUNCH_REPORT_'+type(exc).__name__
        return False


@sims4.commands.Command('mhs148.mensa',
    command_type=sims4.commands.CommandType.Live)
def m142_mensa(_connection=None):
    if _RUNTIME is None or _RUNTIME.m141_journal is None:
        sims4.commands.output(
            'M145 MENSA: monitor non avviato',_connection)
        return
    success=_m142_write_lunch_summary(_RUNTIME)
    sims4.commands.output(
        'M145 MENSA: salvato={} file=MHS_CLASSROOM_CONTROL_MENSA_NPC_ATTESE.json '
        'NESSUNA AZIONE MODIFICATA'.format(success),_connection)


@sims4.commands.Command('mhs148.periodi',
    command_type=sims4.commands.CommandType.Live)
def m142_periods(_connection=None):
    if _RUNTIME is None:
        sims4.commands.output('M145 PERIODI: non attiva',_connection)
        return
    sims4.commands.output(
        'M145 PERIODI: fase={} pomeriggio_riarmato={} '
        'richieste_automatiche={} riprese_limitate={} lezione_create={} '
        'orari_eventi={}'.format(
        _RUNTIME.m142_period,_RUNTIME.m142_afternoon_rearmed,
        len(_RUNTIME.m142_auto_accepted),
        len(_RUNTIME.m142_retry_attempted),
        sorted(_RUNTIME.lesson_created),
        _RUNTIME.m142_afternoon_roll_events[-2:]),_connection)


# M143: second phase uses the ACTUAL active native EA subject interaction,
# observed from a playable student already in class. Only when the game's
# own target-side test PASSES; otherwise reports reason and leaves EA alone.
def _m143_direct_attend(runtime):
    if not runtime.active or not runtime.in_school():
        return False
    try:
        stamp=game_clock(services.time_service())
        m=stamp.get('minute')
        h=stamp.get('hour')
        if h not in (10,14) or type(m) is not int or not 7<=m<=24:
            return False
        if runtime.lesson_classes is None:
            return False
        period=runtime.m142_period
        roster=RosterStore(FOLDER).load(runtime.slot)
        groups=tuple(tuple(str(s) for s in roster.class_members(k))
                     for k in (1,2))
        if groups!=runtime.lesson_classes:
            runtime.m141_last_tick_error='DIRECT_ROSTER_CHANGED'
            return False
        sim_info_mgr=services.sim_info_manager()
        played=find_playable_entry(groups,sim_info_mgr,
                                   services.active_household())
        jobs=inspect_player_jobs(
            played,services.get_zone_situation_manager(),None)
        by_id={str(r.get('sim_id')):r
               for r in jobs.get('students',())}
        targets=[]
        for row in played:
            sid=str(row['sim_id'])
            key=(period,sid)
            if key in runtime.m143_direct_attempted:
                continue
            klass=row['registered_class']
            sim=row['sim_info'].get_sim_instance()
            running=getattr(getattr(sim,'queue',None),'running',None) if sim else None
            name=type(running).__name__ if running else ''
            if protected_gameplay(name):
                continue
            queued=_queued_action_names(sim) if sim else None
            if queued is None or any(protected_gameplay(action) for action in queued):
                continue
            state=runtime.lesson_requests.state(period,sid)
            now=minute_of_day(stamp)
            if state['attempts']>=runtime.lesson_requests.max_attempts:
                continue
            if state['last_minute'] is not None and (
                    now-state['last_minute']<runtime.lesson_requests.min_gap_minutes):
                continue
            valid=job_matches_class(klass,by_id.get(sid,{}).get('situation_jobs'))
            allowed,reason=allowed_direct_attend(
                stamp,klass,sid,valid,
                sid in runtime.m142_auto_accepted,
                key in runtime.m143_direct_attempted,name,klass)
            if allowed:
                targets.append((row,key,name))
            elif reason not in ('ALREADY_ATTENDING_CLASS',
                                'NOT_CURRENT_LESSON_RECOVERY_WINDOW'):
                # Track one useful refusal per student per period.
                marker=(period,sid,reason)
                if marker not in runtime.m143_policy_log:
                    runtime.m143_policy_log.add(marker)
                    runtime.m143_direct_reports.append({
                      'event':'policy_refusal','period':period,'clock':stamp,
                      'sim_id':sid,'class':klass,'reason':reason})
        if not targets:
            return False
        boards,board_status=_m131_state_evidence()
        if board_status!='TWO_VALIDATED_EA_CLASS_BOARDS':
            _m143_refuse_targets(runtime,targets,stamp,'BOARD_'+board_status)
            return False
        if runtime.m143_board_anchors is None:
            try:
                anchors={}
                for klass in (1,2):
                    board=boards[klass][0]
                    position=getattr(board,'position',None)
                    anchors[klass]={
                        'id':str(getattr(board,'id',None)),
                        'position':{axis:float(getattr(position,axis))
                                    for axis in ('x','y','z')}}
                if (anchors[1]['id']!=anchors[2]['id'] and
                        all(anchors[k]['id'] not in ('None','') for k in (1,2))):
                    runtime.m143_board_anchors=anchors
            except Exception:
                pass
        # Important: do not fabricate the tuning ID for a subject. Learn
        # it from an ACTIVE original EA classroom action already running.
        subject,reason=find_observed_attend(played)
        if subject is None:
            _m143_refuse_targets(runtime,targets,stamp,reason)
            return False
        from interactions.context import InteractionContext
        from interactions.priority import Priority
        from sims4.resources import Types
        traits=services.get_instance_manager(Types.TRAIT)
        trait=traits.get(CLASS1_TRAIT_ID) if traits else None
        for row,key,previous in targets:
            sid=str(row['sim_id'])
            klass=row['registered_class']
            result={
                'event':'direct_native_ea_attend','clock':stamp,
                'period':period,'sim_id':sid,'class':klass,
                'source_action':getattr(subject,'__name__',None),
                'source_affordance_guid':getattr(subject,'guid64',None),
                'action_before':previous,
                'game_native_test_passed':False,'queued':False,
                'student_moved_or_completed_unproven':True}
            try:
                target=boards[klass][0]
                sim=row['sim_info'].get_sim_instance()
                result['board_id']=str(getattr(target,'id',None))
                if trait is None:
                    result['reason']='CLASS_TRAIT_NOT_LOADED'
                elif not callable(getattr(row['sim_info'].trait_tracker,
                                           'has_trait',None)):
                    result['reason']='CLASS_TRAIT_CHECK_MISSING'
                elif bool(row['sim_info'].trait_tracker.has_trait(trait))!=(klass==1):
                    result['reason']='CLASS_TRAIT_MISMATCH_REFUSED'
                elif sim is None or not callable(getattr(sim,'push_super_affordance',None)):
                    result['reason']='SIM_OR_PUSH_API_MISSING'
                else:
                    context=InteractionContext(
                        sim,InteractionContext.SOURCE_SCRIPT_WITH_USER_INTENT,
                        Priority.High)
                    test_result=subject.test(target,context)
                    result['game_native_test_passed']=bool(test_result)
                    result['native_test_result']=str(test_result)[:250]
                    if not test_result:
                        result['reason']='NATIVE_EA_TEST_REFUSED'
                    else:
                        # Push exact observed EA Attend interaction only.
                        accepted=sim.push_super_affordance(
                            subject,target,context,picked_object=target)
                        result['queued']=bool(accepted)
                        result['reason']=(
                            'EA_DIRECT_ATTEND_ACCEPTED_UNCONFIRMED' if accepted
                            else 'EA_DIRECT_ATTEND_REJECTED')
            except Exception as exc:
                result['reason']='EA_DIRECT_'+type(exc).__name__
            # Only one direct test/push per player per class period. Does not
            # repeatedly push on every three-minute monitor sample.
            runtime.m143_direct_attempted.add(key)
            if 'native_test_result' in result:
                runtime.lesson_requests.record_result(period,sid,stamp,
                    bool(result.get('queued')),result.get('reason'),
                    native_test_passed=bool(result.get('game_native_test_passed')))
            runtime.m143_direct_reports.append(result)
        _m141_capture(runtime,'m143_direct_native_attend')
        return True
    except Exception as exc:
        runtime.m141_last_tick_error='DIRECT_'+type(exc).__name__
        return False


def _m143_refuse_targets(runtime,targets,clock_value,reason):
    # Missing live source may appear shortly after the class begins; retry
    # observation at next interval. Do not mark as a real interaction attempt.
    for row,key,_ in targets:
        tag=(key,reason)
        if tag in runtime.m143_policy_log:
            continue
        runtime.m143_policy_log.add(tag)
        runtime.m143_direct_reports.append({
            'event':'source_not_ready','clock':clock_value,
            'period':key[0],'sim_id':key[1],
            'class':row['registered_class'],
            'reason':reason,'queued':False})


def _m143_write_full_report(runtime):
    """Single end-of-school command produces lesson and dining evidence."""
    if runtime is None or runtime.m141_journal is None:
        return False
    try:
        import json
        if not os.path.isdir(FOLDER):
            os.makedirs(FOLDER)
        path=os.path.join(FOLDER,'MHS_CLASSROOM_CONTROL_INTERAZIONI_GIOCABILI_EA.json')
        payload={
            'kind':'M143_REAL_EA_ATTEND_TEST_AND_QUEUE_LIFECYCLE',
            'direct_attempts':runtime.m143_direct_reports,
            'initial_native_accepted':runtime.m140_auto_reports,
            'afternoon_roll_events':runtime.m142_afternoon_roll_events,
            'observed_exclusive_board_anchors':runtime.m143_board_anchors,
            'class_membership_fixed':True,
            'does_not_prove_seated_or_completed':True,
            'native_ea_test_never_bypassed':True,
            'M145_subject_picker_result':runtime.m145_patch_result,
            'M146_early_class2_preparation':runtime.m147_preclass_reports,
            'M146_board_anchor_status':runtime.m147_anchors_status,
            'no_nonclass_player_actions_automated':True}
        with open(path,'w',encoding='utf-8') as output:
            json.dump(payload,output,indent=2,ensure_ascii=False)
        # For NPCs, measure whether they ate while seated at lunch.
        groups=runtime.lesson_classes or ()
        npc_ids=[]
        info_mgr=services.sim_info_manager()
        for klass in groups:
            for sid in klass:
                info=info_mgr.get(int(sid)) if info_mgr else None
                if info is not None and getattr(info,'is_selectable',True) is False:
                    npc_ids.append(str(sid))
        dining=analyze_npc_dining(runtime.m141_journal.samples,npc_ids)
        with open(os.path.join(FOLDER,
             'MHS_CLASSROOM_CONTROL_MENSA_NPC_SEDUTI.json'),'w',encoding='utf-8') as output:
            json.dump(dining,output,indent=2,ensure_ascii=False)
        attendance=summarize_registered_attendance(
            runtime.m141_journal.samples,groups,runtime.m143_board_anchors)
        with open(os.path.join(FOLDER,
             'MHS_CLASSROOM_CONTROL_PRESENZE_DUE_AULE.json'),'w',
             encoding='utf-8') as output:
            json.dump(attendance,output,indent=2,ensure_ascii=False)
        # One comprehensive report: the user uploads ONE file, not four.
        from mhs_school_readback import summarize_staff_shift
        shift_verdict=summarize_staff_shift(runtime.school_staff_samples)
        all_sids=tuple(str(sid) for group in groups for sid in group)
        waiting=summarize_npc_lunch(
            runtime.m141_journal.samples,all_sids,sample_minutes=3)
        complete={
            'diagnostic_revision':'SECOND_DAY_READ_ONLY_OBSERVATIONS',
            'school_readback_errors':runtime.school_readback_errors,
            'lesson_entry_observations':runtime.lesson_entry_samples,
            'school_staff':{
                'samples':runtime.school_staff_samples,
                'native_job_shift_verdict':shift_verdict,
                'selection_bridge_implemented':'EXPERIMENTAL_NATIVE_EXACT_GUESTS',
                'native_guest_projection_applied':any(
                    item.get('applied') for item in runtime.staff_projection_reports),
                'registry_is_not_native_assignment':True,
                'native_staff_appointments':dict(runtime.staff_plan.get('jobs',{})),
                'native_staff_multi_appointments':{
                    str(job):list(ids) for job,ids in
                    runtime.staff_plan.get('job_groups',{}).items()
                    if len(ids)>1},
                'native_two_custodians_beta':bool(
                    runtime.staff_plan.get(
                        'two_custodians_explicit_invites_beta')),
                'native_staff_blocked_roles':dict(runtime.staff_plan.get('blocked',{})),
                'native_staff_projection_attempts':runtime.staff_projection_reports,
                'native_staff_situations_created':dict(runtime.staff_created),
                'native_staff_exact_filter_hits':runtime.staff_filter_hits,
                'actual_staff_still_requires_game_verification':True},
            'classroom_control':{
                'npc_board_guard':runtime.classroom_guard_result,
                'scoped_test_checks':runtime.classroom_scope_checks,
                'wrong_or_ambiguous_board_blocks':runtime.classroom_scope_blocked,
                'last_block_per_registered_student':runtime.classroom_scope_last,
                'outside_scope_original_rules':True,
                'no_forced_seating_or_completion':True},
            'kind':'M143_ONE_FILE_FULL_SCHOOL_REPORT',
            'save_slot':runtime.slot,
            'classes':groups,
            'school_day_journal':runtime.m141_journal.samples,
            'school_observation_errors':runtime.m141_journal.errors,
            'native_original_ea_class_entry':payload,
            'm147_integration':{
                'early_playable_attempts':runtime.m147_preclass_reports,
                'early_playable_accepted_count':sum(
                    1 for item in runtime.m147_preclass_reports
                    if item.get('queued') is True),
                'board_anchor_status':runtime.m147_anchors_status,
                'monitor_terminal_reason':runtime.m147_trace_end,
                'report_generated_at_clock':game_clock(services.time_service()),
                'in_school_at_report':runtime.in_school(),
                'last_sample_clock':(
                    runtime.m141_journal.samples[-1].get('clock')
                    if runtime.m141_journal.samples else None),
                'registered_npc_principal_or_truancy_incidents':
                    truant_evidence(runtime.m141_journal.samples),
                'no_npc_teleport_or_truancy_bypass':True,
                'no_forced_lesson_end':True,
                'm148_game_and_sim_clock':read_live_clocks(services),
                'm148_poll_rate_sim_minutes':3,
                'm148_full_snapshot_interval_sim_minutes':15,
                'm148_full_snapshots_skipped':runtime.m148_skipped_samples,
                'm148_low_impact_journal_flush_every':50,
                'goals_completion_not_modified':True,
            },
            'physical_classroom_attendance':attendance,
            'npc_lunch_posture':dining,
            'npc_lunch_ordering':waiting,
            'no_manual_teens_lunch_automation':True,
            'not_verified_in_game_until_trial':True,
        }
        destination=os.path.join(FOLDER,'MHS_CLASSROOM_CONTROL_REPORT_COMPLETO.json')
        temporary=destination+'.tmp'
        with open(temporary,'w',encoding='utf-8') as output:
            json.dump(complete,output,indent=2,ensure_ascii=False)
        os.replace(temporary,destination)
        return True
    except Exception as exc:
        runtime.m141_last_tick_error='FULL_REPORT_'+type(exc).__name__
        return False


@sims4.commands.Command('mhs148.clock',
    command_type=sims4.commands.CommandType.Live)
def m148clock(_connection=None):
    """Read visible GameClock and simulated TimeService independently."""
    try:
        info=read_live_clocks(services)
        game=info.get('game_time_displayed') or {}
        sim=info.get('sim_time_processed') or {}
        sims4.commands.output(
            'M148 CLOCK: UI={} SIM={} gap_min={} stato={} '
            'lettura_sola=True'.format(
                game.get('repr','NON_DISPONIBILE'),
                sim.get('repr','NON_DISPONIBILE'),
                info.get('lag_minutes'),info.get('state')),_connection)
    except Exception as exc:
        sims4.commands.output(
            'M148 CLOCK LETTURA: '+type(exc).__name__,_connection)


@sims4.commands.Command('mhs148.report',
    command_type=sims4.commands.CommandType.Live)
def m143_report(_connection=None):
    if _RUNTIME is None or not _RUNTIME.active:
        sims4.commands.output(
            'M148 REPORT: attivare da casa con mhs148.arm',_connection)
        return
    journal=_RUNTIME.m141_journal
    if journal is None:
        sims4.commands.output('M148 REPORT: monitor non avviato',_connection)
        return
    _m141_capture(_RUNTIME,'end_of_day_report')
    ok_day=journal.flush()
    ok_lunch=_m142_write_lunch_summary(_RUNTIME)
    ok_full=_m143_write_full_report(_RUNTIME)
    sims4.commands.output(
        'M148 REPORT: diario={} mensa={} test_ea={} campioni={} '
        'tentativi_diretti={} errore={}'.format(
         ok_day,ok_lunch,ok_full,len(journal.samples),
         len(_RUNTIME.m143_direct_attempted),
         _RUNTIME.m141_last_tick_error or 'nessuno'),_connection)
    if ok_day and ok_full:
        sims4.commands.output(
            'M148 REPORT UNICO: MHS_CLASSROOM_CONTROL_REPORT_COMPLETO.json',
            _connection)


@sims4.commands.Command('mhs148.compat',
    command_type=sims4.commands.CommandType.Live)
def m145_compat(_connection=None):
    if _RUNTIME is None or not _RUNTIME.active:
        sims4.commands.output(
            'M148 COMPAT: non attiva, mhs148.arm da casa',_connection)
        return
    sims4.commands.output(
        'M148 COMPAT: selezione={} lezioni={} scuola={} '
        'nessun test EA bypassato'.format(
           _RUNTIME.m140_patch_result,
           _RUNTIME.m145_patch_result,
           _RUNTIME.in_school()),_connection)
