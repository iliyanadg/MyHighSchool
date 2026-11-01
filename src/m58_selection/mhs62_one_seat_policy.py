"""M62: offline-only policy for ONE roster pupil in an EA-owned base seat.

No live hooks or EA imports. This determines whether an already-created
school situation has a genuinely unassigned Base Student job that can be
considered for a single registered candidate. It does not guarantee the
student can assume that EA job, enter the lot, or sit at a desk.
"""
from mhs58_guest_policy import guest_list_decision


def _valid_ids(values):
    if values is None:
        return None
    try:
        seq = tuple(values)
    except TypeError:
        return None
    ids = []
    for raw in seq:
        if isinstance(raw, bool) or not isinstance(raw, (str, int)):
            return None
        sid = str(raw)
        if not sid.isdigit() or int(sid) < 1 or str(int(sid)) != sid:
            return None
        ids.append(sid)
    return tuple(ids) if len(set(ids)) == len(ids) else None


def plan_one_registered_base_guest(situation_guid, job_guests,
                                   ordered_registered_ids, verified_eligible_ids,
                                   present_ids=(), occupied_role_ids=(),
                                   playable_ids=(), verified_school_zone=False,
                                   active=False):
    """Return a candidate, never modify EA data.

    Caller must supply eligibility verified for the *actual* EA school job,
    not just human teen age. All identities must be from the same checked
    save/zone. Missing or inconsistent evidence means preserve vanilla EA.
    EA explicit guests, core jobs, venue/staff, duplicate/occupied Sim IDs,
    and unverified school zones are never overridden.

    The caller must reserve a chosen ID before consulting this planner for
    another seat; this pure function does not keep its own reservation state.
    """
    preserve = lambda why: {'action': 'preserve', 'reason': why}
    if not verified_school_zone or not active:
        return preserve('not verified active school')
    roster = _valid_ids(ordered_registered_ids)
    eligible = _valid_ids(verified_eligible_ids)
    present = _valid_ids(present_ids)
    occupied = _valid_ids(occupied_role_ids)
    playable = _valid_ids(playable_ids)
    if any(v is None for v in (roster, eligible, present, occupied, playable)):
        return preserve('missing or invalid verified Sim IDs')
    if not roster or not eligible:
        return preserve('no verified candidate')
    if not set(eligible).issubset(roster):
        return preserve('eligibility outside registered roster')
    if set(playable) & set(eligible):
        return preserve('playable erroneously marked eligible for NPC job')
    if set(occupied) & set(eligible):
        # A Sim already committed to a core/phase job is never a base invite.
        eligible = tuple(sid for sid in eligible if sid not in occupied)
    excluded = set(present) | set(occupied) | set(playable)
    candidates = tuple(sid for sid in roster
                       if sid in eligible and sid not in excluded)
    if not candidates:
        return preserve('no free verified registered candidate')
    # Keep the existing M58 one-vacancy, no-overwrite guest policy intact.
    decision = guest_list_decision(
        situation_guid, job_guests, candidates[:1],
        verified_school_zone=True, active=True)
    if decision['action'] != 'candidate':
        return preserve('EA guest decision: ' + decision['reason'])
    return {'action': 'candidate', 'candidate_id': candidates[0],
            'kind': 'plan-only', 'requested_count': 1}
