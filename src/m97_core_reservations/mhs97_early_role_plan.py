"""M97 — prepare five EA school core role reservations BEFORE NPC selection.

Pure Python 3.7, no EA imports or state mutation. This verifies an EXPLICIT
job->Sim choice from the user's save registry and EA SimFilter eligibility.
It does NOT assign roles, install a hook, modify EA's school, or guarantee
that EA will honor the reservations. EA integration is the next boundary.

The five student jobs and their filters were observed in the live Mac M94
report. Teacher jobs and Base Student must NOT be used as core roles.
"""
from mhs93_verified_jobs import VERIFIED_SPECS, CORE_STUDENT_JOBS, TEACHER_JOBS

CORE_JOB_ORDER=(278965,278966,278967,278968,303765)

def _sid(value):
    if type(value) not in (int,str):
        raise ValueError('Invalid Sim ID')
    s=str(value)
    if not s.isdigit() or int(s)<1 or s!=str(int(s)):
        raise ValueError('Invalid Sim ID')
    return s

def early_role_plan(class_ids, playable_ids, assignments,
                    ea_eligible_ids_by_job, filter_specs=None):
    """Validate exact 8+8 roster, 5 manually selected EA core roles.

    The caller must get ea_eligible_ids_by_job through the actual game's
    filter evaluation. Do not supply the entire roster as a fabricated
    eligibility result. False or incomplete eligibility blocks the plan.
    No automatic/random role selection is performed here.
    """
    def blocked(reason):
        return {'status':'BLOCKED','reason':reason,
                'role_binding_confirmed':False,'changes_to_ea':False}
    try:
        if not isinstance(class_ids,(tuple,list)) or len(class_ids)!=2:
            return blocked('exactly two classes required')
        groups=tuple(tuple(_sid(sid) for sid in group) for group in class_ids)
        if any(len(group)!=8 for group in groups):
            return blocked('each class must have eight students')
        everyone=groups[0]+groups[1]
        if len(set(everyone))!=16:
            return blocked('sixteen unique students required')
        played=tuple(_sid(sid) for sid in playable_ids)
        if len(set(played))!=len(played) or not set(played)<=set(everyone):
            return blocked('playable students must be enrolled and unique')
        if (not isinstance(assignments,dict)
                or set(assignments)!=CORE_STUDENT_JOBS
                or any(type(job) is not int for job in assignments)):
            return blocked('all five EA core student roles must be assigned')
        if filter_specs is None:
            filter_specs=VERIFIED_SPECS
        if (not isinstance(filter_specs,dict) or
                set(filter_specs)!=set(VERIFIED_SPECS) or
                any(tuple(filter_specs[j])!=VERIFIED_SPECS[j]
                    for j in VERIFIED_SPECS)):
            return blocked('EA current-school job filters unverified')
        core=tuple(_sid(assignments[job]) for job in CORE_JOB_ORDER)
        if len(set(core))!=5:
            return blocked('one student cannot hold two special roles')
        if not set(core)<=set(everyone):
            return blocked('one core student is not enrolled')
        if set(core)&set(played):
            return blocked('EA NPC core student cannot be a playable teen')
        if (not isinstance(ea_eligible_ids_by_job,dict) or
                set(ea_eligible_ids_by_job)!=CORE_STUDENT_JOBS):
            return blocked('all five actual EA filters must be evaluated')
        for job in CORE_JOB_ORDER:
            eligible=ea_eligible_ids_by_job[job]
            if not isinstance(eligible,(tuple,list,set,frozenset)):
                return blocked('invalid EA role eligibility')
            matching=set(_sid(sid) for sid in eligible)
            if assignments[job] is None or str(assignments[job]) not in matching:
                return blocked('selected Sim failed EA job filter '+str(job))
        ordinary=tuple(sid for sid in everyone
                       if sid not in set(played) and sid not in set(core))
        if len(ordinary)+len(played)+len(core)!=16:
            return blocked('student headcount mismatch')
        return {'status':'EARLY_ROLE_PLAN_VALIDATED_NOT_EA_BOUND',
                'changes_to_ea':False,
                'classes':groups,'all_16':everyone,
                'playable':played,'core':core,
                'normal_npcs':ordinary,
                'base_invites_needed':len(ordinary),
                'role_reservations':tuple((job,str(assignments[job]))
                                          for job in CORE_JOB_ORDER),
                'role_binding_confirmed':False,
                'core_filter_metadata_verified':True,
                'role_eligibility_verified':True}
    except (ValueError,TypeError,KeyError):
        return blocked('invalid or incomplete core role selection')

def validate_live_binding(plan, bound_job_ids, school_verified=False,
                          save_verified=False, day_verified=False):
    """Read-only validation of actual EA job->Sim binding.

    This function is intentionally NOT a magic activation flag. Call only
    after EA has actually bound all five student jobs and the verified
    school/session context is known. It is too late to use this snapshot
    as proof of an *early* reservation for the current day.
    """
    if (not isinstance(plan,dict) or
            plan.get('status')!='EARLY_ROLE_PLAN_VALIDATED_NOT_EA_BOUND' or
            not school_verified or not save_verified or not day_verified):
        return False
    if not isinstance(bound_job_ids,dict) or set(bound_job_ids)!=CORE_STUDENT_JOBS:
        return False
    try:
        actual=tuple((job,_sid(bound_job_ids[job])) for job in CORE_JOB_ORDER)
    except (ValueError,TypeError):
        return False
    return actual==tuple(plan.get('role_reservations',()))
