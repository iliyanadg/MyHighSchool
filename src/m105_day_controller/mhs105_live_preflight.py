"""M105: live-game school-day preflight BEFORE zone travel, no EA override.

This module is NOT automatically installed and DOES NOT change the game.
It loads this save's 2x8 enrollment + five manually selected core roles,
evaluates all six real EA SimFilters synchronously for existing 13 NPCs,
and prepares a single immutable 3+5+8 plan for later atomic install.

It must run from the home lot before EA school zone spin-up. A completed
preflight is NOT evidence that any of the five roles is bound in EA.
"""
import os
from itertools import combinations
import services
from sims.sim_info_types import Age,Species
from sims4.resources import Types
from mhs_m2_game_bridge import current_slot
from mhs_m2_store import RosterStore
from mhs34_settings import SettingsStore
from mhs97_core_role_store import CoreRoleStore,ROLE_TO_JOB
from mhs93_verified_jobs import VERIFIED_SPECS
from mhs101_original_slot_gate import validated_filter_ids
from mhs105_atomic_school_roster import plan_school_day,ALL_JOBS,CORE_JOBS,BASE_JOB

_FOLDER=os.path.join(os.path.expanduser('~'),'Documents',
                     'Electronic Arts','The Sims 4',
                     'MY_HIGH_SCHOOL_M25_TEST_DATA')
_ROSTER=RosterStore(_FOLDER)
_SETTINGS=SettingsStore(_FOLDER)
_ROLES=CoreRoleStore(_FOLDER)

def _result(status,reason='',**data):
    response={'status':status,'reason':reason,
              'ea_overrides_installed':False,
              'ea_school_roles_bound':False,
              'students_spawned':False}
    response.update(data)
    return response

def _teen(info):
    return (info is not None and
            getattr(info,'age',None)==Age.TEEN and
            getattr(info,'species',None)==Species.HUMAN)

def _base_data():
    slot=str(current_slot(allow_travel=True))
    settings=_SETTINGS.load(slot)
    if not settings.active or settings.class_count!=2:
        return _result('BLOCKED','activate two MHS classes first')
    roster=_ROSTER.load(slot)
    groups=tuple(tuple(str(sid) for sid in roster.class_members(i))
                 for i in (1,2))
    if any(len(group)!=8 for group in groups):
        return _result('BLOCKED','exactly eight enrolled per class')
    everyone=groups[0]+groups[1]
    if len(set(everyone))!=16:
        return _result('BLOCKED','duplicate enrollment')
    manager=services.sim_info_manager()
    if manager is None:
        return _result('BLOCKED','SimInfoManager unavailable')
    if any(not _teen(manager.get(int(sid))) for sid in everyone):
        return _result('BLOCKED','one registered student not a human teen')
    household=services.active_household()
    if household is None:
        return _result('BLOCKED','no active household')
    playables=tuple(str(s.sim_id) for s in household.sim_info_gen()
                    if _teen(s))
    if len(playables)!=3 or not set(playables)<=set(everyone):
        return _result('BLOCKED','need the three enrolled household teens')
    chosen=_ROLES.load(slot)
    if not chosen.complete or len(chosen.chosen())!=5:
        return _result('BLOCKED','five manual core roles not yet assigned')
    return _result('LOCAL_REGISTRY_VERIFIED',save_slot=slot,
                   classes=groups,playable=playables,
                   assigned_roles=chosen.chosen())

def _query_ea_filters(ordinary):
    """Explicitly inspect ALL six job filters without requesting a Sim spawn.

    API return values must be real, scored SimFilterResult instances; the
    same callback=None was verified in the previous Mac M101d test.
    Any exception or missing job is a fail-closed preflight blocker.
    """
    mgr=services.get_instance_manager(Types.SIM_FILTER)
    service=services.sim_filter_service()
    if mgr is None or service is None:
        return None,{'reason':'filter manager or EA service unavailable'}
    result={}
    calls={}
    for job in ALL_JOBS:
        filter_guid=VERIFIED_SPECS[job][0]
        tuned=mgr.get(filter_guid)
        if tuned is None:
            return None,{'reason':'EA filter tuning missing',
                         'job_id':job,'filter_guid':filter_guid}
        try:
            data=service.submit_filter(
                callback=None,sim_filter=tuned,
                sim_constraints=ordinary,allow_yielding=False)
        except Exception as exc:
            return None,{'reason':'EA filter query failed',
                         'job_id':job,'filter_guid':filter_guid,
                         'error_type':type(exc).__name__,
                         'error_message':' '.join(str(exc).split())[:180]}
        if not isinstance(data,(tuple,list)):
            return None,{'reason':'EA filter returned unverified data',
                         'job_id':job,'result_type':type(data).__name__}
        eligible=validated_filter_ids(data,ordinary)
        # A nonempty raw result with zero validated scored Sims is
        # ambiguous. Never silently treat it as a negative eligibility
        # signal for every registered student.
        if data and not eligible:
            return None,{'reason':'EA results lack verifiable scored IDs',
                         'job_id':job,'raw_count':len(data)}
        result[job]=tuple(str(sid) for sid in eligible)
        calls[str(job)]={'filter_guid':filter_guid,
                         'verified_eligible_count':len(eligible)}
    return result,{'calls':calls}

