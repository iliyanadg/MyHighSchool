"""M108 school classroom phase policy (offline, zero EA state modifications).

Six actual EA WeeklyScheduleSituationData resources, read from the user's
extracted HS Years XML, define the *native* jobs for class preparation and
lessons. These stage jobs are NOT necessarily the final classroom/seat.
Do not use an EA class-one hidden trait as proof of MHS class selection.

This is a deterministic *proposal* for existing 16 physically-present and
school-enrolled teens. No live hook, no Sim trait change, no extra situations,
no changes to EA teachers, principal, lunch, or lesson schedule.

Important: EA Class1 has different WithTrait/NoTrait branches. The two
branches are not two different MHS classes. A future native hook must
coordinate them, including original eligibility tests, upper-bound
modifiers and actual job assignment.
"""

EA_SCHOOL_SCHEDULES = frozenset((277657, 279958))

# tuning ID: (period kind, MHS class, EA background situation,
#             student-only job, original tuned upper bound)
PHASE_DATA = {
    293642: ('prepare', 1, 293815, 277919, 6),  # Class1 with trait
    293644: ('prepare', 1, 304701, 277919, 6),  # Class1 no trait
    297773: ('prepare', 2, 297774, 277919, 8),  # Others; same job ID!
    304561: ('lesson', 1, 304703, 277919, 6),   # Class1 no trait
    304563: ('lesson', 1, 304565, 277919, 6),   # Class1 with trait
    304570: ('lesson', 2, 304567, 280777, 8),   # Others
}

# EA original school clock: 09:30,10:00,13:30,14:00.
WINDOWS = {
    '09:30': 'prepare',
    '10:00': 'lesson',
    '13:30': 'prepare',
    '14:00': 'lesson',
}


def _ids(values):
    if not isinstance(values, (tuple, list, set, frozenset)):
        return None
    result = []
    for raw in values:
        if type(raw) not in (str, int) or not str(raw).isdigit():
            return None
        normalized = str(int(raw))
        if int(raw) <= 0 or normalized != str(raw):
            return None
        result.append(normalized)
    return tuple(result) if len(set(result)) == len(result) else None


def _result(status, reason='', **detail):
    result = {
        'status': status,
        'reason': reason,
        'changes_to_game': False,
        'native_phase_job_assignment_verified': False,
        'seating_verified': False,
    }
    result.update(detail)
    return result


def _manifest_groups(manifest):
    if not isinstance(manifest, dict):
        return None
    try:
        groups = manifest['classes']
        playable = _ids(manifest['playable'])
        enrolled = _ids(manifest['all_16'])
        if (manifest['status'] !=
                'M108_INVITATIONS_PREPARED_NOT_GAME_AUTHORIZED'
                or type(groups) not in (tuple, list) or len(groups) != 2
                or playable is None or len(playable) != 3
                or enrolled is None or len(enrolled) != 16):
            return None
        class1, class2 = (_ids(g) for g in groups)
        if (class1 is None or class2 is None
                or len(class1) != 8 or len(class2) != 8
                or len(set(class1 + class2)) != 16
                or tuple(class1 + class2) != tuple(enrolled)
                or not set(playable) <= set(enrolled)):
            return None
        return (class1, class2, playable, enrolled)
    except (TypeError, KeyError):
        return None


def _context_valid(manifest, context, stage):
    try:
        return (
            isinstance(context, dict)
            and context.get('verified_ea_phase_origin') is True
            and context.get('verified_school_zone') is True
            and type(context.get('schedule_guid')) is int
            and context['schedule_guid'] in EA_SCHOOL_SCHEDULES
            and str(context.get('save_slot')) == manifest['save_slot']
            and type(context.get('sim_day')) is int
            and context['sim_day'] == manifest['sim_day']
            and str(context.get('zone_id')) == manifest['school_zone']
            and context.get('time_window') in WINDOWS
            and WINDOWS[context['time_window']] == stage
        )
    except (KeyError, TypeError, ValueError):
        return False


