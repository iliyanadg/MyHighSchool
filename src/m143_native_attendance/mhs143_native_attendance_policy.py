"""M143 observed native whiteboard Attend rescue, purely conservative policy.

EA gameplay interaction is never invented: choose the CURRENT actual tuned
interaction visibly running on a registered Class 1 playable Sim, for the
current school hour, and test it against the Class 2 whiteboard and teen.
No forced routing, teleport, placement, job changes, NPC pushes or test bypass.
"""
CLASS_ACTION = 'super_HighSchool_Active_Whiteboard_Attend_'
CLASS_ACTION_ALLOWED = (
    'super_HighSchool_Active_Whiteboard_Attend_',
    'super_HighSchool_Active_UseBook_Class',
    'mixer_HighSchool_Active_Listen_',
    'mixer_HighSchool_Active_WriteOnBook',
)
NEEDS_PROTECTED = ('toilet','Toilet','Sleep','Shower','sickness','Pregnancy')


def short_type(obj):
    if obj is None:
        return ''
    cls = type(obj)
    return str(getattr(cls,'__name__',''))


def classroom_activity(name):
    name = str(name or '')
    return any(token in name for token in CLASS_ACTION_ALLOWED)


def allowed_direct_attend(clock, klass, sid, exact_job, initially_accepted,
                          already_direct, action_name, target_class):
    if klass not in (1,2) or not sid:
        return False,'NOT_REGISTERED_TEEN'
    if target_class!=klass:
        return False,'WRONG_CLASS_TARGET_REFUSED'
    hour,minute = clock.get('hour'), clock.get('minute')
    if type(hour) is not int or type(minute) is not int:
        return False,'CLOCK_UNAVAILABLE'
    if not ((hour==10 or hour==14) and 7 <= minute <= 24):
        return False,'NOT_CURRENT_LESSON_RECOVERY_WINDOW'
    if not exact_job:
        return False,'EA_NATIVE_JOB_NOT_PRESENT'
    if not initially_accepted:
        return False,'NO_NATIVE_CLASS_START_REQUEST'
    if already_direct:
        return False,'ONE_DIRECT_ATTEMPT_PER_LESSON'
    if classroom_activity(action_name):
        return False,'ALREADY_ATTENDING_CLASS'
    if any(token in str(action_name or '') for token in NEEDS_PROTECTED):
        return False,'PROTECTED_ACTION'
    return True,'ELIGIBLE_FOR_NATIVE_EA_ATTEND_TEST'


def find_observed_attend(played):
    """Same-day affordance from a running real EA class action, no guessed IDs.

    These are instances from find_playable_entry, not names from player input.
    Ambiguous distinct subjects are rejected.
    """
    matches={}
    for row in played:
        try:
            sim = row['sim_info'].get_sim_instance()
            running = getattr(getattr(sim,'queue',None),'running',None)
            actual = type(running)
            name = getattr(actual,'__name__','')
            if CLASS_ACTION not in name:
                continue
            guid = getattr(actual,'guid64',None)
            if type(guid) is not int or guid<=0:
                continue
            if not callable(getattr(actual,'test',None)):
                continue
            matches[guid]=actual
        except Exception:
            continue
    if len(matches)!=1:
        return None,'NO_UNAMBIGUOUS_OBSERVED_NATIVE_ATTEND'
    affordance=next(iter(matches.values()))
    return affordance,'OBSERVED_ACTUAL_EA_CLASS_AFFORDANCE'


def job_matches_class(registered_class,job_rows):
    expected={1:{(304565,277919),(304703,277919)},
              2:{(304567,280777)}}
    if registered_class not in expected:
        return False
    return any(
        (r.get('situation_guid'),r.get('job_guid'))
        in expected[registered_class] for r in job_rows or ()
        if isinstance(r,dict))


def analyze_npc_dining(samples, student_ids):
    """Read-only distribution of actual running eat actions and posture.

    This does not count an action queued as consumed food. Likewise an action
    observed at the counter is not proof the cafeteria routing is broken.
    """
    ids=set(str(s) for s in student_ids)
    records={sid:dict(eating_samples=0,sitting_eating_samples=0,
                      standing_eating_samples=0,ordering_samples=0,
                      eating_positions=[],ordered_service_targets=[])
             for sid in ids}
    for snapshot in samples:
        clock=snapshot.get('clock') or {}
        h=clock.get('hour')
        if type(h) is not int or not (11 <= h < 14):
            continue
        for row in snapshot.get('students') or ():
            sid=str(row.get('sim_id'))
            if sid not in ids or row.get('selectable') is not False:
                continue
            rec=records[sid]
            action=str(row.get('running_action') or '')
            eating=('Food_Eat' in action or 'generic_consume_food' in action
                    or 'eat_to_clean_from_sit' in action)
            ordering=('si_MarketStalls_OrderFood' in action or
                      'HighSchool_Active_NPC_Lunch_CreateFood' in action)
            sitting=('posture_Sit' in str(row.get('posture') or ''))
            if eating:
                rec['eating_samples']+=1
                rec['sitting_eating_samples' if sitting
                    else 'standing_eating_samples']+=1
                if len(rec['eating_positions'])<3:
                    rec['eating_positions'].append(row.get('position'))
            if ordering:
                rec['ordering_samples']+=1
                target=row.get('action_target_id')
                if target is not None and target not in rec['ordered_service_targets']:
                    if len(rec['ordered_service_targets'])<4:
                        rec['ordered_service_targets'].append(target)
    return {
      'kind':'M143_PASSIVE_LUNCH_EATING_POSTURE_AUDIT',
      'registered_npc_count':len(records),
      'npc_with_eating_samples':sum(bool(x['eating_samples'])
                                    for x in records.values()),
      'npc_with_sitting_eating_samples':sum(
          bool(x['sitting_eating_samples']) for x in records.values()),
      'npc_with_only_standing_eating_samples':sum(
          bool(x['standing_eating_samples']) and
          not x['sitting_eating_samples'] for x in records.values()),
      'students':records,
      'no_player_meals_automated':True,
      'npc_interactions_modified':0,
      'does_not_prove_completed_order_or_consumption':True,
    }
