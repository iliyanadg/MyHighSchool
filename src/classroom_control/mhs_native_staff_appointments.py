"""School staffing through exact, pre-create EA guest invitations.

Stable EA jobs and situations are grounded in the verified High School Years
tuning.  The M53 registry itself does not grant anyone a native role.

For the EA Venue situation a second *explicitly invited* janitor is now
supported as a guarded beta.  The native situation exposes a shared janitor
job, not two different janitor jobs.  Its auto-invite=1 is not a proof of
an upper bound on explicit guest invitations; whether both people obtain
the job and work in-game still REQUIRES a real Sims 4 playtest.

The High School cafeteria is a TendObjectSituation. Multiple vendors for
one object have not been validated; this code must never insert a second
vendor into a single station or fake a second station/situation.
"""
ROLE_JOBS = {
    298052: (('teacher1', 277895), ('teacher2', 278963)),
    298096: (('principal', 278223), ('custodians', 290196)),
    278011: (('cafeteria', 278010),),
}
ALL_NATIVE_JOBS = frozenset(job for roles in ROLE_JOBS.values()
                            for _,job in roles)
MULTI_GUEST_NATIVE_ROLES = frozenset(('custodians',))


def _id(value):
    if type(value) not in (int,str):
        raise ValueError('STAFF_SIM_ID_INVALID')
    item=str(value)
    if not item.isdigit() or str(int(item))!=item or int(item)<1:
        raise ValueError('STAFF_SIM_ID_INVALID')
    return item


def load_native_staff_plan(roster, info_manager, human_species, adult_ages,
                           enrolled_ids=()):
    """Read a single, per-save/day roster snapshot; validate all staff IDs.

    'jobs' retains compatibility with one-Sim callers: it intentionally has
    no entry for a role with two selected Sims. 'job_groups' always stores all
    selected IDs per eligible native job, never silently drops the second
    employee. A failed role is refused *as a whole*, leaving EA's native
    fallback in charge and recording an explicit reason.
    """
    enrolled=set(str(sid) for sid in enrolled_ids)
    getter=getattr(info_manager,'get',None)
    if not callable(getter):
        raise ValueError('STAFF_SIM_INFO_MANAGER_UNAVAILABLE')
    ready={}
    groups={}
    blocked={}
    selected=set()
    for situation,roles in ROLE_JOBS.items():
        for role,job in roles:
            try:
                ids=tuple(_id(sid) for sid in roster.members(role))
            except Exception:
                blocked[role]='STAFF_SIM_ID_INVALID'
                continue
            if not ids:
                continue
            if len(set(ids))!=len(ids):
                blocked[role]='DUPLICATED_SELECTED_STAFF'
                continue
            if len(ids)>1 and (role not in MULTI_GUEST_NATIVE_ROLES or
                                len(ids)>2):
                blocked[role]='NATIVE_JOB_MULTI_CAPACITY_NOT_VERIFIED'
                continue
            if any(sid in selected or sid in enrolled for sid in ids):
                blocked[role]='STAFF_ALREADY_OCCUPIED_OR_STUDENT'
                continue
            try:
                infos=[getter(int(sid)) for sid in ids]
                if any(info is None or
                       getattr(info,'species',None)!=human_species or
                       getattr(info,'age',None) not in adult_ages
                       for info in infos):
                    blocked[role]='STAFF_NOT_ADULT_HUMAN'
                    continue
            except Exception:
                blocked[role]='STAFF_SIM_INFO_UNAVAILABLE'
                continue
            selected.update(ids)
            groups[job]=ids
            if len(ids)==1:
                ready[job]=ids[0]
    return {
        'jobs':ready,'job_groups':groups,'blocked':blocked,
        'situation_roles':ROLE_JOBS,'roster_read_only':True,
        'no_hidden_traits_modified':True,
        'two_custodians_explicit_invites_beta':any(
            len(ids)>1 for job,ids in groups.items() if job==290196),
        'staff_native_job_assignment_in_game_verified':False,
    }


def _requested_groups(situation_guid,plan):
    roles=ROLE_JOBS.get(situation_guid)
    if roles is None:
        return None
    jobs=plan.get('jobs',{})
    groups=plan.get('job_groups',{})
    wanted={}
    for role,job in roles:
        if job in groups:
            ids=tuple(groups[job])
        elif job in jobs:
            ids=(jobs[job],)
        else:
            continue
        # Unsupported multi-role invitations must not pass a handcrafted
        # invalid plan through this lower-level helper.
        if (not ids or
                (len(ids)>1 and (role not in MULTI_GUEST_NATIVE_ROLES
                                 or len(ids)>2))):
            raise ValueError('UNSUPPORTED_NATIVE_STAFF_JOB_MULTIPLICITY')
        normalized=tuple(_id(sid) for sid in ids)
        if len(set(normalized))!=len(normalized):
            raise ValueError('DUPLICATED_APPOINTED_SIM')
        wanted[job]=normalized
    return wanted


