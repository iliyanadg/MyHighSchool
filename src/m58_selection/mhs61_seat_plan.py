"""M61: fail-closed EA Base Student seat planning, pure Python 3.7.

No game hooks, invitations, Sim spawning, or tuning alterations. Supports an
incremental transition to per-seat EA job assignment only after observation
of the correct actual runtime method and candidate eligibility.
"""
BASE_SITUATION=277733
BASE_JOB=277894

def plan_seats(enrolled_ids, physical_ids, playable_ids=(), occupied_ids=(),
               seat_count=6):
    """Return deterministic candidates for vacant Base Student seats.

    physical_ids may include Sims from any role; playable and occupied Sims
    may not be assigned again. Never fill vacant positions with random NPCs.
    A seat_count is a cap, NOT a promise that EA accepts this many Sims.
    """
    if isinstance(seat_count,bool) or not isinstance(seat_count,int) or not 0<=seat_count<=6:
        raise ValueError('unverified number of Base Student positions')
    ids=tuple(str(v) for v in enrolled_ids)
    if len(ids)!=len(set(ids)) or any(not x.isdigit() or int(x)<=0 or str(int(x))!=x for x in ids):
        raise ValueError('invalid or duplicated enrolled Sim IDs')
    excluded=set(str(x) for group in (physical_ids,playable_ids,occupied_ids) for x in group)
    remaining=tuple(x for x in ids if x not in excluded)
    return {'candidates':remaining[:seat_count],
            'not_yet_assigned':remaining[seat_count:],
            'already_handled':len(ids)-len(remaining),
            'capacity':seat_count,
            'mode':'PLAN_ONLY_NO_EA_MUTATION'}
