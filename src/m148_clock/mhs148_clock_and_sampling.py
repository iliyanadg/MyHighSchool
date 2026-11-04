"""M148: distinguish displayed game time from simulated EA timeline.

TheSims4 TimeService.sim_now may lag behind GameClock.now().
The UI school schedule counts down against game time, while native
actions and alarm callbacks need to be simulated on the server timeline.
Never fabricate completed lessons or use a calendar hour alone as proof.
No game imports here, for Python3.7 testability.
"""

SIM_TICKS_PER_MINUTE = 1500

def describe_time(value):
    if value is None:
        return None
    result={'repr':str(value)[:110]}
    for field in ('hour','minute','absolute_ticks'):
        item=getattr(value,field,None)
        try:
            item=item() if callable(item) else item
        except Exception:
            item=None
        if type(item) in (int,float):
            result[field]=item
    return result

def dual_clock_from_services(sim_time_service, game_clock_service):
    """Pure readback. Missing game clock is explicit, never invented."""
    try:
        sim_now=getattr(sim_time_service,'sim_now',None)
        if callable(sim_now):
            sim_now=sim_now()
    except Exception:
        sim_now=None
    try:
        actual=getattr(game_clock_service,'now',None)
        if callable(actual):
            actual=actual()
    except Exception:
        actual=None
    sim=describe_time(sim_now)
    game=describe_time(actual)
    gap=None
    if sim and game:
        try:
            delta=actual-sim_now
            get_minutes=getattr(delta,'in_minutes',None)
            if callable(get_minutes):
                gap=round(float(get_minutes()),2)
            else:
                a=game.get('absolute_ticks')
                b=sim.get('absolute_ticks')
                if a is not None and b is not None:
                    gap=round((a-b)/SIM_TICKS_PER_MINUTE,2)
        except Exception:
            a=game.get('absolute_ticks')
            b=sim.get('absolute_ticks')
            if a is not None and b is not None:
                gap=round((a-b)/SIM_TICKS_PER_MINUTE,2)
    state=('UNAVAILABLE' if gap is None else
           'GAME_CLOCK_BEHIND' if gap< -1 else
           'SIMULATION_MORE_THAN_HOUR_BEHIND' if gap>=60 else
           'SIMULATION_LAG_HIGH' if gap>=20 else
           'SIMULATION_LAG_MODERATE' if gap>=5 else
           'CLOCKS_ALIGNED')
    return {'game_time_displayed':game,'sim_time_processed':sim,
            'lag_minutes':gap,'state':state,
            'no_game_time_modification':True}

def read_live_clocks(services):
    try:
        sim=services.time_service()
    except Exception:
        sim=None
    try:
        game=services.game_clock_service()
    except Exception:
        game=None
    return dual_clock_from_services(sim,game)

def should_capture_sim_snapshot(now_ticks,last_ticks,forced=False,
                                min_minutes=15):
    """Limit expensive 16-Sim report snapshots to once each 15 Sim minutes.

    Events may force one snapshot, but repeated normal timer samples do not
    walk 16 Sims/3 playable EA jobs or JSON flush every three Sim minutes.
    """
    if forced:
        return True
    if type(now_ticks) not in (int,float):
        return False
    if last_ticks is None:
        return True
    return now_ticks-last_ticks>=min_minutes*SIM_TICKS_PER_MINUTE

def should_do_school_work(sim_clock):
    """Avoid setting class jobs based on UI time. Sim time is authoritative."""
    if not isinstance(sim_clock,dict):
        return False
    return type(sim_clock.get('hour'))==int and type(sim_clock.get('minute'))==int
