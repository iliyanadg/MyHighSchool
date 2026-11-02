"""M61 one-student opt-in pilot via Sims 4 command console.

No automatic invitation. Command is explicit: mhs61.pilot
Operates only after verifying the saved roster and EA school situations.
Records at most ONE attempted invitation for a live zone/day, no retries.
"""
import services
from sims.sim_info_types import Age, Species
from mhs_m2_game_bridge import current_slot
from mhs_m2_store import RosterStore
from mhs34_settings import SettingsStore
from mhs55_attendance_core import (
    valid_student, school_running, already_in_base_student)
from mhs61_guest_adapter import create_one_existing_student
from mhs99_situation_trace import snapshot as trace_situation
import json

import os
ROOT=os.path.join(os.path.expanduser('~'),'Documents','Electronic Arts',
                  'The Sims 4','MY_HIGH_SCHOOL_M25_TEST_DATA')
_ATTEMPTED=set()
_LAST='non eseguito'
_LAST_TARGET=None
_LAST_SITUATION_ID=None
_TRACE_HISTORY=[]
_TRACE_HANDLE=None
_TRACE_POLL_COUNT=0
_TRACE_NAME='MHS_M99_INVITO_STUDENTE_TRACE.json'

def _stop_trace_alarm():
    global _TRACE_HANDLE
    if _TRACE_HANDLE is not None:
        try:
            import alarms
            alarms.cancel_alarm(_TRACE_HANDLE)
        except Exception:
            pass
        _TRACE_HANDLE=None


def _capture_trace():
    """Read-only evidence of EA situation + actual Sim arrival."""
    if _LAST_TARGET is None:
        return {'phase':'NO_PILOT_YET'}
    slot,zone_id,sid,name,klass=_LAST_TARGET
    result={'name':name,'student_id':sid,'class':klass,
            'created_situation_id':_LAST_SITUATION_ID,
            'save_slot':slot,'zone_id':zone_id}
    try:
        zone=services.current_zone()
        if str(getattr(zone,'id',None))!=zone_id or current_slot(allow_travel=True)!=slot:
            result['phase']='DIFFERENT_SAVE_OR_ZONE'
        else:
            mgr=services.get_zone_situation_manager()
            info=services.sim_info_manager().get(sid)
            result.update(trace_situation(mgr,info,_LAST_SITUATION_ID))
            service=services.time_service()
            now=getattr(service,'sim_now',None)
            ticks=getattr(now,'absolute_ticks',None)
            if callable(ticks):
                result['sim_absolute_ticks']=int(ticks())
    except Exception as exc:
        result['phase']='TRACE_ERROR'
        result['error']=type(exc).__name__
    _TRACE_HISTORY.append(result)
    del _TRACE_HISTORY[:-20]
    try:
        if not os.path.isdir(ROOT):
            os.makedirs(ROOT)
        target=os.path.join(ROOT,_TRACE_NAME)
        temp=target+'.tmp'
        with open(temp,'w',encoding='utf-8') as output:
            json.dump({'kind':'M99_EA_SCHOOL_SITUATION_LIFECYCLE_READ_ONLY',
                       'does_not_verify_correct_class_seating':True,
                       'events':_TRACE_HISTORY},output,
                      indent=2,sort_keys=True)
        os.replace(temp,target)
    except Exception:
        pass
    return result


def trace_status():
    record=_capture_trace()
    if record.get('phase')=='NO_PILOT_YET':
        return 'Nessuna convocazione M61 registrata'
    return ('{}: {} | situazione EA: {} | {}').format(
        record.get('name','Studente'),
        record.get('phase','UNKNOWN'),
        record.get('created_situation_id','?'),
        _TRACE_NAME)


def _trace_alarm(_handle=None):
    global _TRACE_POLL_COUNT
    _TRACE_POLL_COUNT+=1
    record=_capture_trace()
    # A situation may be queued/destroyed/recreated while EA is still
    # deciding whether to instantiate the guest. Keep tracing for the
    # full hour unless the save/zone changed; don't call one observation
    # a final conclusion.
    if (_TRACE_POLL_COUNT>=12 or
            record.get('phase')=='DIFFERENT_SAVE_OR_ZONE'):
        _stop_trace_alarm()


def _start_trace_alarm():
    global _TRACE_HANDLE,_TRACE_POLL_COUNT
    _stop_trace_alarm()
    _TRACE_POLL_COUNT=0
    try:
        import alarms
        from date_and_time import create_time_span
        zone=services.current_zone()
        if zone is not None:
            _TRACE_HANDLE=alarms.add_alarm(zone,create_time_span(minutes=5),
                                          _trace_alarm,repeating=True)
    except Exception:
        _TRACE_HANDLE=None