def propose_phase_students(manifest, phase_data_guid, situation_guid,
                           student_job_guid, context,
                           observed_on_lot, observed_ea_school_members,
                           verified_native_eligible_ids):
    """Propose exact native NPC job candidates, without assigning anyone.

    Every input is required. The live caller must read *real* zone and EA
    school membership, plus the results of EA's phase eligibility tests.
    No inferred eligibility/trait changes are allowed. This policy is
    deliberately blocked when EA's native phase cap is insufficient.
    """
    groups = _manifest_groups(manifest)
    if groups is None:
        return _result('INVALID_MANIFEST', '16 distinct school teens required')
    if type(phase_data_guid) is not int or phase_data_guid not in PHASE_DATA:
        return _result('UNVERIFIED_PHASE', 'phase tuning not recognised')
    stage, class_num, expected_situation, expected_job, upper = (
        PHASE_DATA[phase_data_guid])
    if situation_guid != expected_situation or student_job_guid != expected_job:
        return _result('UNVERIFIED_PHASE',
                       'both native situation and job must match')
    if not _context_valid(manifest, context, stage):
        return _result('UNVERIFIED_CONTEXT',
                       'verified save, day, zone and school clock required')
    class1, class2, playable, enrolled = groups
    on_lot = _ids(observed_on_lot)
    school = _ids(observed_ea_school_members)
    eligible = _ids(verified_native_eligible_ids)
    if on_lot is None or school is None or eligible is None:
        return _result('OBSERVATIONS_MISSING', 'actual native sets required')
    if not set(enrolled) <= set(on_lot):
        return _result('REGISTERED_STUDENT_ABSENT',
                       'never fill an absent enrolled student with an NPC',
                       missing_ids=tuple(x for x in enrolled
                                         if x not in set(on_lot)))
    if set(school) != set(enrolled):
        return _result('EA_SCHOOL_ROLE_MISMATCH',
                       'native school situations must cover exact 16',
                       missing_ids=tuple(x for x in enrolled
                                         if x not in set(school)),
                       extraneous_ids=tuple(x for x in school
                                            if x not in set(enrolled)))
    enrolled_class = (class1, class2)[class_num - 1]
    playable_here = tuple(x for x in enrolled_class if x in set(playable))
    expected_npcs = tuple(x for x in enrolled_class
                          if x not in set(playable))
    eligible_set = set(eligible)
    missing_eligible = tuple(x for x in expected_npcs
                             if x not in eligible_set)
    report = {
        'phase_data_guid': phase_data_guid,
        'native_situation_guid': expected_situation,
        'student_job_guid': expected_job,
        'phase': stage,
        'time_window': context['time_window'],
        'class_number': class_num,
        'registered_students_in_class': 8,
        'playable_ids': playable_here,
        'exact_npc_ids': expected_npcs,
        'npc_count_required': len(expected_npcs),
        'native_tuned_npc_upper_bound': upper,
        'minimum_tuned_slot_shortfall': max(0, len(expected_npcs) - upper),
        'native_modifiers_verified': False,
        'hidden_class_one_trait_not_modified': True,
        'teachers_and_principal_untouched': True,
    }
    if missing_eligible:
        return _result('NATIVE_PHASE_ELIGIBILITY_BLOCKED',
                       'original EA phase tests exclude chosen registered NPCs',
                       rejected_registered_ids=missing_eligible, **report)
    if len(expected_npcs) > upper:
        return _result('NATIVE_PHASE_CAPACITY_BLOCKED',
                       'native phase count must be safely extended',
                       **report)
    # This is only a candidate proposal. EA's phase modifiers and
    # simultaneous WithTrait/NoTrait branches may still constrain it.
    return _result('PROPOSED_NOT_EA_ASSIGNED',
                   'all requested NPCs are eligible in the supplied observations',
                   **report)


def assess_native_phase_result(manifest, phase, time_window,
                               actual_class1_npcs, actual_class2_npcs,
                               actual_seated_by_class=None):
    """Evaluate observed EA assignments; absence of seating data stays unknown.

    EA phase job IDs overlap between classroom paths. Therefore callers
    MUST supply actual situation-scoped membership for each class,
    aggregated across EA Class1 WithTrait/NoTrait branches.
    """
    groups = _manifest_groups(manifest)
    if groups is None:
        return _result('INVALID_MANIFEST')
    if WINDOWS.get(time_window) != phase:
        return _result('UNVERIFIED_PHASE')
    class1, class2, playable, enrolled = groups
    actual1, actual2 = _ids(actual_class1_npcs), _ids(actual_class2_npcs)
    if actual1 is None or actual2 is None:
        return _result('OBSERVATIONS_MISSING')
    played = set(playable)
    expected1 = frozenset(x for x in class1 if x not in played)
    expected2 = frozenset(x for x in class2 if x not in played)
    if (frozenset(actual1) != expected1
            or frozenset(actual2) != expected2
            or set(actual1) & set(actual2)):
        return _result(
            'WRONG_NATIVE_CLASSROOM_PHASE',
            'EA situation-scoped job members do not match MHS classes',
            class1_matched=len(expected1 & set(actual1)),
            class2_matched=len(expected2 & set(actual2)),
        )
    if phase != 'lesson':
        return _result('PREPARATION_NPC_JOBS_MATCH',
                       'go-to-class job membership is not lesson seating',
                       native_phase_job_assignment_verified=True)
    if actual_seated_by_class is None:
        return _result('LESSON_NPC_JOBS_MATCH_SEATING_UNKNOWN',
                       'job membership does not prove students are seated',
                       native_phase_job_assignment_verified=True)
    if (not isinstance(actual_seated_by_class, (tuple, list))
            or len(actual_seated_by_class) != 2):
        return _result('SEATING_OBSERVATION_INVALID',
                       native_phase_job_assignment_verified=True)
    seated = tuple(_ids(group) for group in actual_seated_by_class)
    if (seated[0] is None or seated[1] is None
            or set(seated[0]) != set(class1)
            or set(seated[1]) != set(class2)):
        return _result('SEATING_NOT_VERIFIED',
                       native_phase_job_assignment_verified=True)
    return _result('LESSON_8_PLUS_8_SEATED_OBSERVED',
                   'verified only for explicitly supplied live observations',
                   native_phase_job_assignment_verified=True,
                   seating_verified=True)
