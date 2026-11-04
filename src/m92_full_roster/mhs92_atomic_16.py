"""M92: ONE atomic 8+8 enrollment plan for the whole EA school day.

No partial cohort is ever approved. This is a pure contract for the future
runtime adapter: ALL 16 registered teens, including playable/core roles, must
be accounted for before any mutation to EA school selection.
"""
# Verified against user-exported EA 298052 (current patch):
# teacher jobs 277895,278963 are STAFF, never students.
# The five student roles are possible jobs, NOT proof they are all spawned.
CORE_STUDENT_JOB_IDS=frozenset((278965,278966,278967,278968,303765))
CORE_TEACHER_JOB_IDS=frozenset((277895,278963))


def core_occupants(core_role_jobs):
    """Validate observed EA CoreClassNPCs *job -> registered Sim ID*.

    The caller must read live EA membership. Missing roles are fine; invented
    occupants or repeated Sim IDs are forbidden. None means no reliable data.
    """
    if core_role_jobs is None or not isinstance(core_role_jobs,dict):
        raise ValueError('EA CoreClassNPCs job membership not verified')
    students=[]
    for job,sid in core_role_jobs.items():
        if type(job) is not int or job not in CORE_STUDENT_JOB_IDS:
            raise ValueError('unknown core school student job')
        if isinstance(sid,bool) or not str(sid).isdigit() or int(sid)<=0:
            raise ValueError('invalid core role student')
        students.append(str(int(sid)))
    if len(set(students))!=len(students):
        raise ValueError('same student assigned to multiple core jobs')
    return frozenset(students)


def full_cohort_plan(manifest, eligible_npc_ids, playable_present_ids,
                     core_role_ids, base_job_slots, phase1_slots,
                     phase2_slots, zone_cap_free_or_reserved,
                     ea_filters_verified=False, core_role_jobs=None):
    """Fail closed unless every member of the SAME 16-student cohort is counted.

    core_role_jobs: optional observed EA mapping. Runtime integration must pass
    it: this function never guesses how many of EA's five roles are occupied.
    The capacity figure is a validated zone budget, NOT a raw tuning max.
    """
    def blocked(reason):
        return {'status':'BLOCKED','reason':reason,'changes_to_ea':False}
    if manifest is None or len(manifest.class_ids)!=2:
        return blocked('two classes required')
    groups=tuple(tuple(str(s) for s in group) for group in manifest.class_ids)
    if any(len(g)!=8 for g in groups):
        return blocked('each class must contain exactly eight')
    everyone=groups[0]+groups[1]
    if len(set(everyone))!=16 or set(everyone)!=set(manifest.all_student_ids):
        return blocked('16 distinct students must match registry')
    if not ea_filters_verified:
        return blocked('EA eligibility not verified')

    playable=set(str(x) for x in playable_present_ids)
    core=set(str(x) for x in core_role_ids)
    eligible=set(str(x) for x in eligible_npc_ids)
    everyone_set=set(everyone)
    if core_role_jobs is not None:
        try:
            actual_core=core_occupants(core_role_jobs)
        except ValueError as exc:
            return blocked(str(exc))
        if core!=actual_core:
            return blocked('actual EA core occupants do not match roster plan')
    if not playable.issubset(everyone_set) or not core.issubset(everyone_set):
        return blocked('unregistered playable or special-role student')
    if playable & core:
        return blocked('playable and core role conflict')
    if set(manifest.active_household_teens).intersection(everyone_set)!=playable:
        return blocked('registered playable students not accounted for on lot')
    normal=tuple(x for x in everyone if x not in playable and x not in core)
    if not set(normal).issubset(eligible):
        return blocked('one or more registered NPCs not eligible for Base EA job')
    values=(base_job_slots,phase1_slots,phase2_slots,zone_cap_free_or_reserved)
    if any(type(v) is not int or v<0 for v in values):
        return blocked('capacity unknown')
    if base_job_slots<len(normal):
        return blocked('too few EA Base student invitations')
    if phase1_slots<8 or phase2_slots<8:
        return blocked('insufficient simultaneous classroom seats')
    if zone_cap_free_or_reserved<16:
        return blocked('16 physical school occupants not supported')
    return {'status':'READY_FOR_ADAPTER','changes_to_ea':False,
            'classes':groups,'all_16':everyone,'normal_npcs':normal,
            'base_invites_needed':len(normal),
            'playable_count':len(playable),'core_count':len(core),
            'playable':tuple(x for x in everyone if x in playable),
            'core':tuple(x for x in everyone if x in core),
            'core_jobs_verified':core_role_jobs is not None}