def pilot():
    """Explicit trial with fail-closed checks. Returns diagnostic string."""
    global _LAST,_LAST_TARGET,_LAST_SITUATION_ID
    try:
        zone=services.current_zone()
        mgr=services.get_zone_situation_manager()
        sims=services.sim_info_manager()
        if zone is None or mgr is None or sims is None:
            return 'BLOCCATO: zona o gestore EA non pronto'
        slot=current_slot(allow_travel=True)
        settings=SettingsStore(ROOT).load(slot)
        if not settings.active:
            return 'BLOCCATO: gestione MY HIGH SCHOOL non attiva'
        if not school_running(mgr,sims.get_all(),Age.TEEN):
            return 'BLOCCATO: situazione scolastica EA non verificata'
        roster=RosterStore(ROOT).load(slot)
        from date_and_time import sim_ticks_per_day
        now=services.time_service().sim_now
        day=int(now.absolute_ticks())//int(sim_ticks_per_day())
        key=(str(slot),str(getattr(zone,'id',None)),day)
        if key in _ATTEMPTED:
            return 'BLOCCATO: prova gia eseguita in questa giornata'
        if not callable(getattr(mgr,'get_situations_sim_is_in',None)):
            return 'BLOCCATO: verifica duplicati EA assente'
        household=services.active_household()
        home=set(str(s.sim_id) for s in household.sim_info_gen()) if household else set()
        candidate=None
        selected_class=None
        for klass in range(1,settings.class_count+1):
            for sid in roster.class_members(klass):
                info=sims.get(int(sid))
                if str(sid) in home or not valid_student(info,Age.TEEN,Species.HUMAN):
                    continue
                if info.get_sim_instance() is not None:
                    continue
                candidate=info
                selected_class=klass
                break
            if candidate is not None:
                break
        if candidate is None:
            return 'BLOCCATO: nessun adolescente idoneo da convocare'
        from sims4.resources import Types
        from situations.situation_guest_list import (
            SituationGuestList,SituationGuestInfo,SituationInvitationPurpose)
        sit=services.get_instance_manager(Types.SITUATION).get(277733)
        job=services.get_instance_manager(Types.SITUATION_JOB).get(277894)
        if sit is None or job is None:
            return 'BLOCCATO: tuning EA assente'
        # Mark BEFORE creating: never retry a failed or delayed EA request.
        _ATTEMPTED.add(key)
        _LAST_TARGET=(str(slot),str(getattr(zone,'id',None)),int(candidate.sim_id),
                      '{} {}'.format(getattr(candidate,'first_name',''),getattr(candidate,'last_name','')).strip(),selected_class)
        result=create_one_existing_student(
            mgr,sit,job,candidate.sim_id,
            SituationGuestList,SituationGuestInfo,
            SituationInvitationPurpose.INVITED)
        # EA's create_situation return value may be a situation ID. Keep
        # the actual ID, not just bool(result), for lifecycle inspection.
        _LAST_SITUATION_ID=result if type(result) is int and result>0 else None
        del _TRACE_HISTORY[:]
        _capture_trace()
        if _LAST_SITUATION_ID is not None:
            _start_trace_alarm()
        _LAST='Convocato {} (Classe {}), EA: {}. {}'.format(
            _LAST_TARGET[3],selected_class,bool(result),arrival_status())
        return _LAST
    except Exception as exc:
        _LAST='ERRORE '+type(exc).__name__
        return _LAST

def arrival_status():
    if _LAST_TARGET is None:
        return 'Nessuna convocazione M61 registrata'
    slot,zone_id,sid,name,klass=_LAST_TARGET
    try:
        zone=services.current_zone()
        if str(getattr(zone,'id',None))!=zone_id or current_slot(allow_travel=True)!=slot:
            return 'Controllo bloccato: lotto o salvataggio differente'
        info=services.sim_info_manager().get(sid)
        present=bool(info is not None and info.get_sim_instance() is not None)
        return '{} | Classe {} | {}'.format(name,klass,
                'PRESENTE sul lotto' if present else 'non ancora presente sul lotto')
    except Exception as exc:
        return 'Verifica indisponibile: {}'.format(type(exc).__name__)


def last_status():
    return _LAST

def install_command():
    try:
        import sims4.commands
        @sims4.commands.Command('mhs61.pilot',
                                command_type=sims4.commands.CommandType.Live)
        def _command(_connection=None):
            sims4.commands.output(pilot(),_connection)
        @sims4.commands.Command('mhs61.check',
                                command_type=sims4.commands.CommandType.Live)
        def _check(_connection=None):
            sims4.commands.output(arrival_status(),_connection)
        @sims4.commands.Command('mhs61.trace',
                                command_type=sims4.commands.CommandType.Live)
        def _trace(_connection=None):
            sims4.commands.output(trace_status(),_connection)
        return True
    except Exception:
        return False

install_command()
