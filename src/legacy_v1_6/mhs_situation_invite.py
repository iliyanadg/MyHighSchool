"""Experimental invitation integration for ONE previously enrolled test Sim.

EA XML reference, owned/extracted by the user:
 situation_HighSchool_Active_NPC_Base_Student (277733), job (277894).
Uses an EA staff-suggested API that is not guaranteed for every situation.
No hidden-API patching, no tuning overrides, no global auto spawn, no JSON writes.
"""
from mhs_school_diagnostics import situation_guid

TEST_SIM_ID = '568605179473255124'  # Amarachi Darong in user's TEST save 3
BASE_STUDENT_SITUATION = 277733
BASE_STUDENT_JOB = 277894


class InvitationCheckError(RuntimeError):
    pass


def _loaded_teen_situations(manager, sim_manager, teen_age):
    if manager is None or sim_manager is None:
        raise InvitationCheckError('Gestore Sims o situazioni non disponibile')
    method = getattr(manager, 'get_situations_sim_is_in', None)
    if not callable(method):
        raise InvitationCheckError('API lettura situazioni non disponibile')
    seen = set()
    matches = []
    for info in sim_manager.get_all():
        if getattr(info, 'age', None) != teen_age:
            continue
        getter = getattr(info, 'get_sim_instance', None)
        if not callable(getter):
            continue
        try:
            sim = getter()
            if sim is None:
                continue
            for situation in tuple(method(sim) or ()):
                if situation_guid(situation) != BASE_STUDENT_SITUATION:
                    continue
                key = id(situation)
                if key not in seen:
                    seen.add(key)
                    matches.append(situation)
        except Exception:
            continue
    return matches


def _student_job(situation):
    all_jobs = getattr(situation, 'all_jobs_gen', None)
    if callable(all_jobs):
        try:
            for job in all_jobs():
                if int(getattr(job, 'guid64', -1)) == BASE_STUDENT_JOB:
                    return job
        except Exception:
            pass
    # Explicitly do not guess a job by name or use numeric id as a job object.
    return None


def check_invitation(manager, sim_manager, target_info, teen_age):
    situations = _loaded_teen_situations(manager, sim_manager, teen_age)
    # Do NOT choose arbitrarily if multiple matching base situations exist.
    if len(situations) > 1:
        raise InvitationCheckError('Trovate piu situazioni NPC_Base_Student; test bloccato')
    situation = situations[0] if situations else None
    job = _student_job(situation) if situation is not None else None
    method = getattr(situation, 'invite_sim_to_job', None) if situation is not None else None
    getter = getattr(target_info, 'get_sim_instance', None)
    instance = getter() if callable(getter) else None
    already = False
    if instance is not None and situation is not None:
        get_for_sim = getattr(manager, 'get_situations_sim_is_in', None)
        if callable(get_for_sim):
            try:
                already = situation in tuple(get_for_sim(instance) or ())
            except Exception:
                pass
    return {'situation': situation, 'job': job,
            'method': method if callable(method) else None,
            'already': already, 'instance': instance}


def invite_once(preflight, target_info):
    """One EA API call only; never guesses alternative signatures or spawns via cheats.

    Sends loaded Sim instance if available, else SimInfo. Some versions may reject
    unloaded SimInfo; report failure rather than adding new lots/situations or retrying.
    """
    method, job = preflight['method'], preflight['job']
    if not callable(method) or job is None or preflight['situation'] is None:
        raise InvitationCheckError('Precondizioni mancanti')
    if preflight['already']:
        return False, 'gia partecipante'
    candidate = preflight['instance'] if preflight['instance'] is not None else target_info
    try:
        response = method(candidate, job=job)
    except Exception as exc:
        return False, 'API ha rifiutato la richiesta: {}'.format(type(exc).__name__)
    return True, 'richiesta inviata (risposta {}); verifica in gioco'.format(type(response).__name__)


def inspect_student_situations(manager, sim_manager, teen_age):
    """List all Base Student situation instances seen on loaded teens, READ ONLY.

    Distinct instances can share the same EA tuning GUID.  An instance ID is
    displayed for diagnostics ONLY.  This function NEVER chooses/invites.
    The participant counts represent loaded teens discovered by inspection,
    not necessarily every participant of a situation.
    """
    if manager is None or sim_manager is None:
        raise InvitationCheckError('Gestore situazioni o Sims non disponibile')
    getter = getattr(manager, 'get_situations_sim_is_in', None)
    if not callable(getter):
        raise InvitationCheckError('API di lettura situazioni non disponibile')
    seen = {}
    for info in sim_manager.get_all():
        if info is None or getattr(info, 'age', None) != teen_age:
            continue
        sim_getter = getattr(info, 'get_sim_instance', None)
        if not callable(sim_getter):
            continue
        try:
            sim = sim_getter()
            if sim is None:
                continue
            situations = tuple(getter(sim) or ())
        except Exception:
            continue
        name = '{} {}'.format(getattr(info, 'first_name', '') or '',
                              getattr(info, 'last_name', '') or '').strip()
        sid = str(getattr(info, 'sim_id', None) or id(info))
        for situation in situations:
            if situation_guid(situation) != BASE_STUDENT_SITUATION:
                continue
            key = id(situation)
            if key not in seen:
                run_id = getattr(situation, 'id', None)
                if run_id is None:
                    run_id = getattr(situation, 'situation_id', None)
                job = _student_job(situation)
                method = getattr(situation, 'invite_sim_to_job', None)
                seen[key] = {
                    'run_id': str(run_id) if run_id is not None else 'non esposto',
                    'job_available': job is not None,
                    'api_available': callable(method),
                    'members': {},
                }
            seen[key]['members'][sid] = name or '(senza nome)'
    # Order is purely for display and NEVER used to pick a situation for an invite.
    result = list(seen.values())
    result.sort(key=lambda row: (row['run_id'], sorted(row['members'].values())))
    return result
