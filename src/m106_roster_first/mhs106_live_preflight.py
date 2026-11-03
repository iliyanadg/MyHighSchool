"""M106 roster-first live preflight. No EA mutations; no install side effects.

Use the exact same per-save 2x8 register, three active playable teens,
five manually selected role preferences, and SIX scored EA SimFilters as
M105, but do not require the original Core SimFilters to accept all five
choices. This is the step that precedes a separate school-only runtime
adapter; it cannot itself put sixteen students on the school lot.
"""
from mhs105_live_preflight import _base_data, _query_ea_filters
from mhs106_roster_first_policy import propose_roster_first


def prepare_live_roster_first():
    """Read actual EA eligibility and compute immutable candidate for 16."""
    try:
        original=_base_data()
        if original.get('status')!='LOCAL_REGISTRY_VERIFIED':
            return {
                'status':'BLOCKED',
                'reason':original.get('reason','MHS registry unavailable'),
                'game_modified':False,
                'ea_role_binding_verified':False,
            }
        groups=original['classes']
        played=original['playable']
        registered=groups[0]+groups[1]
        ordinary=tuple(int(sid) for sid in registered if sid not in played)
        if len(ordinary)!=13:
            return {'status':'BLOCKED',
                    'reason':'exactly thirteen registered NPCs required',
                    'game_modified':False}
        eligible,details=_query_ea_filters(ordinary)
        if eligible is None:
            return {'status':'BLOCKED',
                    'reason':'EA SimFilter eligibility unavailable',
                    'filter_details':details,
                    'game_modified':False}
        plan=propose_roster_first(
            groups,played,eligible,original['assigned_roles'])
        if plan.get('status')!='BRIDGE_CANDIDATE_ONLY_NOT_EA_BOUND':
            return {'status':'BLOCKED','reason':plan.get('reason','no plan'),
                    'filter_details':details,
                    'game_modified':False}
        # The optimizer may find a valid EA partition by silently moving
        # a user-selected Core role holder. The live pilot must NOT do this.
        manual_roles=original.get('assigned_roles')
        proposed_roles=plan.get('core_role_assignments')
        if (not isinstance(manual_roles,dict)
                or len(manual_roles)!=5
                or not isinstance(proposed_roles,(tuple,list))
                or len(proposed_roles)!=5
                or any(job not in manual_roles
                       or str(manual_roles[job])!=sid
                       for job,sid in proposed_roles)):
            return {'status':'BLOCKED',
                    'reason':'manual EA Core role assignments would change',
                    'filter_details':details,
                    'manual_roles_preserved':False,
                    'game_modified':False,
                    'attendance_verified':False}
        # A successful PLAN is not a release condition or authorization
        # to replace EA Core job filters. No modified Sims or role bindings.
        return {'status':'ROSTER_FIRST_CANDIDATE_ONLY',
                'save_slot':original['save_slot'],
                'plan':plan,'filter_details':details,
                'school_only_bridge_count':plan['school_only_bridge_count'],
                'manual_roles_preserved':True,
                'game_modified':False,
                'ea_filters_modified':False,
                'core_jobs_reserved':False,
                'ea_role_binding_verified':False,
                'base_count_overridden':False,
                'lot_capacity_verified':False,
                'attendance_verified':False}
    except Exception as exc:
        return {'status':'BLOCKED','reason':'M106 preflight exception',
                'error_type':type(exc).__name__,
                'game_modified':False}


def human_summary(result):
    """Make the state explicit; never claim an EA school success."""
    if not isinstance(result,dict):
        return 'M106 piano non verificabile'
    if result.get('status')!='ROSTER_FIRST_CANDIDATE_ONLY':
        return 'M106 BLOCCATA: '+str(result.get('reason','unknown'))
    plan=result['plan']
    pairs=plan['school_only_bridge_candidates']
    core=len(plan['core_role_assignments'])
    base=len(plan['normal_base_ids'])
    return ('M106 piano con 16 iscritti invariati: 3 giocabili + {} Core + '
            '{} Base; {} proposte filtro Core scuola. Nessuna convocazione '
            'modificata; 16 presenze NON verificate').format(
                core,base,len(pairs))
