"""M101: eligibility/provenance gate for ONE ORIGINAL EA high-school Base slot.

No game imports. The same original WeeklyScheduleDay call must be used,
with its original spin-up flags. Neither a late extra EA situation (M61)
nor an unknown call site is eligible for replacement.
"""
BASE=277733
FILTER=280516
EA_SCHEDULER='weekly_schedule_zone_director'

def original_school_call(situation_guid, guests, options, caller_modules):
    if situation_guid!=BASE:
        return False
    if guests is None or tuple(guests):
        return False
    if not isinstance(options,dict):
        return False
    if options.get('spawn_sims_during_zone_spin_up') is not True:
        return False
    if options.get('user_facing') is not False:
        return False
    if 'duration_override' not in options:
        return False
    if not isinstance(options.get('creation_source'),str):
        return False
    if (not isinstance(caller_modules,(tuple,list))
            or EA_SCHEDULER not in caller_modules):
        return False
    return True

def validated_filter_ids(results, constrained_ids):
    """Extract *only actual EA submit_filter result members* from this query.

    None, deferred results, unexpected shapes, wrong IDs, and raw unscored
    SimInfos are NOT a proof of filter eligibility. Fail closed.
    """
    if not isinstance(constrained_ids,(tuple,list)) or not constrained_ids:
        return ()
    try:
        expected=set()
        for x in constrained_ids:
            if type(x) not in (str,int) or not str(x).isdigit() or int(x)<=0:
                return ()
            expected.add(int(x))
        if results is None or not isinstance(results,(tuple,list)):
            return ()
        ids=[]
        for result in results:
            info=getattr(result,'sim_info',None)
            score=getattr(result,'score',None)
            sid=getattr(info,'sim_id',None)
            if type(sid) is not int or sid not in expected:
                continue
            if isinstance(score,bool) or not isinstance(score,(int,float)) or score<=0:
                continue
            if sid not in ids:
                ids.append(sid)
        return tuple(ids)
    except Exception:
        return ()
