"""Opt-in M106 EP12 native school request adapter (experimental, Mac).

Uses the actual six EA filter results and fixed 16 enrolled teens.
Intercepts only original EA Bouncer matching requests inside the verified
high-school zone and same save/day. Other filters pass through unchanged.

This does NOT increase EA's six Base situations. A successful constrained
request is NOT a spawned Sim, an assigned EA SituationJob, or seated student.
Only test on a duplicate save and never alongside a prior MHS beta.
"""
import json
import os
import services
import sims4.commands
from sims4.resources import Types
from mhs_m2_game_bridge import current_slot
from mhs57_filter_policy import guid_for_filter
from mhs93_verified_jobs import VERIFIED_SPECS
from mhs105_game_controller import (
    _day,_zone,_school_schedule_verified,_original_bouncer_origin,
    _m57_compatible)
from mhs106_live_preflight import prepare_live_roster_first,human_summary
from mhs106_school_session import M106Session

_FOLDER=os.path.join(os.path.expanduser('~'),'Documents','Electronic Arts',
                     'The Sims 4','MY_HIGH_SCHOOL_M25_TEST_DATA')
_REPORT='MHS_M106_PIANO_GIORNO.json'
_SESSION=None
_OLD_FILTER=None
_INSTALLED=False
_BASE_TUNING=None
_LAST={'status':'NOT_ARMED','attendance_verified':False}


def _save():
    try:
        if not os.path.isdir(_FOLDER):
            os.makedirs(_FOLDER)
        destination=os.path.join(_FOLDER,_REPORT)
        temp=destination+'.tmp'
        with open(temp,'w',encoding='utf-8') as stream:
            json.dump(_LAST,stream,sort_keys=True,indent=2)
        os.replace(temp,destination)
    except Exception:
        pass


def _filtered(original,service,args,kwargs,mode):
    """M57 delegates to us, which delegates exactly ONCE to original M57."""
    global _LAST
    if _SESSION is None or mode!='matching':
        return _OLD_FILTER(original,service,args,kwargs,mode)
    try:
        tuning=kwargs.get('sim_filter',args[1] if len(args)>1 else None)
        filter_guid=guid_for_filter(tuning)
        choice,newargs,newkwargs=_SESSION.decide(
            mode,filter_guid,args,kwargs,_BASE_TUNING,
            slot=current_slot(allow_travel=True),day=_day(),zone=_zone(),
            bouncer=_original_bouncer_origin(),
            school=_school_schedule_verified())
    except Exception as exc:
        _LAST={'status':'EA_CALL_CONTEXT_UNVERIFIED',
               'error_type':type(exc).__name__,
               'ea_request_preserved':True}
        _save()
        return _OLD_FILTER(original,service,args,kwargs,mode)
    if choice!='CONSTRAIN':
        return _OLD_FILTER(original,service,args,kwargs,mode)
    _LAST=dict(_SESSION.evidence(),status='NATIVE_REQUEST_PROPOSAL',
               note='Neither spawned Sim nor EA Job binding verified')
    _save()
    return _OLD_FILTER(original,service,newargs,newkwargs,mode)


def _install():
    global _INSTALLED,_OLD_FILTER
    if _INSTALLED:
        return True
    import mhs57_filter_runtime as m57
    import mhs105_game_controller as old105
    # Avoid stacking incompatible active high-school filters.
    if (not _m57_compatible(m57)
            or getattr(old105,'_INSTALLED',False)
            or m57._filtered is _filtered):
        return False
    _OLD_FILTER=m57._filtered
    m57._filtered=_filtered
    _INSTALLED=True
    return True


