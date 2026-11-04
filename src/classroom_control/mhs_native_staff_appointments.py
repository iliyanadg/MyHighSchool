"""Native EA staffing appointments with explicit, fail-closed guest IDs.

Only a *verified* situation and native EA job can be appointed.  The saved
M53 registry is not an EA job.  This projection intentionally does not give
any adult a hidden trait, does not alter an existing school situation, and
never creates an extra vendor or janitor situation.

Use the projection BEFORE the original SituationManager.create_situation.
A job for which the live EA capacity (more than one) is not verified stays
native and is reported as unsupported; do not pretend its extra workers
are assigned because they exist in a registry.
"""
ROLE_JOBS = {
    298052: (('teacher1', 277895), ('teacher2', 278963)),
    298096: (('principal', 278223), ('custodians', 290196)),
    278011: (('cafeteria', 278010),),
}
ALL_NATIVE_JOBS = frozenset(job for roles in ROLE_JOBS.values()
                            for _,job in roles)


def _id(value):
    if type(value) not in (int,str):
        raise ValueError('STAFF_SIM_ID_INVALID')
    item=str(value)
    if not item.isdigit() or str(int(item))!=item or int(item)<1:
        raise ValueError('STAFF_SIM_ID_INVALID')
    return item


def load_native_staff_plan(roster, info_manager, human_species, adult_ages,
                           enrolled_ids=()):
    """Freeze the staff registry at home. Reject pets, teens and student IDs.

    Existing saved appointments are immutable for the running school day.
    Return separate *eligible* and *blocked* rows per role.  A second
    custodian/vendor has no verified native EA job capacity: never silently
    choose only one of them.
    """
    enrolled=set(str(sid) for sid in enrolled_ids)
    getter=getattr(info_manager,'get',None)
    if not callable(getter):
        raise ValueError('STAFF_SIM_INFO_MANAGER_UNAVAILABLE')
    ready={}
    blocked={}
    all_selected=set()
    for situation,roles in ROLE_JOBS.items():
        for role,job in roles:
            ids=tuple(_id(sid) for sid in roster.members(role))
            if len(ids)>1:
                blocked[role]='NATIVE_JOB_MULTI_CAPACITY_NOT_VERIFIED'
                continue
            if not ids:
                continue
            sid=ids[0]
            if sid in all_selected or sid in enrolled:
                blocked[role]='STAFF_ALREADY_OCCUPIED_OR_STUDENT'
                continue
            all_selected.add(sid)
            try:
                info=getter(int(sid))
                if (info is None or
                        getattr(info,'species',None)!=human_species or
                        getattr(info,'age',None) not in adult_ages):
                    blocked[role]='STAFF_NOT_ADULT_HUMAN'
                    continue
            except Exception:
                blocked[role]='STAFF_SIM_INFO_UNAVAILABLE'
                continue
            ready[job]=sid
    return {'jobs':ready,'blocked':blocked,
            'situation_roles':ROLE_JOBS,
            'roster_read_only':True,
            'no_hidden_traits_modified':True}


def project_native_staff_guests(old,situation_guid,plan,job_types,guest_cls,
                                invitation_purpose,excluded_ids=()):
    """Replace only an EA staff job with the user's exact appointed Sim.

    Preserve every other EA guest by cloning it.  Existing EA Core student
    guests can be projected by the student controller first, then passed here.
    The exact EA jobs cannot be inferred from a name or list position.
    A failed projection leaves the original list unchanged.
    """
    roles=ROLE_JOBS.get(situation_guid)
    if roles is None:
        return None,{'applied':False,'reason':'NOT_NATIVE_STAFF_SITUATION'}
    wanted={job:plan['jobs'][job] for _,job in roles if job in plan['jobs']}
    if not wanted:
        return None,{'applied':False,'reason':'NO_VERIFIED_APPOINTMENT',
                     'blocked':dict(plan.get('blocked',{}))}
    if old is None or not callable(getattr(old,'guest_info_gen',None)):
        return None,{'applied':False,'reason':'NATIVE_GUEST_LIST_UNAVAILABLE'}
    if any(job not in job_types or
           getattr(job_types[job],'guid64',None)!=job for job in wanted):
        return None,{'applied':False,'reason':'NATIVE_STAFF_JOB_TUNING_UNAVAILABLE'}
    if not callable(getattr(guest_cls,'construct_from_purpose',None)):
        return None,{'applied':False,'reason':'NATIVE_GUEST_FACTORY_UNAVAILABLE'}
    try:
        original=tuple(old.guest_info_gen())
        # Refuse an unexpectedly duplicated native role instead of silently
        # deleting somebody else's job or corrupting the original guest list.
        seen=set()
        for guest in original:
            job=getattr(getattr(guest,'job_type',None),'guid64',None)
            if job in wanted:
                if job in seen:
                    return None,{'applied':False,
                                 'reason':'DUPLICATED_NATIVE_STAFF_JOB'}
                seen.add(job)
        forbidden={str(sid) for sid in excluded_ids}
        if set(wanted.values()) & forbidden:
            return None,{'applied':False,'reason':'STAFF_STUDENT_OR_CORE_COLLISION'}
        modified=type(old)(
            invite_only=True,host_sim_id=old.host_sim_id,
            filter_requesting_sim_id=old.filter_requesting_sim_id)
        appended=set()
        for guest in original:
            job=getattr(getattr(guest,'job_type',None),'guid64',None)
            if job in wanted:
                appointed=guest_cls.construct_from_purpose(
                    int(wanted[job]),job_types[job],invitation_purpose)
                if (str(getattr(appointed,'sim_id',None))!=wanted[job]
                        or getattr(getattr(appointed,'job_type',None),'guid64',None)!=job
                        or getattr(appointed,'accept_alternate_sim',None) is not False):
                    return None,{'applied':False,
                                 'reason':'NATIVE_STAFF_GUEST_NOT_EXACT'}
                modified.add_guest_info(appointed)
                appended.add(job)
            else:
                clone=guest.clone_for_guest_list()
                if clone is None:
                    return None,{'applied':False,'reason':'NATIVE_GUEST_CLONE_FAILED'}
                modified.add_guest_info(clone)
        for _,job in roles:
            if job not in wanted or job in appended:
                continue
            appointed=guest_cls.construct_from_purpose(
                int(wanted[job]),job_types[job],invitation_purpose)
            if (str(getattr(appointed,'sim_id',None))!=wanted[job]
                    or getattr(getattr(appointed,'job_type',None),'guid64',None)!=job
                    or getattr(appointed,'accept_alternate_sim',None) is not False):
                return None,{'applied':False,'reason':'NATIVE_STAFF_GUEST_NOT_EXACT'}
            modified.add_guest_info(appointed)
        actual=tuple(modified.guest_info_gen())
        for job,sid in wanted.items():
            matched=[g for g in actual
                if getattr(getattr(g,'job_type',None),'guid64',None)==job]
            if len(matched)!=1 or str(matched[0].sim_id)!=sid:
                return None,{'applied':False,'reason':'NATIVE_STAFF_VERIFY_FAILED'}
        if len(actual)!=len(original)+len(wanted)-len(seen):
            return None,{'applied':False,'reason':'NATIVE_STAFF_GUEST_COUNT_CHANGED'}
        return modified,{'applied':True,'reason':'NATIVE_STAFF_EXACT_GUESTS',
                         'situation_guid':situation_guid,
                         'appointed':dict(wanted),
                         'blocked':dict(plan.get('blocked',{})),
                         'world_mutations':0}
    except Exception as exc:
        return None,{'applied':False,'reason':'NATIVE_STAFF_PROJECT_'+type(exc).__name__}
