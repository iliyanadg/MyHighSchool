"""M105 early-game native EA school filter connector; NOT in any release.

This module binds the already-tested pure M105 3+5+8 session to existing
M57 EA SimFilterService thin interception. Requires explicit preflight at
home and verified school schedule from venue zone director. No forced
situation, no late invitations, no immediate Sim spawning.

The EA calendar Base Student count is NOT overridden here: full 16
attendance remains unproven until five roles, the capacity, and lessons
are validated. No installable package includes this module yet.
"""
import inspect
import json
import os
import services
import sims4.commands
from date_and_time import sim_ticks_per_day
from mhs_m2_game_bridge import current_slot
from mhs57_filter_policy import guid_for_filter
from mhs105_live_preflight import prepare_live_school_day
from mhs105_native_session import SchoolSession,EXPECTED_SCHOOL_FILTERS

_ROOT=os.path.join(os.path.expanduser('~'),'Documents',
                   'Electronic Arts','The Sims 4',
                   'MY_HIGH_SCHOOL_M25_TEST_DATA')
_REPORT='MHS_M105_PIANO_PRE_LEZIONI.json'
_EA_SCHOOL_SCHEDULES=frozenset((277657,279958))
_SESSION=None
_OLD_FILTER=None
_INSTALLED=False
_LAST={'status':'NOT_ARMED',
       'runtime_in_package':False,
       'school_attendance_verified':False}

def _save():
    try:
        if not os.path.isdir(_ROOT):
            os.makedirs(_ROOT)
        dest=os.path.join(_ROOT,_REPORT)
        tmp=dest+'.tmp'
        with open(tmp,'w',encoding='utf-8') as fd:
            json.dump(_LAST,fd,indent=2,sort_keys=True)
        os.replace(tmp,dest)
    except Exception:
        pass

def _day():
    return (int(services.time_service().sim_now.absolute_ticks())
            //int(sim_ticks_per_day()))

def _zone():
    zone=services.current_zone()
    value=getattr(zone,'id',None) if zone is not None else None
    return str(value) if type(value) is int and value>0 else None

def _school_schedule_verified():
    """Read real EA High School schedule of this zone, not neighborhood."""
    try:
        venue=services.venue_service()
        if venue is None:
            return False
        director=venue.get_zone_director()
        if director is None:
            return False
        schedule=getattr(director,'_schedule',None)
        guid=getattr(schedule,'guid64',None)
        return type(guid) is int and guid in _EA_SCHOOL_SCHEDULES
    except Exception:
        return False

def _original_bouncer_origin():
    """Require a known EA Bouncer stack frame before altering requests."""
    frame=inspect.currentframe()
    try:
        for _ in range(28):
            frame=frame.f_back if frame is not None else None
            if frame is None:
                break
            if frame.f_globals.get('__name__','').split('.')[-1]=='bouncer':
                if frame.f_code.co_name in (
                    '_spawn_all_during_zone_spin_up',
                    '_spawn_sim_for_next_request','_submit_filter_request',
                    '_request_sim_filter','_request_sim_filter_service',
                    '_spawn_sim_for_request','_find_sim_for_request'):
                    return True
    finally:
        del frame
    return False

def _filtered(original,service,args,kwargs,mode):
    global _LAST
    if _SESSION is None or mode!='matching':
        return _OLD_FILTER(original,service,args,kwargs,mode)
    try:
        tuning=kwargs.get('sim_filter',args[1] if len(args)>1 else None)
        guid=guid_for_filter(tuning)
        if guid not in EXPECTED_SCHOOL_FILTERS:
            return _OLD_FILTER(original,service,args,kwargs,mode)
        decision,newargs,newkwargs=_SESSION.constrain(
            mode,guid,args,kwargs,slot=current_slot(allow_travel=True),
            day=_day(),zone=_zone(),
            bouncer=_original_bouncer_origin(),
            school_verified=_school_schedule_verified())
    except Exception as exc:
        _LAST={'status':'FILTER_CONTEXT_ERROR',
               'error_type':type(exc).__name__,
               'ea_school_not_modified':True}
        _save()
        # If preparation fails, delegate exactly once with original args.
        return _OLD_FILTER(original,service,args,kwargs,mode)
    if decision!='constrain':
        return _OLD_FILTER(original,service,args,kwargs,mode)
    _LAST=dict(_SESSION.evidence(),kind='M105_NATIVE_3_5_8_PREPARE',
               note='Constrained request is NOT proof of spawned Sim')
    _save()
    # The previous M57 wrapper remains in observation-only isolation,
    # preserving any unrelated installed EA filter hooks.
    return _OLD_FILTER(original,service,newargs,newkwargs,mode)

def _install():
    global _INSTALLED,_OLD_FILTER
    if _INSTALLED:
        return True
    import mhs57_filter_runtime as m57
    if not m57.installed() or not callable(m57._filtered):
        return False
    _OLD_FILTER=m57._filtered
    m57._filtered=_filtered
    _INSTALLED=True
    return True

def arm():
    global _SESSION,_LAST
    _SESSION=None
    result=prepare_live_school_day()
    if result['status']!='PREFLIGHT_READY_NOT_EA_BOUND':
        _LAST={'status':'BLOCKED_BY_PREFLIGHT',
               'reason':result.get('reason','unverified'),
               'filter_details':result.get('filter_details'),
               'game_unchanged':True}
        _save()
        return 'M105 BLOCCATA: '+_LAST['reason']
    home=_zone()
    if home is None or _school_schedule_verified():
        return 'M105 BLOCCATA: avvia prima da casa, fuori dal liceo'
    try:
        session=SchoolSession(result['plan'],result['save_slot'],_day(),home)
        if not _install():
            return 'M105 BLOCCATA: aggancio filtro EA non disponibile'
        _SESSION=session
        _LAST={'status':'ARMED_EARLY_NATIVE_FILTERS',
               'save_slot':result['save_slot'],
               'registered':16,'playable':3,'core':5,'base':8,
               'ea_school_roles_bound':False,
               'schedule_base_count_changed':False,
               'eight_per_class_verified':False}
        _save()
        return 'M105 prerequisiti approvati, controllo nativo armato'
    except Exception as exc:
        _LAST={'status':'ARM_BLOCKED','error_type':type(exc).__name__}
        _save()
        return 'M105 BLOCCATA: '+type(exc).__name__

def check():
    if _SESSION is None:
        return 'M105 non armata | '+_REPORT
    evidence=_SESSION.evidence()
    _LAST.update(evidence)
    _save()
    return ('M105 richieste native EA: Core {}/5 | Base {}/8. '
            'Presenze NON provate | {}').format(
                evidence['core_requests_constrained'],
                evidence['base_requests_constrained'],_REPORT)

def off():
    global _SESSION,_LAST
    if _SESSION is not None:
        _SESSION.cancel()
    _SESSION=None
    _LAST={'status':'OFF','game_selection_restored':True}
    _save()
    return 'M105 disattivata; selezione EA originale ripristinata'

@sims4.commands.Command('mhs105.arm',
                        command_type=sims4.commands.CommandType.Live)
def _arm_command(_connection=None):
    sims4.commands.output(arm(),_connection)

@sims4.commands.Command('mhs105.check',
                        command_type=sims4.commands.CommandType.Live)
def _check_command(_connection=None):
    sims4.commands.output(check(),_connection)

@sims4.commands.Command('mhs105.off',
                        command_type=sims4.commands.CommandType.Live)
def _off_command(_connection=None):
    sims4.commands.output(off(),_connection)
