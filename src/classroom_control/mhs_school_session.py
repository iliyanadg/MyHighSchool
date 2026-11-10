"""Save-derived roster and school-day policy; no EA imports or game writes.

The native Core situation still has five distinct NPC jobs.  Keep their
explicit appointments rather than silently assigning a playable student or
creating a replacement.  The remaining native Base count is derived from
the saved enrollment, not from one test household's three played teens.
"""

SIM_TICKS_PER_DAY = 1500 * 60 * 24
CORE_JOBS = (278965, 278966, 278967, 278968, 303765)


class SessionPolicyError(ValueError):
    pass


def _sim_id(value):
    if type(value) not in (int, str):
        raise SessionPolicyError('INVALID_SIM_ID')
    result = str(value)
    if not result.isdigit() or int(result) < 1 or str(int(result)) != result:
        raise SessionPolicyError('INVALID_SIM_ID')
    return result


def _short_diagnostic(value, limit=18):
    """Render a bounded, single-line read-only diagnostic from a live Sim."""
    try:
        return str(value).replace(chr(13), ' ').replace(chr(10), ' ')[:limit]
    except Exception:
        return '?'


def _registered_name(info):
    try:
        first = getattr(info, 'first_name', '') or ''
        last = getattr(info, 'last_name', '') or ''
        return _short_diagnostic(' '.join(
            str(value) for value in (first, last) if value), 22) or '?'
    except Exception:
        return '?'


def plan_roster(groups, played_ids, pinned, sim_info_manager,
                teen_age, human_species, core_jobs=CORE_JOBS):
    """Validate two classes and return their native invitation partition.

    ``played_ids`` comes from the live active household.  Unregistered
    household teens are reported separately and never enrolled implicitly.
    Every saved member must still be an existing human teen.  Five manual
    NPC Core appointments remain required by this adapter; with more than
    eleven played enrolled teens it refuses explicitly, without substituting
    Sims or changing native job semantics.
    """
    if (not isinstance(groups, (tuple, list)) or len(groups) != 2 or
            any(not isinstance(g, (tuple, list)) or len(g) != 8
                for g in groups)):
        raise SessionPolicyError('TWO_CLASSES_OF_EIGHT_REQUIRED')
    normalized = tuple(tuple(_sim_id(sid) for sid in group)
                       for group in groups)
    enrolled = normalized[0] + normalized[1]
    if len(set(enrolled)) != 16:
        raise SessionPolicyError('DUPLICATE_REGISTERED_STUDENT')
    if not isinstance(played_ids, (tuple, list, set, frozenset)):
        raise SessionPolicyError('PLAYED_HOUSEHOLD_UNAVAILABLE')
    household = tuple(_sim_id(sid) for sid in played_ids)
    if len(set(household)) != len(household):
        raise SessionPolicyError('DUPLICATE_PLAYED_STUDENT')
    played_set = set(household) & set(enrolled)
    played = tuple(sid for sid in enrolled if sid in played_set)
    npc_ids = set(enrolled) - played_set
    if len(npc_ids) < len(core_jobs):
        raise SessionPolicyError('INSUFFICIENT_NPC_FOR_NATIVE_CORE')
    if type(pinned) is not dict or set(pinned) != set(core_jobs):
        raise SessionPolicyError('FIVE_MANUAL_CORE_APPOINTMENTS_REQUIRED')
    appointments = {job: _sim_id(pinned[job]) for job in core_jobs}
    chosen = tuple(appointments[job] for job in core_jobs)
    if len(set(chosen)) != len(core_jobs):
        raise SessionPolicyError('DUPLICATE_CORE_APPOINTMENT')
    if not set(chosen) <= npc_ids:
        raise SessionPolicyError('CORE_REQUIRES_REGISTERED_NPC')
    getter = getattr(sim_info_manager, 'get', None)
    if not callable(getter):
        raise SessionPolicyError('SIM_INFO_MANAGER_UNAVAILABLE')
    for sid in enrolled:
        try:
            info = getter(int(sid))
            if info is None:
                raise SessionPolicyError('REGISTERED_SIM_MISSING')
            age = getattr(info, 'age', None)
            species = getattr(info, 'species', None)
            if age != teen_age or species != human_species:
                # Do not alter saved enrollment, substitute another Sim, or
                # relax the requirement. Identify the exact enrolled Sim
                # causing the block so a genuine age-up can be distinguished
                # from an unexpected EA runtime enum/species value.
                klass = 1 if sid in normalized[0] else 2
                raise SessionPolicyError(
                    'REGISTERED_SIM_NOT_HUMAN_TEEN C{} {} id={} a={} s={}'
                    .format(klass, _registered_name(info), sid,
                            _short_diagnostic(age),
                            _short_diagnostic(species)))
            # The active household provided in played_ids is authoritative.
            # is_selectable describes a transient UI state, not ownership:
            # it may be None for an NPC or True for a Sim from another
            # previously played household. Never reject a valid enrolled
            # student solely because that flag changes across save/reload.
        except SessionPolicyError:
            raise
        except Exception:
            raise SessionPolicyError('SIM_INFO_READ_FAILED')
    base = tuple(sid for sid in enrolled
                 if sid not in played_set and sid not in chosen)
    return {
        'groups': normalized,
        'enrolled': enrolled,
        'played': played,
        'base': base,
        'pinned': appointments,
        'unregistered_played': tuple(sid for sid in household
                                     if sid not in set(enrolled)),
    }