def arm():
    global _SESSION,_BASE_TUNING,_LAST
    if _SESSION is not None:
        return 'M106 gia armata; usa mhs106.off prima di riavviarla'
    try:
        result=prepare_live_roster_first()
        if result.get('status')!='ROSTER_FIRST_CANDIDATE_ONLY':
            _LAST={'status':'PREFLIGHT_BLOCKED',
                   'reason':result.get('reason','unverified'),
                   'game_unchanged':True}
            _save()
            return human_summary(result)
        home=_zone()
        if home is None or _school_schedule_verified():
            return 'M106 BLOCCATA: avvia prima da casa, non al liceo'
        filters=services.get_instance_manager(Types.SIM_FILTER)
        base=filters.get(VERIFIED_SPECS[277894][0]) if filters else None
        if base is None or guid_for_filter(base)!=280516:
            return 'M106 BLOCCATA: filtro studente EA Base non verificato'
        session=M106Session(result['plan'],result['save_slot'],_day(),home)
        if not _install():
            return 'M106 BLOCCATA: altro hook scolastico o M57 non pronto'
        _BASE_TUNING=base
        _SESSION=session
        _LAST={'status':'ARMED_SCHOOL_ONLY_CORE_BASE_EXPERIMENT',
               'save_slot':result['save_slot'],'registered':16,
               'playable':3,'core':5,'base':8,
               'bridged_core_jobs':result['school_only_bridge_count'],
               'base_schedule_count_changed':False,
               'ea_core_jobs_verified':False,'attendance_verified':False}
        _save()
        return ('M106 test attivato: iscritti 16, Core 5, Base 8. '
                '{} filtri speciali scuola adattati. '
                'Calendario EA NON aumentato, presenze NON garantite. '
                'Usa mhs106.check al liceo.').format(
                    result['school_only_bridge_count'])
    except Exception as exc:
        _LAST={'status':'ARM_ERROR','error_type':type(exc).__name__,
               'game_unchanged':True}
        _save()
        return 'M106 BLOCCATA: '+type(exc).__name__


def check():
    global _LAST
    if _SESSION is None:
        return 'M106 non armata | '+_REPORT
    evidence=_SESSION.evidence()
    try:
        same_save=str(current_slot(allow_travel=True))==_SESSION.slot
        same_day=_day()==_SESSION.day
        school=(_school_schedule_verified()
                and evidence['school_zone']==_zone()
                and _zone()!=_SESSION.home_zone)
        if same_save and same_day and school:
            from sims.sim_info_types import Age,Species
            from mhs105_live_core_binding import inspect_core_jobs
            proof=inspect_core_jobs(
                _SESSION.plan,services.sim_info_manager().get_all(),
                services.get_zone_situation_manager(),
                Age.TEEN,Species.HUMAN,
                school_verified=True,save_verified=True,day_verified=True)
        else:
            proof={'status':'UNKNOWN','reason':'school/save/day not verified',
                   'actual_ea_core_binding_verified':False}
    except Exception as exc:
        proof={'status':'UNKNOWN','reason':'EA role read failed',
               'error_type':type(exc).__name__,
               'actual_ea_core_binding_verified':False}
    _LAST.update(evidence)
    _LAST['ea_core_roles_readonly']=proof
    _save()
    return ('M106 richieste native: Core {}/5; Base {}/8. '
            'Ruoli EA: {}. Calendario Base originale NON modificato. '
            '16 presenze NON provate | {}').format(
                evidence['core_requests_constrained'],
                evidence['base_targets_constrained'],
                proof['status'],_REPORT)


def off():
    global _SESSION,_BASE_TUNING,_LAST,_INSTALLED,_OLD_FILTER
    if _SESSION is not None:
        _SESSION.off()
    _SESSION=None
    _BASE_TUNING=None
    try:
        import mhs57_filter_runtime as m57
        if _INSTALLED and m57._filtered is _filtered:
            m57._filtered=_OLD_FILTER
            _INSTALLED=False
            _OLD_FILTER=None
    except Exception:
        pass
    _LAST={'status':'OFF','ea_requests_restored':True}
    _save()
    return 'M106 disattivata; filtro EA originale ripristinato'


@sims4.commands.Command('mhs106.arm',
                        command_type=sims4.commands.CommandType.Live)
def _arm_command(_connection=None):
    sims4.commands.output(arm(),_connection)


@sims4.commands.Command('mhs106.check',
                        command_type=sims4.commands.CommandType.Live)
def _check_command(_connection=None):
    sims4.commands.output(check(),_connection)


@sims4.commands.Command('mhs106.off',
                        command_type=sims4.commands.CommandType.Live)
def _off_command(_connection=None):
    sims4.commands.output(off(),_connection)
