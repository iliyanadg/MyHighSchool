"""M116: read exact original EA Base/Core SituationJob members by create receipt.

A SchoolNativeGuestSession now preserves the original situation ID for
each Base:student and Core invitation. Query SituationManager.get(id),
BaseSituation.all_jobs_gen and all_sims_in_job_gen to compare what EA
actually assigned versus the *specific* thirteen chosen NPC Sim IDs.

Read only. NO Bouncer callback is installed here. A match in a snapshot
does not prove Bouncer event provenance, 3 playable arrival, lesson jobs,
classroom seating, full-day attendance or absence of wider lot capacity.
"""
from mhs108_native_invitation import (
    BASE_JOB, CORE_JOBS, BASE_SITUATION, CORE_SITUATION,
    SchoolNativeGuestSession,
)

KNOWN_STAFF_JOBS = frozenset((277895, 278963))


def _guid(value):
    found = getattr(value, 'guid64', None)
    return found if type(found) is int and found > 0 else None


def _sim_id(value):
    one = getattr(value, 'id', None)
    two = getattr(value, 'sim_id', None)
    if one is not None and two is not None and one != two:
        return None
    found = one if one is not None else two
    if type(found) is not int or found <= 0:
        return None
    return str(found)


def _blocked(status, **extra):
    out = {
        'kind': 'M116_ORIGINAL_EA_BASE_CORE_NATIVE_JOB_READBACK',
        'status': status,
        'game_modified': False,
        'native_ea_methods_wrapped': False,
        'native_guest_jobs_13_verified_in_snapshot': False,
        'post_bouncer_callback_provenance_verified': False,
        'all_3_playables_on_lot_verified': False,
        'native_two_classroom_lessons_verified': False,
        'all_16_students_attending_verified': False,
        'classroom_seating_verified': False,
        'full_school_day_verified': False,
    }
    out.update(extra)
    return out


