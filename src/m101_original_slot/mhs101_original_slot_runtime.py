"""M101: opt-in ONE original EA school slot trial, not an extra situation.

Arm from console BEFORE travelling to the school on a school morning:
  mhs101.arm
The only eligible call is the EA WeeklyScheduleDay original Base request
with spawn_sims_during_zone_spin_up=True. We query EA's real 280516
filter synchronously, constrained to the 13 enrolled NPC IDs. If this
can't be proved or the query is deferred, keep the original vanilla call.
No staff/core/venue overrides; no extra situations; no random retries.

TEST SAVE ONLY, NOT A FULL-ROSTER RELEASE. Never install with M94/M99.
"""
import inspect
import json
import os
import services
from sims.sim_info_types import Age,Species
from sims4.resources import Types
from date_and_time import sim_ticks_per_day
from mhs_m2_game_bridge import current_slot
from mhs_m2_store import RosterStore
from mhs34_settings import SettingsStore
from mhs55_attendance_core import valid_student
from mhs89_precreate_hook import install as install_precreate
from mhs100_one_slot_policy import OneSlotPilot,select_one
from mhs101_original_slot_gate import original_school_call,validated_filter_ids
from mhs99_situation_trace import snapshot as trace_situation

DIR=os.path.join(os.path.expanduser('~'),'Documents','Electronic Arts',
                 'The Sims 4','MY_HIGH_SCHOOL_M25_TEST_DATA')
REPORT='MHS_M101_UNO_SLOT_EA.json'
_BASE=277733
_JOB=277894
_FILTER=280516
_ARMED=None
_STATE={'phase':'NOT_ARMED'}
_PILOT=OneSlotPilot()
_INSTALLED=False

def _now_day():
    service=services.time_service()
    now=service.sim_now
    return int(now.absolute_ticks())//int(sim_ticks_per_day())

def _zone():
    current=services.current_zone()
    if current is None:
        return None
    return str(getattr(current,'id',None))

def _write():
    try:
        if not os.path.isdir(DIR):
            os.makedirs(DIR)
        dest=os.path.join(DIR,REPORT)
        temp=dest+'.tmp'
        with open(temp,'w',encoding='utf-8') as fd:
            json.dump(dict(_STATE,kind='M101_ONE_ORIGINAL_EA_SCHOOL_SLOT',
                           full_roster_controlled=False),fd,indent=2,
                      sort_keys=True)
        os.replace(temp,dest)
    except Exception:
        pass

def _set(phase,**details):
    _STATE.clear()
    _STATE.update({'phase':phase})
    _STATE.update(details)
    _write()

def _parents():
    result=[]
    frame=inspect.currentframe()
    try:
        for _ in range(18):
            frame=frame.f_back if frame is not None else None
            if frame is None:
                break
            if frame.f_code.co_name=='start_long_term_situation':
                module=frame.f_globals.get('__name__','')
                if module.split('.')[-1]=='weekly_schedule_zone_director':
                    result.append('weekly_schedule_zone_director')
    finally:
        del frame
    return tuple(result)

def _valid_roster():
    slot=current_slot(allow_travel=True)
    settings=SettingsStore(DIR).load(slot)
    if not settings.active or settings.class_count!=2:
        return None
    roster=RosterStore(DIR).load(slot)
    classes=tuple(tuple(str(s) for s in roster.class_members(k))
                  for k in (1,2))
    if len(classes[0])!=8 or len(classes[1])!=8:
        return None
    everyone=classes[0]+classes[1]
    if len(set(everyone))!=16:
        return None
    simmgr=services.sim_info_manager()
    if simmgr is None or any(
            not valid_student(simmgr.get(int(sid)),Age.TEEN,Species.HUMAN)
            for sid in everyone):
        return None
    household=services.active_household()
    if household is None:
        return None
    playable=tuple(str(s.sim_id) for s in household.sim_info_gen()
                   if valid_student(s,Age.TEEN,Species.HUMAN))
    if not set(playable)<=set(everyone):
        return None
    ordinary=tuple(int(sid) for sid in everyone if sid not in playable)
    if not ordinary:
        return None
    present=tuple(int(info.sim_id) for info in simmgr.get_all()
                  if info.get_sim_instance() is not None)
    return slot,classes,playable,ordinary,present