def school_day_key(slot, absolute_ticks):
    """Use processed simulation time, never the displayed UI clock."""
    try:
        slot = _sim_id(slot)
    except SessionPolicyError:
        raise SessionPolicyError('SAVE_SLOT_UNAVAILABLE')
    if int(slot) >= 0xFFFFFFFE:
        raise SessionPolicyError('SAVE_SLOT_UNAVAILABLE')
    if type(absolute_ticks) is not int or absolute_ticks < 0:
        raise SessionPolicyError('SIMULATION_TIME_UNAVAILABLE')
    return slot, absolute_ticks // SIM_TICKS_PER_DAY


def _valid_key(value):
    if not (isinstance(value, tuple) and len(value) == 2 and
            type(value[0]) is str and type(value[1]) is int and value[1] >= 0):
        return False
    try:
        return school_day_key(value[0], value[1] * SIM_TICKS_PER_DAY) == value
    except SessionPolicyError:
        return False


def session_decision(current_key, new_key, settings_active, in_school,
                     roster_changed=False, zone_changed=False, reload=False):
    """Choose bookkeeping lifecycle without touching any EA situation.

    A RESET means discard the previous day's *controller bookkeeping* before
    EA creates the new day's situations.  It does not replay EA scheduling,
    cancel actions, respawn Sims, or create a school day.  Midday enrollment
    changes are always deferred.  Loading directly into an active school day
    cannot safely reconstruct already-issued invitations and requires home
    activation instead of silently installing a second controller.
    """
    flags = (settings_active, in_school, roster_changed, zone_changed, reload)
    if any(type(flag) is not bool for flag in flags):
        return 'BLOCK', 'INVALID_SESSION_CONTEXT'
    if not settings_active:
        return 'STOP', 'MANAGEMENT_DISABLED'
    if not _valid_key(new_key):
        return 'BLOCK', 'SIMULATION_TIME_OR_SLOT_UNAVAILABLE'
    if current_key is not None and not _valid_key(current_key):
        return 'BLOCK', 'CURRENT_SESSION_KEY_INVALID'
    if current_key is None:
        if in_school:
            return 'BLOCK', 'INITIAL_ACTIVATION_REQUIRES_HOME'
        return 'START', 'VERIFIED_HOME_ACTIVATION'
    if current_key[0] != new_key[0]:
        if in_school:
            return 'STOP', 'SAVE_CHANGED_DURING_SCHOOL'
        return 'RESET', 'SAVE_SLOT_CHANGED'
    if new_key[1] < current_key[1]:
        if in_school:
            return 'STOP', 'EARLIER_SAVE_LOADED_DURING_SCHOOL'
        return 'RESET', 'EARLIER_SAVE_RELOADED'
    if reload:
        if in_school:
            return 'STOP', 'SCHOOL_RELOAD_REQUIRES_HOME'
        return 'RESET', 'HOME_RELOAD'
    if new_key[1] > current_key[1]:
        return 'RESET', 'NEW_SCHOOL_DAY'
    if in_school:
        if roster_changed:
            return 'DEFER', 'ROSTER_CHANGES_APPLY_NEXT_SCHOOL_DAY'
        return 'KEEP', 'ACTIVE_SCHOOL_DAY_PRESERVED'
    if roster_changed:
        return 'RESET', 'HOME_ROSTER_CHANGED'
    if zone_changed:
        return 'RESET', 'HOME_ZONE_CHANGED'
    return 'KEEP', 'SAME_SAVE_AND_DAY'
