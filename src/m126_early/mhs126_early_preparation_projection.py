"""M126: exact enrolled eight teen guest-list projection for EA PREP phase.

ONLY affects a selected original EA situation's student-job invitations,
not school Base/Core admission. No runtime imports, no tuning mutation.
Class1 WITH/NO trait are two ALTERNATE paths for one MHS classroom.
Never use a real student's name/location as a substitute for roster ID.

Preparation situations are EA-native; projecting student IDs does not
prove early arrival, pathing, assigned seats or permitted guest capacity.
"""
PREP_JOBS={293815:(1,277919),304701:(1,277919),
           297774:(2,277919)}
STAFF_JOBS=frozenset((277918,278224,277895,278963))


def _valid_ids(raw):
    if not isinstance(raw,(tuple,list)) or len(raw)!=8:
        return None
    ids=tuple(str(s) for s in raw)
    if (len(set(ids))!=8
            or any(not x.isdigit() or str(int(x))!=x or int(x)<=0
                   for x in ids)):
        return None
    return ids


def project_original_PREP_guests(situation_guid,original,classes,
                                   job_by_guid,guest_cls,purpose,
                                   already_projected_classes):
    """(new_guest_list,reason). Unrecognized input preserves vanilla EA.

    The caller may use this ONLY inside a previously verified original
    SituationManager.create_situation call for this live school zone.
    """
    if situation_guid not in PREP_JOBS:
        return None,'NOT_A_RECOGNISED_PREP'
    klass,student_job=PREP_JOBS[situation_guid]
    if klass in already_projected_classes:
        return None,'CLASS_ALREADY_ATTEMPTED'
    if (not isinstance(classes,(tuple,list)) or len(classes)!=2
            or _valid_ids(classes[0]) is None
            or _valid_ids(classes[1]) is None
            or set(map(str,classes[0]))&set(map(str,classes[1]))):
        return None,'REGISTRY_2X8_INVALID'
    if (original is None or not callable(getattr(original,'guest_info_gen',None))
            or not callable(getattr(original,'add_guest_info',None))
            or not callable(getattr(guest_cls,'construct_from_purpose',None))):
        return None,'EA_GUEST_LIST_API_UNVERIFIED'
    job=job_by_guid.get(student_job)
    if getattr(job,'guid64',None)!=student_job:
        return None,'EA_PREP_JOB_NOT_FOUND'
    chosen=tuple(str(x) for x in classes[klass-1])
    all_enrolled=set(map(str,classes[0]+classes[1]))
    try:
        guests=tuple(original.guest_info_gen())
        staff=[]
        seen_staff=set()
        for guest in guests:
            guid=getattr(getattr(guest,'job_type',None),'guid64',None)
            if guid==student_job:
                # Original students will be replaced in the *new* list.
                continue
            if guid not in STAFF_JOBS:
                return None,'UNRECOGNISED_EA_JOB_PRESERVE_VANILLA'
            sid=str(getattr(guest,'sim_id',None))
            if (not sid.isdigit() or sid in seen_staff
                    or sid in all_enrolled):
                return None,'STAFF_GUEST_AMBIGUOUS'
            seen_staff.add(sid)
            staff.append(guest)
        replacement=type(original)(
            invite_only=True,host_sim_id=original.host_sim_id,
            filter_requesting_sim_id=original.filter_requesting_sim_id)
        for guest in staff:
            clone=getattr(guest,'clone_for_guest_list',None)
            if not callable(clone):
                return None,'EA_STAFF_CLONE_UNAVAILABLE'
            replacement.add_guest_info(clone())
        for sid in chosen:
            guest=guest_cls.construct_from_purpose(int(sid),job,purpose)
            if (str(getattr(guest,'sim_id',None))!=sid
                    or getattr(getattr(guest,'job_type',None),'guid64',None)
                        !=student_job
                    or getattr(guest,'accept_alternate_sim',None) is not False):
                return None,'EA_STUDENT_GUEST_NOT_EXACT'
            replacement.add_guest_info(guest)
        actual=tuple(replacement.guest_info_gen())
        student_rows=tuple(str(g.sim_id) for g in actual
                           if getattr(getattr(g,'job_type',None),
                                      'guid64',None)==student_job)
        if (len(actual)!=len(staff)+8 or student_rows!=chosen):
            return None,'PROJECTED_EA_GUEST_LIST_MISMATCH'
        return replacement,'EIGHT_EXACT_REGISTERED_PREP_GUESTS_PROJECTED'
    except Exception as exc:
        return None,'EA_PREP_GUEST_PROJECTION_'+type(exc).__name__