def prepare_live_school_day():
    """Pure preflight. DO NOT install EA hooks or start any situation."""
    try:
        local=_base_data()
        if local['status']!='LOCAL_REGISTRY_VERIFIED':
            return local
        classes=local['classes']
        playable=local['playable']
        everyone=classes[0]+classes[1]
        ordinary=tuple(int(sid) for sid in everyone if sid not in playable)
        if len(ordinary)!=13:
            return _result('BLOCKED','13 enrolled nonplayable expected')
        # No generated NPC candidate, no late school invitation.
        eligible,details=_query_ea_filters(ordinary)
        if eligible is None:
            return _result('BLOCKED','one EA filter could not be verified',
                           filter_details=details)
        plan=plan_school_day(classes,playable,eligible,
                             confirmed_core_assignments=local['assigned_roles'])
        if plan['status']!='PREPARED_NOT_EA_BOUND':
            return _result('BLOCKED','whole-day role allocation invalid',
                           plan_reason=plan.get('reason','unspecified'),
                           filter_details=details)
        return _result('PREFLIGHT_READY_NOT_EA_BOUND',
                       save_slot=local['save_slot'],plan=plan,
                       filter_details=details,
                       install_requires_verified_school_context=True,
                       school_capacity_not_yet_verified=True)
    except Exception as exc:
        return _result('BLOCKED','preflight raised error',
                       error_type=type(exc).__name__,
                       error_message=' '.join(str(exc).split())[:180])


# Real EA SimFilter eligibility is separate from the tentative M98 menu.
# Read all six filters ONCE, and do not silently change the player's choices.
_DIAGNOSTIC_ROLE_NAMES=(
    (278965,'Cheerleader'),(278966,'Scacchi'),(278967,'Football'),
    (278968,'Informatica'),(303765,'Sim perfido'))

def diagnose_live_role_choices():
    """Show exact EA-eligible enrolled NPCs and a coordinated manual proposal.

    Never writes the role registry, changes situations or makes EA spawn Sims.
    Preserve as many EA-eligible existing manual appointments as possible,
    while respecting all five real job filters AND the eight Base vacancies.
    """
    local=_base_data()
    if local['status']!='LOCAL_REGISTRY_VERIFIED':
        return ("M105 IDONEITA': "+local.get('reason','registro non valido'),)
    classes=local['classes']
    playables=set(local['playable'])
    everyone=classes[0]+classes[1]
    ordinary=tuple(int(sid) for sid in everyone if sid not in playables)
    eligible,details=_query_ea_filters(ordinary)
    if eligible is None:
        return ("M105 FILTRI EA NON LEGGIBILI: "+
                details.get('reason','errore sconosciuto'),)
    chosen=local['assigned_roles']
    manager=services.sim_info_manager()
    def label(sid):
        info=manager.get(int(sid))
        if info is None:
            return 'ID '+str(sid)
        full='{} {}'.format(getattr(info,'first_name',''),
                            getattr(info,'last_name','')).strip()
        return full or ('ID '+str(sid))
    rows=["M105 IDONEITA' EA (sola lettura): nessun ruolo modificato"]
    for job,name in _DIAGNOSTIC_ROLE_NAMES:
        assigned=chosen.get(job)
        matches=tuple(str(sid) for sid in ordinary
                      if str(sid) in set(eligible[job]))
        match_list=', '.join(label(sid) for sid in matches) or 'NESSUNO'
        state='OK' if assigned in matches else 'NON IDONEO'
        rows.append('{}: {} {}. Idonei: {}'.format(
            name,label(assigned) if assigned else 'Nessuno',
            state,match_list))
    base=set(eligible[BASE_JOB])
    rows.append('Studenti Base EA idonei: {}/13 (servono 8)'.format(
        sum(str(sid) in base for sid in ordinary)))
    valid_pins=tuple(job for job in CORE_JOBS
                     if chosen.get(job) in set(eligible[job]))
    proposal=None
    # At most 32 subsets: keep the greatest number of existing roles.
    # Each trial verifies the entire class/NPC/Base allocation jointly.
    if sum(str(sid) in base for sid in ordinary)>=8:
        for retained_count in range(len(valid_pins),-1,-1):
            for kept in combinations(valid_pins,retained_count):
                pins={job:chosen[job] for job in kept}
                test=plan_school_day(
                    classes,local['playable'],eligible,
                    confirmed_core_assignments=pins,
                    propose_missing_roles=True)
                if test['status'] in (
                        'PREPARED_NOT_EA_BOUND',
                        'PROPOSAL_NEEDS_MANUAL_CONFIRMATION'):
                    proposal=dict(test['core_role_assignments'])
                    break
            if proposal is not None:
                break
    if proposal is None:
        rows.append('NESSUN piano 5 Core + 8 Base trovato per gli iscritti.')
        rows.append('Non cambiare ruoli a caso: rivedere gli iscritti/idoneita EA.')
    else:
        changed=tuple((name,proposal[job])
                      for job,name in _DIAGNOSTIC_ROLE_NAMES
                      if chosen.get(job)!=proposal[job])
        if changed:
            rows.append('PROPOSTA (non salvata, da confermare nel menu):')
            rows.extend('{} -> {}'.format(name,label(sid))
                        for name,sid in changed)
            rows.append('Rimuovi prima i ruoli da cambiare; poi riassegna.')
        else:
            rows.append('Tutti i 5 Core e gli 8 Base risultano compatibili.')
    return tuple(rows)
