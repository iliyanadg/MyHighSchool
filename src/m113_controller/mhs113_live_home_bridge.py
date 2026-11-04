"""M113 real MHS home save/roster/Core-role snapshot (read-only).

Uses M105's already implemented live _base_data() to read M2/M34
enrollment/settings and M97 manual Core appointments, plus exact EA
save/day/home zone. Does not call hooks, create situations, alter filters,
save files or write MHS registry. NO live school controller entry point.
"""
from mhs113_early_school_entry import _home_plan


def prepare_live_home_snapshot():
    """Read one real home school-day plan, fail closed if any field changes."""
    result={
        'kind':'M113_REAL_HOME_MANIFEST_READ_ONLY',
        'status':'HOME_PREFLIGHT_BLOCKED',
        'reason':'UNKNOWN',
        'hooks_installed':False,
        'game_modified':False,
        'live_school_ea_stage_graph_connected':False,
        'exact_16_attendance_verified':False,
    }
    try:
        import services
        from date_and_time import sim_ticks_per_day
        from mhs_m2_game_bridge import current_slot
        from mhs105_live_preflight import _base_data
        zone=services.current_zone()
        home=getattr(zone,'id',None)
        if type(home) is not int or home<=0:
            result['reason']='CURRENT_HOME_ZONE_UNAVAILABLE'
            return result
        venue=services.venue_service()
        if venue is None:
            result['reason']='VENUE_SERVICE_UNAVAILABLE'
            return result
        director=venue.get_zone_director()
        schedule=getattr(director,'_schedule',None)
        if getattr(schedule,'guid64',None) in (277657,279958):
            result['reason']='MUST_START_FROM_HOME_NOT_SCHOOL'
            return result
        slot=str(current_slot(allow_travel=False))
        clock=services.time_service()
        ticks=clock.sim_now.absolute_ticks()
        day_ticks=sim_ticks_per_day()
        if (type(ticks) is not int or
                type(day_ticks) is not int or day_ticks<=0 or ticks<0):
            result['reason']='EA_SIM_DAY_UNAVAILABLE'
            return result
        day=ticks//day_ticks
        local=_base_data()
        if (local.get('status')!='LOCAL_REGISTRY_VERIFIED'
                or local.get('save_slot')!=slot):
            result['reason']=local.get('reason','MHS_ROSTER_OR_CORE_ROLES_UNAVAILABLE')
            return result
        plan=_home_plan(
            local['classes'],local['playable'],
            local['assigned_roles'],slot,day,home)
        if plan is None:
            result['reason']='INVALID_EXACT_3_PLAYABLE_5_CORE_8_BASE'
            return result
        result.update(
            status='HOME_PLAN_READY_NOT_GAME_AUTHORIZED',
            reason='',
            # This is runtime data only, NOT written to GitHub or disk.
            plan=plan,
            selected_students=16,
            selected_playable=3,
            selected_core=5,
            selected_base=8,
            early_ea_school_callback_observed=False,
            native_bouncer_jobs_verified=False,
        )
        return result
    except Exception as exc:
        result['reason']='HOME_READ_EXCEPTION_'+type(exc).__name__
        return result
