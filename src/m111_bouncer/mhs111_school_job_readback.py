"""M111: read original EA school situation/job membership, no EA hooks.

Uses SituationManager.get_situations_sim_is_in(sim) and
BaseSituation.get_current_job_for_sim(sim), both already identified in
the user's EA sources. Does not alter students, filters, situations or
roster. An EA job readback is not a proven Bouncer completion barrier,
nor proof that the Sim is physically in the right classroom/seat.

A school enrollment is a MHS class 1/2, NOT a native EA situation:
Class 1 uses two alternate EA native situations (WithTrait/NoTrait).
The same job GUID 277919 is also used in Class 2 preparation.
Python 3.7 compatible. Not a standalone game entry point.
"""
from collections import defaultdict

# situation GUID -> (EA phase, MHS class, exact student job GUID)
# Taken from M108 native phase tuning and checked by real M110 Mac trace.
CLASS_PHASES = {
    293815: ('prepare', 1, 277919),
    304701: ('prepare', 1, 277919),
    297774: ('prepare', 2, 277919),
    304565: ('lesson', 1, 277919),
    304703: ('lesson', 1, 277919),
    304567: ('lesson', 2, 280777),
}
BASE_CORE = frozenset((277733, 298052))
MAX_SITUATIONS_PER_SIM = 64


def _sid(value):
    if type(value) not in (str, int) or not str(value).isdigit():
        return None
    value = str(value)
    if not value.isdigit() or int(value) < 1 or str(int(value)) != value:
        return None
    return value


def _guid(tuned):
    if tuned is None:
        return None
    for item in (tuned, getattr(tuned, 'tuned_class', None), type(tuned)):
        if item is None:
            continue
        try:
            value = getattr(item, 'guid64', None)
        except Exception:
            continue
        if type(value) is int and value > 0:
            return value
    return None


def _blocked(reason, **details):
    out = {
        'kind': 'M111_EA_CLASS_JOB_READBACK_NO_MUTATION',
        'status': reason, 'game_modified': False,
        'post_bouncer_barrier_verified': False,
        'exact_16_native_membership_verified': False,
        'two_classroom_seating_verified': False,
        'full_school_day_verified': False,
    }
    out.update(details)
    return out


def _expected(manifest):
    """Reject incomplete, duplicated or extra classes (no fake 16/16)."""
    try:
        if (getattr(manifest, 'selected_count', None) != 16
                or len(manifest.class_ids) != 2
                or len(manifest.class_ids[0]) != 8
                or len(manifest.class_ids[1]) != 8):
            return None
        groups = tuple(tuple(_sid(s) for s in c)
                       for c in manifest.class_ids)
        flat = groups[0] + groups[1]
        if (None in flat or len(set(flat)) != 16
                or set(flat) != set(manifest.all_student_ids)):
            return None
        return groups
    except (ValueError, AttributeError, TypeError, IndexError):
        return None


