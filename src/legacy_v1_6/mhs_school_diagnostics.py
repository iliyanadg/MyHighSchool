"""MY HIGH SCHOOL v0.6 - diagnostic of live school situations (NO spawn).

The mapping below comes from the resource IDs in the user's own exported
EA XML tuning; no tuning or third-party script is copied into this mod.

All functions are read-only and introspective; game APIs can differ by patch.
"""

KNOWN_SCHOOL_SITUATIONS = {
    276363: 'situation_HighSchool_Active_NPC_AttendClass',
    276364: 'situation_HighSchool_Active_NPC_TeachClass',
    276420: 'situation_HighSchool_Active_NPC_Bullies',
    276679: 'situation_HighSchool_Active_Player_Orientation',
    276680: 'situation_HighSchool_Active_Player_FreeTime',
    276681: 'situation_HighSchool_Active_Player_AttendClass',
    276682: 'situation_HighSchool_Active_Player_AttendExam',
    276683: 'situation_HighSchool_Active_Player_Lunch',
    276684: 'situation_HighSchool_Active_Player_Afterschool',
    276685: 'situation_HighSchool_Active_Player_SchoolFight',
    276686: 'situation_HighSchool_Active_Player_Main',
    277733: 'situation_HighSchool_Active_NPC_Base_Student',
    277968: 'situation_HighSchool_Active_NPC_PrepareForClass',
    278889: 'situation_HighSchool_Active_NPC_Lunch_Faculty',
    280775: 'situation_HighSchool_Active_NPC_TPose',
    280923: 'situation_HighSchool_Active_Player_Phases_FireDrill',
    280925: 'situation_HighSchool_Active_NPC_FireDrill',
    282048: 'situation_HighSchool_Active_Player_CareerDay',
    282049: 'situation_HighSchool_Active_Player_CareerDay_NoDialog',
    282109: 'situation_HighSchool_Active_CareerDay_BackgroundNPCs',
    284009: 'situation_HighSchool_Active_NPC_ThrowFootball',
    284555: 'situation_HighSchool_Active_Player_Phases_GetReadyForClass',
    285597: 'situation_HighSchool_Active_Player_HookyAtSchool',
    285694: 'situation_HighSchool_Active_Player_HookyAtSchool_FromLoot',
    287884: 'situation_HighSchool_Active_NPC_DoMischief',
    288268: 'situation_HighSchool_Active_NPC_Base_FireFighter',
    288504: 'situation_HighSchool_Active_NPC_Lunch_Principal',
    290230: 'situation_HighSchool_Active_NPC_Clean_Janitor',
    292224: 'situation_HighSchool_Active_NPC_Teacher_ExamPrep',
    293815: 'situation_HighSchool_Active_NPC_GoToClass1',
    293819: 'situation_HighSchool_Active_NPC_GoToClass_Teacher',
    297168: 'situation_HighSchool_Active_Background_Morning',
    297579: 'situation_HighSchool_Active_Background_AfterSchool',
    297587: 'situation_HighSchool_Active_Background_SchoolFight_Fight',
    297588: 'situation_HighSchool_Active_Background_SchoolFight_Others',
    297774: 'situation_HighSchool_Active_Background_GoToClass_Others',
    298052: 'situation_HighSchool_Active_NPC_Base_CoreClassNPCs',
    298096: 'situation_HighSchool_Active_NPC_Base_VenueNPCs',
    298817: 'situation_HighSchool_Active_Background_Lunch_Student',
    304565: 'situation_HighSchool_Active_Background_AttendClass1',
    304567: 'situation_HighSchool_Active_Background_AttendClass_Others',
    304701: 'situation_HighSchool_Active_NPC_GoToClass1_NoTrait',
    304703: 'situation_HighSchool_Active_Background_AttendClass1_NoTrait',
    304829: 'situation_HighSchool_Active_Individual_Study',
}


def situation_guid(situation):
    """The tuning GUID is usually on the dynamically tuned situation type.

    Do not mistake the *running instance id* (situation.id) for a tuning GUID.
    """
    candidates = (type(situation), getattr(situation, 'situation_type', None), situation)
    for candidate in candidates:
        if candidate is None:
            continue
        try:
            value = getattr(candidate, 'guid64', None)
            if value is not None:
                return int(value)
        except (ValueError, TypeError, AttributeError):
            continue
    return None


def situation_names_for_sim(situation_manager, sim_instance):
    """Returns (recognized high-school names, total situation count, error).

    The get_situations_sim_is_in API is documented in Sims4CommunityLibrary.
    Report an unavailable API rather than inventing school participation.
    """
    if sim_instance is None:
        return [], 0, None
    if situation_manager is None:
        return [], 0, 'SituationManager non disponibile'
    getter = getattr(situation_manager, 'get_situations_sim_is_in', None)
    if not callable(getter):
        return [], 0, 'API get_situations_sim_is_in non disponibile'
    try:
        situations = tuple(getter(sim_instance) or ())
    except Exception as exc:
        return [], 0, 'Errore elenco situazioni: {}'.format(type(exc).__name__)
    names = set()
    for situation in situations:
        guid = situation_guid(situation)
        if guid in KNOWN_SCHOOL_SITUATIONS:
            names.add(KNOWN_SCHOOL_SITUATIONS[guid].replace('situation_HighSchool_Active_', ''))
    return sorted(names), len(situations), None


def zone_scan(manager, teen_records, enrolled_ids):
    """Pure read-only summary for active-world teens with instantiated Sims.

    teen_records is a list of (name, sim_id, sim_info); excludes unloaded Sims
    from school situation enumeration but includes them in roster display.
    """
    rows = []
    school_counts = {}
    errors = set()
    loaded_count = 0
    for name, sim_id, sim_info in teen_records:
        getter = getattr(sim_info, 'get_sim_instance', None)
        sim = None
        if callable(getter):
            try:
                sim = getter()
            except Exception as exc:
                errors.add('get_sim_instance: {}'.format(type(exc).__name__))
        if sim is None:
            continue
        loaded_count += 1
        schools, total, error = situation_names_for_sim(manager, sim)
        if error:
            errors.add(error)
        for label in schools:
            school_counts[label] = school_counts.get(label, 0) + 1
        rows.append((name, sim_id, schools, sim_id in enrolled_ids, total))
    return {
        'loaded_teens': loaded_count,
        'school_counts': school_counts,
        'rows': rows,
        'errors': sorted(errors),
    }