def _actual_filter_ids(ordinary):
    """Diagnostic M101b: tell API errors apart from genuinely empty filters.

    The result MUST be actual scored EA filter matches; no guessing from
    enrolled teen age or arbitrary SimInfo IDs. Never spawns a Sim.
    """
    evidence={'requested_filter_guid':_FILTER,'candidate_count':len(ordinary),
              'phase':'NOT_QUERIED','eligible_count':0}
    try:
        if not hasattr(Types,'SIM_FILTER'):
            evidence['phase']='MISSING_SIM_FILTER_RESOURCE_TYPE'
            return (),evidence
        manager=services.get_instance_manager(Types.SIM_FILTER)
        if manager is None:
            evidence['phase']='NO_EA_FILTER_INSTANCE_MANAGER'
            return (),evidence
        filt=manager.get(_FILTER)
        if filt is None:
            evidence['phase']='MISSING_EA_BASE_FILTER_TUNING'
            return (),evidence
        service=services.sim_filter_service()
        if service is None:
            evidence['phase']='NO_EA_FILTER_SERVICE'
            return (),evidence
        method=getattr(service,'submit_filter',None)
        if not callable(method):
            evidence['phase']='NO_SUBMIT_FILTER_METHOD'
            return (),evidence
        evidence['phase']='CALLING_EA_FILTER'
        actual=method(sim_filter=filt,sim_constraints=ordinary,
                      allow_yielding=False)
        evidence['result_type']=type(actual).__name__
        if actual is None:
            evidence['phase']='EA_FILTER_RETURNED_NONE'
            return (),evidence
        if not isinstance(actual,(tuple,list)):
            evidence['phase']='EA_FILTER_UNEXPECTED_RESULT_TYPE'
            return (),evidence
        evidence['raw_result_count']=len(actual)
        if not actual:
            evidence['phase']='EA_FILTER_RETURNED_EMPTY'
            return (),evidence
        evidence['sample_result_type']=type(actual[0]).__name__
        evidence['sample_has_sim_info']=getattr(actual[0],'sim_info',None) is not None
        evidence['sample_has_score']=hasattr(actual[0],'score')
        ids=validated_filter_ids(actual,ordinary)
        evidence['eligible_count']=len(ids)
        evidence['phase']=('EA_FILTER_VERIFIED_MATCH' if ids else
                           'EA_FILTER_RESULTS_NOT_VERIFIED')
        return ids,evidence
    except Exception as exc:
        evidence['phase']='EA_FILTER_QUERY_EXCEPTION'
        evidence['exception_type']=type(exc).__name__
        return (),evidence

def arm():
    global _ARMED,_PILOT
    try:
        slot,classes,playable,ordinary,present=_valid_roster()
        day=_now_day()
        if _zone() is None or len(ordinary)>16:
            raise ValueError('lotto o registro non valido')
        # The arm is ephemeral: it does not persist across restarts.
        # The next school-zone load must have exactly this save/day.
        if not install():
            raise RuntimeError('aggancio originale EA non disponibile')
        _ARMED=(str(slot),day)
        _PILOT=OneSlotPilot()
        _set('ARMED_BEFORE_SCHOOL',save_slot=str(slot),school_day=day,
             enrolled_count=16,npc_count=len(ordinary),
             playables=len(playable))
        return 'M101 armata: massimo 1 slot EA originale nella prossima visita al liceo. '+REPORT
    except Exception as exc:
        _ARMED=None
        _set('ARM_BLOCKED',error=type(exc).__name__)
        return 'M101 BLOCCATA: registro completo o slot EA non verificabile ('+type(exc).__name__+')'

def _context(manager,situation_type,guest_list,args,kwargs):
    if _ARMED is None or str(current_slot(allow_travel=True))!=_ARMED[0]:
        return False
    if _now_day()!=_ARMED[1]:
        return False
    if not original_school_call(getattr(situation_type,'guid64',None),
                                tuple(guest_list.guest_info_gen()),
                                kwargs,_parents()):
        return False
    return True

