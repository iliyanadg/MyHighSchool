"""Explicit EA schedule capacities for existing school cafeteria counters.

Only adjusts the *count* of the original High School Years cafeteria
TendObjectSituation during the school's original schedule evaluation.
Never spawns independent ad-hoc jobs, assigns random Sims, or changes
the time of lunch. EA remains responsible for assigning one distinct
station per situation. More than one station must be discovered on-lot.
"""
CAFETERIA_SITUATION=278011


def cafeteria_native_schedule_count(original, workers, stations):
    """Return (count_tuple, reason), changing only a known EA one-slot tuple.

    If the live EA situation schedule reports other cardinalities, if the
    object manager has not verified capacity, or if the worker roster is
    missing, preserve the original unchanged. No proof of actual spawning.
    """
    if (type(original) is not tuple or len(original)!=2 or
            any(type(v) is not int for v in original) or
            original!=(1,1)):
        return original,'EA_VENDOR_COUNT_UNSUPPORTED'
    if (type(workers) not in (list,tuple) or not 2<=len(workers)<=3 or
            any(type(sid) is not str or not sid.isdigit() or
                not int(sid) for sid in workers) or
            len(set(workers))!=len(workers)):
        return original,'NO_VALID_MULTI_VENDOR_APPOINTMENTS'
    if type(stations) is not int or stations < len(workers):
        return original,'ADDITIONAL_CAFETERIA_STATION_REQUIRED'
    return (len(workers),len(workers)),'NATIVE_EA_SCHEDULE_VENDOR_COUNT_ADJUSTED'