def inspect_created_native_guest_jobs(session, manager):
    """Compare all nine native situation IDs against real EA job members.

    Returns incomplete/mismatch instead of falling back to random
    students when the original EA SituationManager cannot find a job.
    Source identity and callback timing must still be verified by a
    future original-EA post-Bouncer stage.
    """
    if not isinstance(session, SchoolNativeGuestSession):
        return _blocked('NATIVE_GUEST_SESSION_NOT_READY')
    manifest = session.manifest
    receipts = dict(session.native_created_receipts())
    expected_tickets = set(['core'] +
                           ['base:'+sid for sid in manifest['base_ids']])
    if (len(receipts) != 9 or set(receipts) != expected_tickets or
            len(set(receipts.values())) != 9):
        return _blocked('NATIVE_EA_NINE_CREATE_RECEIPTS_NOT_READY',
                        receipts_present=len(receipts))
    getter = getattr(manager, 'get', None)
    if not callable(getter):
        return _blocked('EA_SITUATION_MANAGER_GET_MISSING')
    assignment_done = getattr(manager, '_sim_assignment_complete', None)
    if assignment_done is not True:
        return _blocked('EA_SPINUP_ASSIGNMENT_FLAG_NOT_OBSERVED')
    observed = {}
    unexpected_student_ids = set()
    discrepancies = []
    seen_sim_ids = set()
    expected_core = dict(manifest['core_assignments'])
    requested_base = set(manifest['base_ids'])
    for ticket, situation_id in sorted(receipts.items()):
        situation = getter(situation_id)
        if situation is None:
            discrepancies.append((ticket, 'EA_SITUATION_ID_MISSING'))
            continue
        wanted_type = (CORE_SITUATION if ticket == 'core'
                       else BASE_SITUATION)
        if _guid(situation) != wanted_type:
            discrepancies.append((ticket, 'WRONG_NATIVE_SITUATION_GUID'))
            continue
        jobs_method = getattr(situation, 'all_jobs_gen', None)
        members_method = getattr(situation, 'all_sims_in_job_gen', None)
        all_method = getattr(situation, 'all_sims_in_situation_gen', None)
        if not all(callable(method) for method in (
                jobs_method, members_method, all_method)):
            discrepancies.append((ticket, 'EA_JOB_MEMBERSHIP_API_MISSING'))
            continue
        try:
            jobs = tuple(jobs_method())
            if not jobs:
                discrepancies.append((ticket, 'NO_NATIVE_JOB_TYPES'))
                continue
            found_by_job = {}
            everybody = set()
            for job in jobs:
                guid = _guid(job)
                if guid is None or guid in found_by_job:
                    raise ValueError('AMBIGUOUS_JOB_GUID')
                sims = tuple(members_method(job))
                ids = tuple(_sim_id(sim) for sim in sims)
                if (None in ids or len(ids) != len(set(ids))
                        or everybody.intersection(ids)):
                    raise ValueError('DUPLICATE_OR_INVALID_SIM')
                everybody.update(ids)
                found_by_job[guid] = set(ids)
            actual = tuple(_sim_id(sim) for sim in all_method())
            if (None in actual or len(actual) != len(set(actual))
                    or set(actual) != everybody):
                raise ValueError('INCONSISTENT_SITUATION_MEMBERS')
            if set(found_by_job) - (
                    set((BASE_JOB,) + CORE_JOBS) | KNOWN_STAFF_JOBS):
                raise ValueError('UNKNOWN_NATIVE_JOB_TYPE')
            for guid in KNOWN_STAFF_JOBS:
                if found_by_job.get(guid, set()) & set(manifest['all_16']):
                    raise ValueError('ENROLLED_STUDENT_HAS_STAFF_JOB')
        except Exception as exc:
            discrepancies.append((ticket, type(exc).__name__))
            continue
        if ticket == 'core':
            actual_core = {
                job: found_by_job.get(job, set()) for job in CORE_JOBS}
            if (set(found_by_job) & set([BASE_JOB])
                    or any(actual_core[job] != {expected_core[job]}
                           for job in CORE_JOBS)):
                discrepancies.append((ticket, 'CORE_NPC_JOB_MISMATCH'))
                unexpected_student_ids.update(
                    set().union(*actual_core.values()) -
                    set(expected_core.values()))
                continue
            members = set(expected_core.values())
        else:
            expected_sid = ticket.split(':', 1)[1]
            actual_base = found_by_job.get(BASE_JOB, set())
            if (actual_base != {expected_sid}
                    or set(found_by_job) & set(CORE_JOBS)):
                discrepancies.append((ticket, 'BASE_NPC_JOB_MISMATCH'))
                unexpected_student_ids.update(actual_base - {expected_sid})
                continue
            members = {expected_sid}
        if seen_sim_ids.intersection(members):
            discrepancies.append((ticket, 'STUDENT_ASSIGNED_TWICE'))
            continue
        seen_sim_ids.update(members)
        observed[ticket] = {
            'situation_id': situation_id,
            'situation_guid': wanted_type,
            'student_sim_ids': tuple(sorted(members, key=int)),
        }
    wanted = requested_base | set(expected_core.values())
    status = ('NATIVE_GUEST_JOBS_MATCH_OBSERVED'
              if not discrepancies and seen_sim_ids == wanted
              else 'NATIVE_GUEST_JOBS_DIFFER')
    return _blocked(
        status,
        native_guest_jobs_13_verified_in_snapshot=(status ==
            'NATIVE_GUEST_JOBS_MATCH_OBSERVED'),
        number_original_native_situations_found=len(observed),
        enrolled_npc_job_ids_observed=len(seen_sim_ids),
        native_situation_receipts_read=len(receipts),
        discrepancies=tuple(discrepancies),
        extra_native_student_ids=tuple(sorted(unexpected_student_ids,
                                              key=int)),
        matching_native_situation_student_assignments=observed,
        ea_zone_spinup_assignment_flag_observed=True,
        readback_source='ORIGINAL_EA_SITUATION_MANAGER_GET_AND_JOB_GENERATORS',
    )