def _resolve(manager,situation,guests):
    if _ARMED is None:
        return None
    try:
        data=_valid_roster()
        if data is None:
            _set('SKIPPED_INVALID_ROSTER')
            return None
        slot,classes,playable,ordinary,present=data
        eligible,filter_evidence=_actual_filter_ids(ordinary)
        if not eligible:
            # Save the FIRST informative diagnostic rather than overwriting
            # it with each subsequent vanilla EA Base request.
            if _STATE.get('phase') not in (
                    'EA_ORIGINAL_CALL_ACCEPTED',
                    'ORIGINAL_SITUATION_CREATED',
                    'PRESELECTED_FOR_ORIGINAL_EA_BASE_CALL'):
                _set('SKIPPED_NO_VERIFIED_EA_BASE_FILTER_MATCH',
                     filter_guid=_FILTER,filter_diagnostic=filter_evidence)
            return None
        key=(str(slot),_zone(),_now_day())
        action,sid,reason=_PILOT.resolve(
            key,_BASE,tuple(),class_ids=classes,
            playable_ids=playable,eligible_base_ids=eligible,
            already_on_zone_ids=present,active_school=True,
            save_verified=True,zone_verified=True,day_verified=True)
        if action!='choose':
            # EA routinely issues more Base calls after the one pilot has
            # succeeded. Never erase its accepted situation ID or result.
            if _STATE.get('phase') not in (
                    'EA_ORIGINAL_CALL_ACCEPTED',
                    'ORIGINAL_SITUATION_CREATED',
                    'PRESELECTED_FOR_ORIGINAL_EA_BASE_CALL'):
                _set('SKIPPED_'+action.upper(),reason=reason)
            return None
        info=services.sim_info_manager().get(sid)
        if not valid_student(info,Age.TEEN,Species.HUMAN):
            _set('SKIPPED_SIM_CHANGED')
            return None
        _set('PRESELECTED_FOR_ORIGINAL_EA_BASE_CALL',
             name='{} {}'.format(info.first_name,info.last_name).strip(),
             sim_id=sid,save_slot=str(slot),zone_id=_zone(),
             class_id=1 if str(sid) in classes[0] else 2,
             eligible_ids_from_live_ea_filter=list(eligible),
             filter_diagnostic=filter_evidence)
        return (sid,True,True)
    except Exception as exc:
        _set('SKIPPED_ERROR',error=type(exc).__name__)
        return None

def _created(sid, situation_id):
    if (_PILOT.attempted and _PILOT.sim_id==sid
            and type(situation_id) is int and situation_id>0):
        data={k:v for k,v in _STATE.items() if k!='phase'}
        data['created_situation_id']=situation_id
        _set('ORIGINAL_SITUATION_CREATED',**data)

def _confirmed(sid):
    if _PILOT.confirm(sid):
        data={k:v for k,v in _STATE.items() if k!='phase'}
        _set('EA_ORIGINAL_CALL_ACCEPTED',**data)

def _check():
    sid=_STATE.get('sim_id')
    if sid is None:
        return 'M101: '+str(_STATE.get('phase','not armed'))+' | '+REPORT
    try:
        # Never claim an arrival from another save or a different lot.
        if (_ARMED is None or str(current_slot(allow_travel=True))!=_ARMED[0]
                or _STATE.get('zone_id')!=_zone()
                or _now_day()!=_ARMED[1]):
            return 'M101: controllo disponibile solo nello stesso lotto/giorno'
        info=services.sim_info_manager().get(int(sid))
        situation_id=_STATE.get('created_situation_id')
        if type(situation_id) is int and situation_id>0:
            checked=trace_situation(
                services.get_zone_situation_manager(),info,situation_id)
        else:
            checked={'phase':'SITUATION_ID_UNAVAILABLE',
                     'on_lot':bool(info is not None and info.get_sim_instance() is not None)}
        previous={k:v for k,v in _STATE.items()
                  if k not in ('phase','latest_verification')}
        previous['latest_verification']=checked
        # The outcome of the original call and the latest inspection are
        # different facts, and remain separately visible in the report.
        phase=_STATE.get('phase','UNKNOWN')
        _set(phase,**previous)
        return ('M101: {} | {} | {} | {}').format(
            phase,_STATE.get('name','Sim'),
            checked.get('phase','UNKNOWN'),REPORT)
    except Exception as exc:
        return 'M101 verifica non disponibile ('+type(exc).__name__+') | '+REPORT

def _install_commands():
    try:
        import sims4.commands
        @sims4.commands.Command('mhs101.arm',
                                command_type=sims4.commands.CommandType.Live)
        def _arm(_connection=None):
            sims4.commands.output(arm(),_connection)
        @sims4.commands.Command('mhs101.check',
                                command_type=sims4.commands.CommandType.Live)
        def _check_command(_connection=None):
            sims4.commands.output(_check(),_connection)
        return True
    except Exception:
        return False

def install():
    global _INSTALLED
    if _INSTALLED:
        return True
    try:
        from situations.situation_manager import SituationManager
        job=services.get_instance_manager(Types.SITUATION_JOB).get(_JOB)
        if job is None or getattr(job,'guid64',None)!=_JOB:
            return False
        from situations.situation_guest_list import (SituationGuestInfo,
                                                      SituationInvitationPurpose)
        result=install_precreate(
            SituationManager,_resolve,job,SituationGuestInfo,
            SituationInvitationPurpose.INVITED,
            on_applied=_confirmed,context_checker=_context,
            on_created=_created)
        _INSTALLED=result
        return result
    except Exception:
        return False

_install_commands()
install()