def project_native_staff_guests(old,situation_guid,plan,job_types,guest_cls,
                                invitation_purpose,excluded_ids=()):
    """Project exact selected guest IDs into one verified EA staff situation.

    The only multi-person case is two janitors in the SAME native Venue
    situation under job 290196. No second situation and no second vendor.
    Never modify 'old'. Unknown original guests or collisions with other
    original jobs cause a fail-closed return with the original EA call intact.
    """
    if situation_guid not in ROLE_JOBS:
        return None,{'applied':False,'reason':'NOT_NATIVE_STAFF_SITUATION'}
    try:
        wanted=_requested_groups(situation_guid,plan)
    except ValueError as exc:
        return None,{'applied':False,'reason':str(exc)}
    if not wanted:
        return None,{'applied':False,'reason':'NO_VERIFIED_APPOINTMENT',
                     'blocked':dict(plan.get('blocked',{}))}
    if old is None or not callable(getattr(old,'guest_info_gen',None)):
        return None,{'applied':False,'reason':'NATIVE_GUEST_LIST_UNAVAILABLE'}
    if any(job not in job_types or
           getattr(job_types[job],'guid64',None)!=job for job in wanted):
        return None,{'applied':False,'reason':'NATIVE_STAFF_JOB_TUNING_UNAVAILABLE'}
    factory=getattr(guest_cls,'construct_from_purpose',None)
    if not callable(factory):
        return None,{'applied':False,'reason':'NATIVE_GUEST_FACTORY_UNAVAILABLE'}
    try:
        original=tuple(old.guest_info_gen())
        seen=set()
        for guest in original:
            job=getattr(getattr(guest,'job_type',None),'guid64',None)
            if job in wanted:
                if job in seen:
                    return None,{'applied':False,
                                 'reason':'DUPLICATED_NATIVE_STAFF_JOB'}
                seen.add(job)
        required=tuple(sid for ids in wanted.values() for sid in ids)
        if len(set(required))!=len(required):
            return None,{'applied':False,'reason':'DUPLICATED_APPOINTED_SIM'}
        forbidden={str(sid) for sid in excluded_ids}
        if set(required)&forbidden:
            return None,{'applied':False,
                         'reason':'STAFF_STUDENT_OR_CORE_COLLISION'}
        retained_ids=set()
        for guest in original:
            job=getattr(getattr(guest,'job_type',None),'guid64',None)
            if job in wanted:
                continue
            try:
                retained_ids.add(_id(getattr(guest,'sim_id',None)))
            except ValueError:
                continue
        if set(required)&retained_ids:
            return None,{'applied':False,
                         'reason':'APPOINTED_SIM_ALREADY_HAS_OTHER_EA_JOB'}

        def exact_staff_guest(job,sid):
            guest=factory(int(sid),job_types[job],invitation_purpose)
            if (str(getattr(guest,'sim_id',None))!=sid or
                    getattr(getattr(guest,'job_type',None),'guid64',None)!=job or
                    getattr(guest,'accept_alternate_sim',None) is not False):
                raise ValueError('NATIVE_STAFF_GUEST_NOT_EXACT')
            return guest

        modified=type(old)(
            invite_only=True,host_sim_id=old.host_sim_id,
            filter_requesting_sim_id=old.filter_requesting_sim_id)
        appended=set()
        for guest in original:
            job=getattr(getattr(guest,'job_type',None),'guid64',None)
            if job in wanted:
                for sid in wanted[job]:
                    modified.add_guest_info(exact_staff_guest(job,sid))
                appended.add(job)
            else:
                clone=guest.clone_for_guest_list()
                if clone is None:
                    return None,{'applied':False,
                                 'reason':'NATIVE_GUEST_CLONE_FAILED'}
                modified.add_guest_info(clone)
        for _,job in ROLE_JOBS[situation_guid]:
            if job in wanted and job not in appended:
                for sid in wanted[job]:
                    modified.add_guest_info(exact_staff_guest(job,sid))

        actual=tuple(modified.guest_info_gen())
        for job,ids in wanted.items():
            obtained=tuple(str(g.sim_id) for g in actual
                          if getattr(getattr(g,'job_type',None),
                                     'guid64',None)==job)
            if obtained!=ids:
                return None,{'applied':False,
                             'reason':'NATIVE_STAFF_VERIFY_FAILED'}
        required_count=sum(len(ids) for ids in wanted.values())
        if len(actual)!=len(original)+required_count-len(seen):
            return None,{'applied':False,
                         'reason':'NATIVE_STAFF_GUEST_COUNT_CHANGED'}
        return modified,{
            'applied':True,'reason':'NATIVE_STAFF_EXACT_GUESTS',
            'situation_guid':situation_guid,
            'appointed':{job:(ids[0] if len(ids)==1 else list(ids))
                         for job,ids in wanted.items()},
            'two_custodians_explicit_invites_beta':
                len(wanted.get(290196,()))==2,
            'blocked':dict(plan.get('blocked',{})),'world_mutations':0,
        }
    except Exception as exc:
        return None,{'applied':False,
                     'reason':('NATIVE_STAFF_GUEST_NOT_EXACT'
                               if str(exc)=='NATIVE_STAFF_GUEST_NOT_EXACT'
                               else 'NATIVE_STAFF_PROJECT_'+type(exc).__name__)}
