"""ONE student-only experimental EA school-situation creation, without guessing.

EA tuning exported by the user:
  277733 = situation_HighSchool_Active_NPC_Base_Student
  277894 = job_HighSchool_Active_Base_NPC_Student
The base job sim_auto_invite upper_bound is 1. The game may therefore run
several same-type situation instances concurrently. Creating a one-Sim
situation avoids choosing an existing instance arbitrarily.

No tuning edits, no changes to roster JSON, no automatic retries.
The game engine can refuse the new situation; school attendance is NOT proven
by creation alone. Test save only.
"""

TARGET_SIM_ID = 568605179473255124
TEST_SAVE_SLOT = 3
BASE_SITUATION_GUID = 277733
BASE_JOB_GUID = 277894


class CallError(RuntimeError):
    pass


def preflight(sim_info, teen_age, situation_manager, school_running, roster_contains, current_slot=None):
    """Pure validations; may run with save slot 0 due to EA travel bug."""
    if sim_info is None or int(getattr(sim_info, 'sim_id', 0)) != TARGET_SIM_ID:
        raise CallError('Amarachi non trovata in questa partita: nessuna azione.')
    if getattr(sim_info, 'age', None) != teen_age:
        raise CallError('Amarachi non e adolescente: nessuna azione.')
    name = '{} {}'.format(getattr(sim_info, 'first_name', ''), getattr(sim_info, 'last_name', '')).casefold()
    if 'amarachi' not in name or 'darong' not in name:
        raise CallError('ID non corrisponde al nome Amarachi Darong: nessuna azione.')
    if current_slot is not None and str(current_slot) != str(TEST_SAVE_SLOT):
        raise CallError('Non sei nel salvataggio di prova 3: nessuna azione.')
    if not roster_contains:
        raise CallError('Amarachi non e iscritta alla Classe 1 del registro di prova: nessuna azione.')
    if situation_manager is None or not callable(getattr(situation_manager, 'create_situation', None)):
        raise CallError('API create_situation non disponibile: nessuna azione.')
    if not school_running:
        raise CallError('Giornata scolastica attiva non rilevata: usa il comando DURANTE le lezioni.')


def check_school_is_running(situation_manager, sim_infos, teen_age, situation_guid_fn):
    """Check a live Base Student situation (observed in v0.7.3)."""
    get_sims_situations = getattr(situation_manager, 'get_situations_sim_is_in', None)
    if not callable(get_sims_situations):
        return False
    for info in sim_infos:
        if getattr(info, 'age', None) != teen_age:
            continue
        get_inst = getattr(info, 'get_sim_instance', None)
        if not callable(get_inst):
            continue
        try:
            sim = get_inst()
            if sim is None:
                continue
            for situation in tuple(get_sims_situations(sim) or ()):
                if situation_guid_fn(situation) == BASE_SITUATION_GUID:
                    return True
        except Exception:
            continue
    return False


def create_for_am(ar_info, situation_manager, situation_tuning, job_tuning,
                  guest_list_type, guest_info_type, invitation_purpose):
    """Try one documented game API call; returns running situation id.

    Never guesses a job from an existing situation or selects a random instance.
    """
    if situation_tuning is None:
        raise CallError('Tuning EA della situazione non trovato (277733).')
    # The EA situation XML supplied by the user explicitly declares 277894
    # in default_job_and_roles. Runtime situation_tuning.default_job() is NOT
    # a reliable check of that mapping; it can be None or refer to a different
    # generic default. Fetch the actual EA job tuning by its own GUID instead.
    if int(getattr(situation_tuning, 'guid64', -1)) != BASE_SITUATION_GUID:
        raise CallError('Situazione diversa dalla EA 277733: azione annullata.')
    job = job_tuning
    if job is None or int(getattr(job, 'guid64', -1)) != BASE_JOB_GUID:
        raise CallError('Ruolo EA 277894 non trovato nel gioco: azione annullata.')
    guest_list = guest_list_type(invite_only=True)
    guest = guest_info_type.construct_from_purpose(TARGET_SIM_ID, job, invitation_purpose)
    guest_list.add_guest_info(guest)
    creation = getattr(situation_manager, 'create_situation', None)
    if not callable(creation):
        raise CallError('API create_situation non disponibile.')
    # Exactly one call, no fallback that might invite multiple NPCs.
    result = creation(situation_tuning, guest_list=guest_list,
                      user_facing=False, creation_source='MY HIGH SCHOOL test save 3')
    if not result:
        raise CallError('Il gioco non ha avviato la situazione EA. Non ripetere a raffica.')
    return result
