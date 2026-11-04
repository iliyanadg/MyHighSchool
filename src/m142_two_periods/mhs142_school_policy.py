"""M142 school periods, bounded playable class retry, passive NPC lunch audit.

Policy is intentionally independent of Sims 4 runtime and is testable offline.
No household meal automation; no NPC rerouting or interaction cancellation.
"""
SITUATION_JOB = {1: ((304565, 277919), (304703, 277919)),
                 2: ((304567, 280777),)}
PROTECTED_PARTS = (
    'HighSchool_Active_Whiteboard_Attend',
    'HighSchool_Active_Whiteboard_Class_Start',
    'HighSchool_Active_UseBook_Class',
    'HighSchool_Active_CreateBook_Class',
    'HighSchool_Active_WriteOnBook',
    'HighSchool_Active_Listen_',
    'toilet',
    'Toilet',
    'Shower',
    'Sleep',
)


def minute_of_day(clock):
    if not isinstance(clock, dict):
        return None
    hour, minute = clock.get('hour'), clock.get('minute')
    if type(hour) is not int or type(minute) is not int:
        return None
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        return None
    return 60 * hour + minute


def period_for_clock(clock):
    m = minute_of_day(clock)
    if m is None:
        return None
    if 9*60+25 <= m < 11*60:
        return 'morning'
    if 13*60+25 <= m < 15*60:
        return 'afternoon'
    return None


def can_roll_to_afternoon(clock, situation_guid, prep_guids, already_rolled):
    m = minute_of_day(clock)
    return (not already_rolled and m is not None
            and 13*60+25 <= m < 14*60
            and (situation_guid is None or situation_guid in prep_guids))


def class_retry_decision(clock, current_period, row, player_job,
                         initial_requested, already_retried,
                         running_action):
    """Allow one second *request* per player per actual lesson period.

    A job check prevents pushing an arbitrary Sim just because a timer fired.
    Merely accepting a push is not proof it actually ran or completed.
    """
    m = minute_of_day(clock)
    klass = row.get('registered_class') if isinstance(row, dict) else None
    sid = str(row.get('sim_id')) if isinstance(row, dict) else 'None'
    if klass not in (1, 2) or sid == 'None':
        return False, 'UNENROLLED_OR_INVALID'
    if not initial_requested:
        return False, 'NATIVE_CREATE_NOT_CONFIRMED'
    if already_retried:
        return False, 'RETRY_ALREADY_USED'
    if current_period == 'morning':
        start, end = 10*60+4, 10*60+15
    elif current_period == 'afternoon':
        start, end = 14*60+4, 14*60+15
    else:
        return False, 'UNKNOWN_SCHOOL_PERIOD'
    if m is None or not start <= m <= end:
        return False, 'OUTSIDE_CLASS_START_WINDOW'
    role_pairs = {(r.get('situation_guid'), r.get('job_guid'))
                  for r in (player_job or {}).get('situation_jobs',())
                  if isinstance(r,dict)}
    if not role_pairs.intersection(SITUATION_JOB[klass]):
        return False, 'NATIVE_CLASS_JOB_MISSING'
    if running_action and any(marker in str(running_action)
                              for marker in PROTECTED_PARTS):
        return False, 'EXISTING_CLASS_OR_PROTECTED_ACTION'
    return True, 'RETRY_ALLOWED_AFTER_NATIVE_ROLE'


def summarize_npc_lunch(samples, class_ids, sample_minutes=3):
    """Observe food queue congestion from sampled actions, never modify NPCs.

    Counts represent samples; an action observed on successive samples is not
    proof that an order never finished between the samples.
    """
    registered = set(str(i) for i in class_ids)
    per_sim = {}
    for sample in samples:
        m = minute_of_day(sample.get('clock'))
        if m is None or not 11*60 <= m < 14*60:
            continue
        for row in sample.get('students',()):
            sid = str(row.get('sim_id'))
            if sid not in registered or row.get('selectable') is not False:
                continue
            state = per_sim.setdefault(sid,{
                'order_samples':0,'eat_samples':0,
                'longest_contiguous_order_samples':0,
                'last_order_target':None,'streak':0,
                'first_order_time':None,'last_order_time':None,
                'food_eaten_observed':False})
            name = str(row.get('running_action') or '')
            ordering = ('si_MarketStalls_OrderFood' in name or
                        'HighSchool_Active_NPC_Lunch_CreateFood' in name)
            eating = ('Food_Eat' in name or
                      'eat_to_clean_from_sit' in name or
                      'generic_consume_food' in name)
            if ordering:
                state['order_samples'] += 1
                key = (name, str(row.get('action_target_id')))
                if key == state['last_order_target']:
                    state['streak'] += 1
                else:
                    state['streak'] = 1
                state['last_order_target'] = key
                state['longest_contiguous_order_samples'] = max(
                    state['longest_contiguous_order_samples'],state['streak'])
                stamp = sample.get('clock',{}).get('repr')
                state['first_order_time'] = state['first_order_time'] or stamp
                state['last_order_time'] = stamp
            else:
                state['last_order_target'] = None
                state['streak'] = 0
            if eating:
                state['eat_samples'] += 1
                state['food_eaten_observed'] = True
    for state in per_sim.values():
        state.pop('last_order_target',None)
        state.pop('streak',None)
        state['longest_sampled_order_minutes_estimate'] = (
            state['longest_contiguous_order_samples'] * sample_minutes)
    return {
        'kind':'M142_PASSIVE_NPC_LUNCH_ORDERING_OBSERVATIONS',
        'npc_students_in_trace':len(per_sim),
        'students_with_ordering_samples':sum(
            bool(x['order_samples']) for x in per_sim.values()),
        'students_with_eating_samples':sum(
            x['food_eaten_observed'] for x in per_sim.values()),
        'students':per_sim,
        'sample_period_minutes':sample_minutes,
        'estimates_not_proof_of_queue_block_or_food_consumption':True,
        'game_mutations':0,
        'playable_lunch_never_automated':True}
