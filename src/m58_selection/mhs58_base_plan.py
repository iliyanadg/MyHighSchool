"""M58 pure planner for EA-owned high-school base situations.

No EA imports, no Sims mutation, no forced spawn. Validated against the
user's 1.129.39.1230 EP12 WeeklySchedule and SituationJob exports.
This is an offline feasibility gate, NOT an installed selection controller.
"""
BASE_STUDENT_SITUATION = 277733
BASE_STUDENT_JOB = 277894
CORE_SITUATION = 298052
VENUE_SITUATION = 298096
BASE_STUDENT_SITUATION_COUNT = 6
BASE_STUDENT_JOB_SLOTS = 1
BASE_STUDENT_CAPACITY = BASE_STUDENT_SITUATION_COUNT * BASE_STUDENT_JOB_SLOTS
SPECIAL_JOBS = {
    'cheer':278965,'chess':278966,'football':278967,
    'computer':278968,'mean':303765,
}
STAFF_JOBS = {
    'teacher1':277895,'teacher2':278963,
    'principal':278223,'janitor':290196,
}


class M58PlanError(ValueError):
    pass


def _ids(seq):
    result = []
    for raw in seq:
        if isinstance(raw,bool) or not isinstance(raw,(str,int)):
            raise M58PlanError('invalid Sim ID')
        sid = str(raw)
        if not sid.isdigit() or int(sid)<1 or str(int(sid))!=sid:
            raise M58PlanError('invalid Sim ID')
        result.append(sid)
    if len(set(result))!=len(result):
        raise M58PlanError('duplicated Sim IDs')
    return tuple(result)


def plan_base_roster(manifest, core_roles=None, unavailable=()):
    """Classify slots, never silently fabricate NPCs or claim attendance.

    core_roles is a mapping of *verified* role->SimID. Unassigned core roles
    remain EA-owned; they MUST NOT be counted as MHS occupied seats.
    unavailable: Sims determined ineligible for the EA base job at runtime
    (e.g. special NPC blacklist traits). The pure planner never guesses.
    """
    core_roles = core_roles or {}
    if any(role not in SPECIAL_JOBS for role in core_roles):
        raise M58PlanError('unrecognized EA core role')
    core = _ids(core_roles.values())
    if len(core)!=len(core_roles):
        raise M58PlanError('duplicate core role Sim')
    cohort = _ids(s for klass in manifest.class_ids for s in klass)
    if len(cohort)!=len(manifest.all_student_ids):
        raise M58PlanError('manifest mismatch')
    if not set(core).issubset(set(cohort)):
        raise M58PlanError('core Sim not enrolled')
    playable = set(manifest.active_household_teens)
    if set(core)&playable:
        raise M58PlanError('cannot bind active playable to NPC core job')
    ineligible = set(_ids(unavailable))
    if not ineligible.issubset(set(cohort)):
        raise M58PlanError('unavailable Sim outside roster')
    npc = tuple(s for s in cohort if s not in playable and s not in core
                and s not in ineligible)
    overflow = tuple(npc[BASE_STUDENT_CAPACITY:])
    slots = tuple(npc[:BASE_STUDENT_CAPACITY])
    return {
        'base_situation':BASE_STUDENT_SITUATION,
        'base_job':BASE_STUDENT_JOB,
        'base_guest_ids':slots,
        'overflow_ids':overflow,
        'core_roles':dict(core_roles),
        'playable_ids':tuple(s for s in cohort if s in playable),
        'unavailable_ids':tuple(s for s in cohort if s in ineligible),
        'unassigned_core_slots':tuple(
            x for x in SPECIAL_JOBS if x not in core_roles),
        'requested_students':len(cohort),
        'vanilla_base_capacity':BASE_STUDENT_CAPACITY,
        'requires_capacity_change':bool(overflow),
    }
