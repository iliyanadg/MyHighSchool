"""M142 experimental Mac: 8 Base + 5 user-pinned Core NPCs, original EA hooks.

Extends M119's actual live result: one EA Base assigned NPC observed at
08:13 and 10:32. Five Core role holders come ONLY from M97 manual selections; no extra NPC generation.
Native original EA Base count (3,3) may be raised to (8,8) only in
school context, using the EA calendar classmethod owner.
One test save only; not a complete 16-student classroom controller.
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
from mhs142_day_trace import DayJournal, observe_student
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
_RUNTIME=None


def zone_schedule():
    zone=services.current_zone()
    venue=services.venue_service()
    director=venue.get_zone_director() if venue else None
    return (getattr(zone,'id',None),
            getattr(getattr(director,'_schedule',None),'guid64',None))


def registered_eight():
    slot=str(current_slot(allow_travel=False))
    setting=SettingsStore(FOLDER).load(slot)
    if not setting.active or setting.class_count!=2:
        raise ValueError('Attiva due classi MHS')
    roster=RosterStore(FOLDER).load(slot)
    enrolled=tuple(str(i) for klass in (1,2)
                   for i in roster.class_members(klass))
    if len(enrolled)!=16 or len(set(enrolled))!=16:
        raise ValueError('Registro deve contenere due classi da 8')
    household=services.active_household()
    if household is None:
        raise ValueError('Nessuna famiglia attiva')
    played=tuple(str(info.sim_id) for info in household.sim_info_gen()
                 if getattr(info,'age',None)==Age.TEEN
                 and getattr(info,'species',None)==Species.HUMAN)
    if len(played)!=3 or not set(played)<=set(enrolled):
        raise ValueError('Tre teen giocabili devono essere iscritti')
    core=CoreRoleStore(FOLDER).load(slot)
    pinned=core.chosen() if core.complete else {}
    if (set(pinned)!=set(CORE_JOBS) or len(set(pinned.values()))!=5
            or not set(pinned.values())<=set(enrolled)-set(played)):
        raise ValueError('Servono 5 ruoli Core manuali, NPC iscritti')
    base=tuple(sid for sid in enrolled
               if sid not in played and sid not in pinned.values())
    if len(base)!=8 or len(set(base))!=8:
        raise ValueError('Base deve contenere 8 NPC esatti')
    mgr=services.sim_info_manager()
    if mgr is None:
        raise ValueError('SimInfoManager assente')
    for sid in enrolled:
        info=mgr.get(int(sid))
        if (info is None or getattr(info,'age',None)!=Age.TEEN
                or getattr(info,'species',None)!=Species.HUMAN):
            raise ValueError('Sim iscritto non umano teen')
        if (sid in base or sid in pinned.values()) and getattr(info,'is_selectable',True) is not False:
            raise ValueError('Base scelto non NPC')
    return slot,base,{int(job):str(sid) for job,sid in pinned.items()}


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
        self.m140_patch_checked=False
        self.m140_patch_result=None
        self.m140_patch_undo=None
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
        if not self.active or not self.in_school():
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
        if not (native_base or native_core or native_lesson or native_prep):
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
        if (len(self.targets)!=8 or len(set(self.targets))!=8
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
            self.base_count_calls+=1
            self.base_count_last=result
            if (result==(3,3) and not self.created
                    and self.pending is None):
                self.base_count_overrides+=1
                return (8,8)
            return result

        def create(obj,kind,*args,**kwargs):
            guid=getattr(kind,'guid64',None)
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
                self.core_pending=True
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
                    else:
                        self.core_failures+=1
                        self.error='EA_CORE_NO_SITUATION_ID'
                    return native
                finally:
                    self.core_pending=False
            if (not self.active or not self.in_school()
                    or getattr(kind,'guid64',None)!=BASE_SITUATION
                    or len(self.created)>=8
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
        if any(owner.__dict__.get(name) is not fn
               for (owner,name),fn in self.wrappers.items()):
            self.error='THIRD_PARTY_RESTORE_CONFLICT'
            return False
        for req,prior in tuple(self._tracked.items()):
            if getattr(req,'_sim_filter',None) is self.blank:
                req._sim_filter=prior
        self._tracked.clear()
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
    if _RUNTIME is not None and _RUNTIME.active:
        return 'M142 gia attiva: '+_RUNTIME.report()
    try:
        zone,schedule=zone_schedule()
        if zone is None or schedule in SCHOOL_SCHEDULES:
            return 'M142 BLOCCATA: armare da casa prima della scuola'
        slot,targets,pinned=registered_eight()
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
        roster=RosterStore(FOLDER).load(slot)
        groups=tuple(tuple(str(s) for s in roster.class_members(i))
                     for i in (1,2))
        if (len(groups[0])!=8 or len(groups[1])!=8
                or len(set(groups[0]+groups[1]))!=16):
            return 'M142 BLOCCATA: registro classi 1 e 2 non valido'
        trial.lesson_classes=groups
        job_mgr=services.get_instance_manager(Types.SITUATION_JOB)
        trial.lesson_jobs={j:job_mgr.get(j)
                           for j in set(x[1] for x in LESSON_JOBS.values())}
        trial.prep_jobs={j:job_mgr.get(j)
                         for j in set(x[1] for x in PREP_JOBS.values())}
        if any(v is None or getattr(v,'guid64',None)!=j
               for j,v in tuple(trial.lesson_jobs.items())+tuple(trial.prep_jobs.items())):
            return 'M142 BLOCCATA: originali job lezione EA assenti'
        if not trial.install():
            return 'M142 BLOCCATA: owner EA modificato o non disponibile'
        # Apply the board compatibility while still home, *before* entering
        # the school: this removes the M137 09:30 timing race entirely.
        # If the EA/Zerbu test differs, original rules stay untouched.
        trial.m140_patch_checked=True
        try:
            manager=services.get_instance_manager(Types.INTERACTION)
            affordance=manager.get(PLAYER_CLASS_START) if manager else None
            trial.m140_patch_result,trial.m140_patch_undo=(
                install_known_whiteboard_adapter(affordance))
        except Exception as exc:
            trial.m140_patch_result={
                'applied':False,'reason':'COMPAT_'+type(exc).__name__}
        _RUNTIME=trial
        _m141_start_watcher(trial)
        return 'M142 PRONTA: 13 NPC + registrazione scuola/mensa automatica'
    except Exception as exc:
        return 'M142 NON ATTIVA: '+type(exc).__name__+': '+str(exc)[:100]


@sims4.commands.Command('mhs142.arm',
    command_type=sims4.commands.CommandType.Live)
def m127arm(_connection=None):
    sims4.commands.output(arm_m127(),_connection)


@sims4.commands.Command('mhs142.status',
    command_type=sims4.commands.CommandType.Live)
def m127status(_connection=None):
    sims4.commands.output(
        _RUNTIME.report() if _RUNTIME is not None
        else 'M142 non attiva',_connection)


@sims4.commands.Command('mhs142.stop',
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


@sims4.commands.Command('mhs142.classi',
    command_type=sims4.commands.CommandType.Live)
def m127classi(_connection=None):
    sims4.commands.output(_snapshot_classes('lesson'),_connection)


@sims4.commands.Command('mhs142.prepara',
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


@sims4.commands.Command('mhs142.azioni',
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


@sims4.commands.Command('mhs142.dettagli',
    command_type=sims4.commands.CommandType.Live)
def m127details(_connection=None):
    report,error=_capture_actions()
    if error is not None:
        sims4.commands.output(error,_connection)
        return
    import json
    os.makedirs(FOLDER,exist_ok=True)
    filename=os.path.join(FOLDER,'MHS_M142_LEZIONI_RUOLI_AZIONI.json')
    with open(filename,'w',encoding='utf-8') as file:
        json.dump(report,file,indent=2,ensure_ascii=False)
    sims4.commands.output(
        'M142: creato MHS_M142_LEZIONI_RUOLI_AZIONI.json (16 Sim). '
        'Nessuna azione del Sim modificata.',_connection)

# M142 manual opt-in recovery: a single known off-task mirror interaction.
_M140_ATTEMPTED=set()
_M140_ZONE_KEY=None


def _m125_candidates(perform):
    global _M140_ZONE_KEY
    if _RUNTIME is None or not _RUNTIME.active:
        return 'M142 RECUPERO: attiva mhs142.arm a casa'
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


@sims4.commands.Command('mhs142.candidati',
    command_type=sims4.commands.CommandType.Live)
def m127candidates(_connection=None):
    sims4.commands.output(_m125_candidates(False),_connection)


@sims4.commands.Command('mhs142.rientro',
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


@sims4.commands.Command('mhs142.tempo',
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
    file=os.path.join(FOLDER,'MHS_M142_ORARI_PERCORSI_EA.json')
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
        'file=MHS_M142_ORARI_PERCORSI_EA.json'.format(
            len(_M140_TIMED_SNAPSHOTS),result['school_job_count'],
            sum(x['phase']=='preparation'
                for x in _RUNTIME.m127_timing_events),
            sum(x['phase']=='lesson'
                for x in _RUNTIME.m127_timing_events)),
        _connection)

def _m128_trait_context():
    if _RUNTIME is None or not _RUNTIME.active:
        return None,None,'M142: eseguire mhs142.arm a casa'
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


@sims4.commands.Command('mhs142.verifica',
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
        filepath=os.path.join(FOLDER,'MHS_M142_TRATTI_EA.json')
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
        'file=MHS_M142_TRATTI_EA.json NESSUNA_MODIFICA'.format(
            len(missing),
            sum(1 for r in missing if r['registered_class']==1),
            sum(1 for r in missing if r['registered_class']==2)),
        _connection)


@sims4.commands.Command('mhs142.allinea',
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


@sims4.commands.Command('mhs142.aula',
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
        filename=os.path.join(FOLDER,'MHS_M142_LAVAGNE_POSTURE_EA.json')
        with open(filename,'w',encoding='utf-8') as stream:
            json.dump(report,stream,indent=2,ensure_ascii=False)
        sims4.commands.output(
            'M142 AULA: studenti={} tratti_errati={} '
            'lavagne_condivise={} NESSUNA_MODIFICA '
            'file=MHS_M142_LAVAGNE_POSTURE_EA.json'.format(
                report['count'],report['trait_mismatches'],
                len(report['board_ids_targeted_by_both_classes'])),
            _connection)
    except Exception as exc:
        sims4.commands.output(
            'M142 AULA: errore '+type(exc).__name__,_connection)

_M140_ANCHORS=None
_M140_READBACKS=[]


@sims4.commands.Command('mhs142.posti',
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
                FOLDER,'MHS_M142_POSTI_AULE_EA.json'),
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


@sims4.commands.Command('mhs142.giocabili',
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


@sims4.commands.Command('mhs142.sync',
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


@sims4.commands.Command('mhs142.causa',
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
                FOLDER,'MHS_M142_CAUSA_RIFIUTO_EA.json'),
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
            'M142 CAUSA: file=MHS_M142_CAUSA_RIFIUTO_EA.json '
            'NESSUNA MODIFICA AL GIOCO',_connection)
    except Exception as exc:
        sims4.commands.output(
            'M142 CAUSA: errore '+type(exc).__name__,_connection)


@sims4.commands.Command('mhs142.ruoli',
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
        filename='MHS_M142_RUOLI_EA_GIOCABILI.json'
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


@sims4.commands.Command('mhs142.testgiocabili',
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
        if len(played)!=3:raise ValueError('EXPECTED_THREE_PLAYABLE_TEENS')
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
        filename='MHS_M142_TEST_EA_GIOCABILI.json'
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


@sims4.commands.Command('mhs142.compat',
    command_type=sims4.commands.CommandType.Live)
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

@sims4.commands.Command('mhs142.auto',
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
def _m141_capture(runtime,event='interval'):
    journal=runtime.m141_journal
    if journal is None or not runtime.active or not runtime.in_school():
        return False
    try:
        if str(current_slot(allow_travel=True))!=runtime.slot:
            runtime.m141_last_tick_error='SAVE_SLOT_CHANGED'
            return False
        manager=services.sim_info_manager()
        if manager is None:
            raise ValueError('NO_SIM_MANAGER')
        rows=[]
        for klass,group in enumerate(runtime.lesson_classes,1):
            for sid in group:
                info=manager.get(int(sid))
                row=observe_student(info,klass)
                if row.get('sim_id') is None:
                    row['sim_id']=str(sid)
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
        ok=journal.append(game_clock(services.time_service()),rows,
                          event,player_jobs,
                          runtime.m140_auto_reports[-4:]+
                          runtime.m142_retry_reports[-4:])
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
        if runtime.lesson_classes is None:
            raise ValueError('ROSTER_UNAVAILABLE')
        if runtime.m141_journal is None:
            runtime.m141_journal=DayJournal(
                FOLDER,runtime.slot,runtime.lesson_classes)
        import alarms
        import clock
        def sample(handle):
            if not runtime.active or not runtime.in_school():
                _m141_stop_trace(runtime)
                return
            _m142_roll_period_if_due(runtime,
                                     game_clock(services.time_service()))
            _m141_capture(runtime,'interval')
            _m142_retry_playables(runtime)
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


@sims4.commands.Command('mhs142.log',
    command_type=sims4.commands.CommandType.Live)
def m141_log(_connection=None):
    if _RUNTIME is None or not _RUNTIME.active:
        sims4.commands.output('M142 LOG: non attiva, attivare da casa',_connection)
        return
    if _RUNTIME.m141_timer is None and _RUNTIME.in_school():
        _m141_start_trace(_RUNTIME,'log_fallback')
    if _RUNTIME.m141_journal is None:
        sims4.commands.output(
            'M142 LOG: registrazione non avviata; errore={}'.format(
                _RUNTIME.m141_start_error or 'nessuno'),_connection)
        return
    _m141_capture(_RUNTIME,'manual_status_snapshot')
    ok=_RUNTIME.m141_journal.flush()
    _m142_write_lunch_summary(_RUNTIME)
    sims4.commands.output(
        'M142 LOG: campioni={} salvato={} errore={} file={}'.format(
        len(_RUNTIME.m141_journal.samples),ok,
        _RUNTIME.m141_last_tick_error or
        _RUNTIME.m141_journal.write_error or 'nessuno',
        'MHS_M142_GIORNATA_LEZIONI_MENSA.json'),_connection)


@sims4.commands.Command('mhs142.monitor',
    command_type=sims4.commands.CommandType.Live)
def m141_monitor(_connection=None):
    if _RUNTIME is None:
        sims4.commands.output('M142 MONITOR: non attiva',_connection)
        return
    if _RUNTIME.active and _RUNTIME.in_school() and _RUNTIME.m141_timer is None:
        _m141_start_trace(_RUNTIME,'monitor_fallback')
    j=_RUNTIME.m141_journal
    sims4.commands.output(
        'M142 MONITOR: scuola={} timer={} campioni={} periodo={} riprese={} origine={} errore={}'.format(
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
            clock, next(iter(PREP_JOBS)), PREP_JOBS,
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


def _m142_retry_playables(runtime):
    """Push once more only when exact player class EA role is active.

    NEVER interact with NPCs, never run in lunch, and never forcibly cancel
    a running action. A successful request still does not prove classroom entry.
    """
    if not runtime.active or not runtime.in_school():
        return False
    try:
        clock_value=game_clock(services.time_service())
        minute=minute_of_day(clock_value)
        if minute is None or not (
                10*60+4<=minute<=10*60+15 or
                14*60+4<=minute<=14*60+15):
            return False
        slot=str(current_slot(allow_travel=True))
        if slot!=runtime.slot:
            return False
        roster=RosterStore(FOLDER).load(slot)
        groups=tuple(tuple(str(s) for s in roster.class_members(k))
                     for k in (1,2))
        if groups!=runtime.lesson_classes:
            return False
        played=find_playable_entry(groups,services.sim_info_manager(),
                                   services.active_household())
        if not played:
            return False
        from mhs134_native_player_job_audit import inspect_player_jobs
        detail=inspect_player_jobs(
            played,services.get_zone_situation_manager(),None)
        jobs={str(j['sim_id']):j for j in detail.get('students',())}
        ready=[]
        for row in played:
            sid=str(row['sim_id'])
            try:
                sim=row['sim_info'].get_sim_instance()
                running=getattr(getattr(sim,'queue',None),'running',None)
                name=(type(running).__name__ if running else None)
            except Exception:
                name=None
            allow,reason=class_retry_decision(
                clock_value,runtime.m142_period,row,jobs.get(sid),
                sid in runtime.m142_auto_accepted,
                (runtime.m142_period,sid) in runtime.m142_retry_attempted,
                name)
            if allow:
                ready.append(row)
        if not ready:
            return False
        boards,status=_m131_state_evidence()
        if status!='TWO_VALIDATED_EA_CLASS_BOARDS':
            runtime.m142_retry_reports.append({
                'period':runtime.m142_period,'reason':status,
                'attempted':False})
            return False
        from sims4.resources import Types
        affordance=services.get_instance_manager(Types.INTERACTION).get(
            PLAYER_CLASS_START)
        if affordance is None:
            runtime.m142_retry_reports.append({
                'period':runtime.m142_period,
                'reason':'EA_AFFORDANCE_MISSING','attempted':False})
            return False
        from interactions.context import InteractionContext
        from interactions.priority import Priority
        def context(sim):
            return InteractionContext(
                sim,InteractionContext.SOURCE_SCRIPT_WITH_USER_INTENT,
                Priority.High)
        for row in ready:
            sid=str(row['sim_id'])
            runtime.m142_retry_attempted.add((runtime.m142_period,sid))
            result=queue_playable_class((row,),boards,affordance,context)
            runtime.m142_retry_reports.append({
                'period':runtime.m142_period,
                'clock':clock_value,
                'sim_id':sid,
                'registered_class':row['registered_class'],
                'reason':result.get('reason'),
                'results':result.get('results',()),
                'attempted':True,
                'native_job_required':True,
                'does_not_prove_action_completed':True})
        _m141_capture(runtime,'m142_bounded_playable_retry')
        return True
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
        path=os.path.join(FOLDER,'MHS_M142_MENSA_NPC_ATTESE.json')
        with open(path,'w',encoding='utf-8') as output:
            json.dump(summary,output,indent=2,ensure_ascii=False)
        return True
    except Exception as exc:
        runtime.m141_last_tick_error='LUNCH_REPORT_'+type(exc).__name__
        return False


@sims4.commands.Command('mhs142.mensa',
    command_type=sims4.commands.CommandType.Live)
def m142_mensa(_connection=None):
    if _RUNTIME is None or _RUNTIME.m141_journal is None:
        sims4.commands.output(
            'M142 MENSA: monitor non avviato',_connection)
        return
    success=_m142_write_lunch_summary(_RUNTIME)
    sims4.commands.output(
        'M142 MENSA: salvato={} file=MHS_M142_MENSA_NPC_ATTESE.json '
        'NESSUNA AZIONE MODIFICATA'.format(success),_connection)


@sims4.commands.Command('mhs142.periodi',
    command_type=sims4.commands.CommandType.Live)
def m142_periods(_connection=None):
    if _RUNTIME is None:
        sims4.commands.output('M142 PERIODI: non attiva',_connection)
        return
    sims4.commands.output(
        'M142 PERIODI: fase={} pomeriggio_riarmato={} '
        'richieste_automatiche={} riprese_limitate={} lezione_create={} '
        'orari_eventi={}'.format(
        _RUNTIME.m142_period,_RUNTIME.m142_afternoon_rearmed,
        len(_RUNTIME.m142_auto_accepted),
        len(_RUNTIME.m142_retry_attempted),
        sorted(_RUNTIME.lesson_created),
        _RUNTIME.m142_afternoon_roll_events[-2:]),_connection)