def observe_school_job_memberships(manifest, manager, sim_infos,
                                   teen_age, human_species, phase):
    """Read one *current* classroom phase for the exact enrolled cohort.

    Each observed member is sourced from a live instantiated teen plus
    SituationManager membership and the EA job getter. This is a
    non-hooked snapshot; absence is a snapshot, not proof of failed
    Bouncer spawning, and job presence is not proof of classroom seating.
    """
    expected = _expected(manifest)
    if expected is None:
        return _blocked('ROSTER_NOT_TWO_FULL_CLASSES')
    if phase not in ('lesson', 'prepare'):
        return _blocked('UNVERIFIED_SCHOOL_PHASE')
    getter = getattr(manager, 'get_situations_sim_is_in', None)
    if not callable(getter):
        return _blocked('EA_SITUATION_MEMBERSHIP_API_UNAVAILABLE')
    try:
        candidates = tuple(sim_infos)
    except Exception:
        return _blocked('EA_SIM_INFO_LIST_UNAVAILABLE')

    on_lot = set()
    seen_infos = set()
    untrusted = []
    rows = []
    actual = {1:set(), 2:set()}
    wrong_jobs = []
    duplicate_jobs = set()
    base_core = []
    # Protect against game APIs returning huge or indefinite collections.
    for info in candidates:
        try:
            if (getattr(info, 'age', None) != teen_age
                    or getattr(info, 'species', None) != human_species):
                continue
            sid = _sid(getattr(info, 'sim_id', None))
            if sid is None:
                untrusted.append('INVALID_TEEN_ID')
                continue
            instance = info.get_sim_instance()
        except Exception:
            untrusted.append('SIM_INFO_READ_FAILED')
            continue
        if instance is None:
            continue
        if sid in seen_infos:
            untrusted.append('DUPLICATE_INSTANTIATED_TEEN')
            continue
        seen_infos.add(sid)
        on_lot.add(sid)
        try:
            situations = getter(instance)
            if situations is None:
                untrusted.append('EA_SITUATION_GETTER_RETURNED_NONE')
                continue
            it = iter(situations)
            # A 65th entry would make the snapshot incomplete, not PASS.
            limited = []
            for index, situation in enumerate(it):
                if index >= MAX_SITUATIONS_PER_SIM:
                    untrusted.append('TOO_MANY_SITUATIONS_FOR_SIM')
                    break
                limited.append(situation)
        except Exception:
            untrusted.append('EA_SITUATION_READ_FAILED')
            continue
        for situation in limited:
            guid = _guid(situation)
            if guid not in CLASS_PHASES and guid not in BASE_CORE:
                continue
            job_reader = getattr(situation, 'get_current_job_for_sim', None)
            if not callable(job_reader):
                untrusted.append('EA_JOB_API_UNAVAILABLE')
                rows.append((sid, guid, None))
                continue
            try:
                job_guid = _guid(job_reader(instance))
            except Exception:
                untrusted.append('EA_JOB_READ_FAILED')
                job_guid = None
            if job_guid is None:
                untrusted.append('EA_JOB_UNKNOWN')
            rows.append((sid, guid, job_guid))
            if guid in BASE_CORE:
                base_core.append((sid, guid, job_guid))
                continue
            stage, klass, required_job = CLASS_PHASES[guid]
            if stage != phase:
                continue
            if job_guid != required_job:
                wrong_jobs.append((sid, guid, job_guid, required_job))
                continue
            if sid in actual[klass]:
                duplicate_jobs.add(sid)
            actual[klass].add(sid)

    unexpected = tuple(sorted(on_lot - set(expected[0] + expected[1]), key=int))
    absent = tuple(sorted(set(expected[0] + expected[1]) - on_lot, key=int))
    missing_per_class = {
        klass: tuple(sorted(set(expected[klass-1])-actual[klass], key=int))
        for klass in (1, 2)
    }
    wrong_class = tuple(sorted(
        (sid, klass) for klass in (1, 2)
        for sid in actual[klass]
        if sid not in expected[klass-1]))
    repeated_cross_class = tuple(sorted(actual[1] & actual[2], key=int))
    class_rows = {str(i): tuple(sorted(actual[i], key=int)) for i in (1, 2)}
    result = _blocked(
        'EA_SCHOOL_JOB_SNAPSHOT_RECORDED',
        phase=phase,
        roster_slot=str(getattr(manifest, 'slot', '')),
        expected_per_class=(8, 8),
        instantiated_teen_count=len(on_lot),
        enrolled_instantiated_count=16-len(absent),
        missing_enrolled_ids=absent,
        extra_instantiated_teen_ids=unexpected,
        observed_class_job_ids=class_rows,
        missing_current_phase_jobs=missing_per_class,
        unexpected_class_memberships=wrong_class,
        duplicate_memberships=tuple(sorted(
            duplicate_jobs | set(repeated_cross_class), key=int)),
        wrong_native_job_guids=tuple(wrong_jobs),
        base_core_native_memberships=tuple(sorted(base_core)),
        untrusted_observation_reasons=tuple(sorted(set(untrusted))),
        # These are actual game job readbacks, NOT post-Bouncer attestation.
        observed_native_school_memberships=tuple(sorted(rows)),
        source='EA_GET_SITUATIONS_SIM_IS_IN_AND_GET_CURRENT_JOB',
    )
    matches = (
        not absent and not unexpected and not wrong_jobs
        and not wrong_class and not repeated_cross_class and not duplicate_jobs
        and not untrusted
        and all(actual[i] == set(expected[i-1]) for i in (1, 2))
    )
    if untrusted:
        result['status'] = 'EA_READBACK_INCOMPLETE'
    elif matches:
        result['status'] = 'SINGLE_PHASE_JOB_MEMBERSHIPS_MATCH_OBSERVED'
    elif any(actual.values()) or on_lot:
        result['status'] = 'SINGLE_PHASE_JOB_MEMBERSHIPS_DIFFER'
    else:
        result['status'] = 'NO_INSTANTIATED_HUMAN_TEENS_OBSERVED'
    return result
