"""M104 opt-in native EA Base Student matching (NO new school situations).

Different design from failed late-invite M61 and original-guest M101:
the default EA Bouncer request stays 100% intact. Only the candidate
pool passed to *one native submit_matching_filter* changes to enrolled
NPC IDs, with native fallback disabled for that request.

This is a limited test, not a 16-student school attendance solution.
Manual arm before traveling to school, once per game process/day.
"""
import inspect
import json
import os
import services
import sims4.commands
from date_and_time import sim_ticks_per_day
from sims.sim_info_types import Age,Species
from mhs_m2_game_bridge import current_slot
from mhs_m2_store import RosterStore
from mhs34_settings import SettingsStore
from mhs57_filter_policy import guid_for_filter
import mhs57_filter_runtime as m57
from mhs104_native_policy import eligible_npcs,native_base_arguments

DIR=os.path.join(os.path.expanduser('~'),'Documents',
                 'Electronic Arts','The Sims 4','MY_HIGH_SCHOOL_M25_TEST_DATA')
REPORT='MHS_M104_NATIVO_FILTRO_EA.json'
_ARMED=None
_ATTEMPTED=False
_OLD=None
_INSTALLED=False
_STATE={'phase':'NOT_ARMED'}

def _day():
    return int(services.time_service().sim_now.absolute_ticks())//int(sim_ticks_per_day())

def _zone():
    zone=services.current_zone()
    return str(getattr(zone,'id',None)) if zone is not None else None

def _write():
    try:
        if not os.path.isdir(DIR):
            os.makedirs(DIR)
        dest=os.path.join(DIR,REPORT)
        temp=dest+'.tmp'
        with open(temp,'w',encoding='utf-8') as fd:
            json.dump(dict(_STATE,kind='M104_ONE_NATIVE_EA_BASE_FILTER',
                           extra_situations_created=0,
                           guest_lists_changed=False,
                           attendance_not_yet_proved=True),fd,
                      indent=2,sort_keys=True)
        os.replace(temp,dest)
    except Exception:
        pass

def _set(phase,**parts):
    _STATE.clear()
    _STATE.update({'phase':phase})
    _STATE.update(parts)
    _write()

def _school_candidates():
    """Load exact save-scoped 2x8 roster only when needed."""
    slot=str(current_slot(allow_travel=True))
    settings=SettingsStore(DIR).load(slot)
    if not settings.active or settings.class_count!=2:
        return None
    roster=RosterStore(DIR).load(slot)
    groups=tuple(tuple(roster.class_members(k)) for k in (1,2))
    manager=services.sim_info_manager()
    if manager is None:
        return None
    for ids in groups:
        for raw in ids:
            info=manager.get(int(raw))
            if (info is None or getattr(info,'age',None)!=Age.TEEN
                    or getattr(info,'species',None)!=Species.HUMAN):
                return None
    household=services.active_household()
    if household is None:
        return None
    playable=tuple(int(s.sim_id) for s in household.sim_info_gen()
                   if getattr(s,'age',None)==Age.TEEN
                   and getattr(s,'species',None)==Species.HUMAN)
    present=tuple(int(info.sim_id) for info in manager.get_all()
                  if info.get_sim_instance() is not None)
    eligible=eligible_npcs(groups,playable,present)
    return (slot,groups,playable,eligible)

def _native_bouncer_caller():
    # Base filter 280516 is specific to high school, but ensure the
    # current request really belongs to EA's Bouncer request path.
    frame=inspect.currentframe()
    try:
        for _ in range(28):
            frame=frame.f_back if frame is not None else None
            if frame is None:
                break
            module=str(frame.f_globals.get('__name__',''))
            if (module.split('.')[-1]=='bouncer'
                    and frame.f_code.co_name in (
                        '_spawn_all_during_zone_spin_up',
                        '_spawn_sim_for_next_request',
                        '_submit_filter_request',
                        '_request_sim_filter',
                        '_request_sim_filter_service',
                        '_spawn_sim_for_request',
                        '_find_sim_for_request')):
                return True
    finally:
        del frame
    return False

