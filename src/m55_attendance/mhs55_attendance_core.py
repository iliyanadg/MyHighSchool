"""M55: guarded school-presence trial for a single enrolled human teenager.

Only the explicit native-picker confirmation may call an EA situation API.
The external classroom roster is read-only. No automatic attendance scheduler,
EA tuning overrides, staff changes, or class-trait manipulation.
"""
BASE_STUDENT_SITUATION = 277733
BASE_STUDENT_JOB = 277894


class AttendanceError(ValueError):
    pass


def valid_student(sim_info, teen_age, human_species):
    return (sim_info is not None and
            getattr(sim_info, 'species', None) == human_species and
            getattr(sim_info, 'age', None) == teen_age)


def select_one(enrolled, offered, chosen):
    """Resolve one exact roster ID; reject stale or unexpected picker results."""
    if type(chosen) not in (tuple, list) or len(chosen) != 1:
        raise AttendanceError('Seleziona un solo studente')
    sid = str(chosen[0])
    if (not sid.isdigit() or not int(sid) or
            str(int(sid)) != sid or sid not in set(enrolled) or
            sid not in set(offered)):
        raise AttendanceError('Studente non iscritto o selezione scaduta')
    return sid


def situation_guid(instance):
    """Use the situation tuning ID, never a running instance ID."""
    for entry in (type(instance), getattr(instance, 'situation_type', None), instance):
        if entry is None:
            continue
        try:
            value = getattr(entry, 'guid64', None)
            if value is not None:
                return int(value)
        except (TypeError, ValueError, AttributeError):
            pass
    return None


def school_running(manager, sim_infos, teen_age):
    """Require at least one live EA Base Student situation before an attempt."""
    if manager is None:
        return False
    getter = getattr(manager, 'get_situations_sim_is_in', None)
    if not callable(getter):
        return False
    for info in sim_infos:
        if getattr(info, 'age', None) != teen_age:
            continue
        try:
            get_sim = getattr(info, 'get_sim_instance', None)
            sim = get_sim() if callable(get_sim) else None
            if sim is not None and any(situation_guid(s) == BASE_STUDENT_SITUATION
                                       for s in tuple(getter(sim) or ())):
                return True
        except Exception:
            continue
    return False


def already_in_base_student(manager, sim_info):
    """A loaded participant cannot be invited twice.

    Fail closed when the situation membership API is unavailable or fails.
    """
    getter = getattr(manager, 'get_situations_sim_is_in', None)
    if not callable(getter):
        raise AttendanceError('API di controllo situazioni assente')
    get_sim = getattr(sim_info, 'get_sim_instance', None)
    try:
        sim = get_sim() if callable(get_sim) else None
        if sim is None:
            return False
        return any(situation_guid(s) == BASE_STUDENT_SITUATION
                   for s in tuple(getter(sim) or ()))
    except Exception:
        raise AttendanceError('Impossibile verificare le situazioni dello studente')


def create_single_student_situation(manager, info, situation_tuning, job_tuning,
                                    guest_list_type, guest_info_type, invited_purpose):
    """One explicit API call using EA student-situation and job tuning IDs.

    Returning an ID confirms only a request, NOT that the Sim arrived or
    attends lessons. Never silently retry.
    """
    if (situation_tuning is None or
            getattr(situation_tuning, 'guid64', None) != BASE_STUDENT_SITUATION or
            job_tuning is None or
            getattr(job_tuning, 'guid64', None) != BASE_STUDENT_JOB):
        raise AttendanceError('Ruolo o situazione liceo EA non disponibile')
    create = getattr(manager, 'create_situation', None)
    if not callable(create):
        raise AttendanceError('API convocazione EA non disponibile')
    guest_list = guest_list_type(invite_only=True)
    guest = guest_info_type.construct_from_purpose(
        int(info.sim_id), job_tuning, invited_purpose)
    guest_list.add_guest_info(guest)
    result = create(situation_tuning, guest_list=guest_list,
                    user_facing=False, creation_source='MY HIGH SCHOOL M55 test')
    if not result:
        raise AttendanceError('EA non ha creato la situazione studente')
    return result