def _native_filter(previous,service,args,kwargs,mode):
    global _ATTEMPTED
    # M57 normally observes. Never turn on its global staff/club hooks.
    if (_ARMED is None or _ATTEMPTED or mode!='matching'):
        return _OLD(previous,service,args,kwargs,mode)
    tuning=kwargs.get('sim_filter',args[1] if len(args)>1 else None)
    if guid_for_filter(tuning)!=280516:
        return _OLD(previous,service,args,kwargs,mode)
    if (str(current_slot(allow_travel=True))!=_ARMED[0]
            or _day()!=_ARMED[1] or _zone()==_ARMED[2]
            or _zone() is None or not _native_bouncer_caller()):
        return _OLD(previous,service,args,kwargs,mode)
    # A single real original EA matching request. If guards fail,
    # preserve vanilla. Do not try again with a different request.
    _ATTEMPTED=True
    try:
        loaded=_school_candidates()
        if loaded is None or loaded[0]!=_ARMED[0]:
            _set('BYPASS_INVALID_ROSTER_OR_ZONE')
            return previous(service,*args,**kwargs)
        slot,groups,playable,npc_ids=loaded
        action,newargs,newkwargs,reason=native_base_arguments(
            mode,args,kwargs,280516,npc_ids)
        if action!='constrain':
            _set('BYPASS_'+action.upper(),reason=reason,
                 matching_filter_guid=280516)
            return previous(service,*args,**kwargs)
        _set('NATIVE_EA_BASE_FILTER_CONSTRAINED',
             matching_filter_guid=280516,
             allowed_npc_ids=list(npc_ids),
             allowed_count=len(npc_ids),
             playable_count=len(playable),
             original_school_situation_untouched=True,
             new_situation_created=False,
             save_slot=slot,school_zone_id=_zone())
    except Exception as exc:
        _set('FILTER_OVERRIDE_BYPASSED_ERROR',error_type=type(exc).__name__)
        return previous(service,*args,**kwargs)
    # Call EA exactly once, OUTSIDE the preparation exception guard:
    # never retry the underlying EA operation if it raises.
    return previous(service,*newargs,**newkwargs)

def arm():
    global _ARMED,_ATTEMPTED
    try:
        loaded=_school_candidates()
        if loaded is None:
            return 'M104 BLOCCATA: registro 2x8 non valido'
        slot,groups,playable,eligible=loaded
        # Exactly the known 16-member test and three accompanied teens.
        if len(playable)!=3 or eligible is None or len(eligible)!=13:
            return 'M104 BLOCCATA: servono 16 iscritti, 3 giocabili, 13 NPC'
        if not install():
            return 'M104 BLOCCATA: EA filter hook non disponibile'
        _ARMED=(slot,_day(),_zone())
        _ATTEMPTED=False
        _set('ARMED_FOR_ONE_NATIVE_EA_FILTER',
             save_slot=slot,school_day=_ARMED[1],
             home_zone_id=_ARMED[2],
             registered=16,accompanied=3,npc_count=13)
        return 'M104 armata: una selezione scolastica EA nativa | '+REPORT
    except Exception as exc:
        _set('ARM_FAILED',error_type=type(exc).__name__)
        return 'M104 BLOCCATA: '+type(exc).__name__

def off():
    global _ARMED
    _ARMED=None
    _set('DISABLED_BY_USER')
    return 'M104 disattivata; nessun altro filtro verrà modificato'

def check():
    phase=_STATE.get('phase','NOT_ARMED')
    if phase!='NATIVE_EA_BASE_FILTER_CONSTRAINED':
        return 'M104: '+phase+' | '+REPORT
    try:
        if (not _ARMED or str(current_slot(allow_travel=True))!=_ARMED[0]
                or _zone()!=_STATE.get('school_zone_id')):
            return 'M104: controllo disponibile nel lotto scolastico attuale'
        info=services.sim_info_manager()
        entered=tuple(sid for sid in _STATE.get('allowed_npc_ids',())
                      if (info.get(int(sid)) is not None
                          and info.get(int(sid)).get_sim_instance() is not None))
        data=dict(_STATE)
        data['on_lot_registered_npc_ids']=list(entered)
        data['on_lot_registered_npc_count']=len(entered)
        _set(phase,**{k:v for k,v in data.items() if k!='phase'})
        return ('M104: EA filtro originale modificato | NPC iscritti sul '
                'lotto: {} | {}').format(len(entered),REPORT)
    except Exception as exc:
        return 'M104 verifica non disponibile: '+type(exc).__name__

def install():
    global _INSTALLED,_OLD
    if _INSTALLED:
        return True
    if not callable(getattr(m57,'_filtered',None)):
        return False
    if not m57.installed():
        return False
    _OLD=m57._filtered
    m57._filtered=_native_filter
    _INSTALLED=True
    return True

@sims4.commands.Command('mhs104.arm',
                        command_type=sims4.commands.CommandType.Live)
def _arm_cmd(_connection=None):
    sims4.commands.output(arm(),_connection)

@sims4.commands.Command('mhs104.check',
                        command_type=sims4.commands.CommandType.Live)
def _check_cmd(_connection=None):
    sims4.commands.output(check(),_connection)

@sims4.commands.Command('mhs104.off',
                        command_type=sims4.commands.CommandType.Live)
def _off_cmd(_connection=None):
    sims4.commands.output(off(),_connection)
