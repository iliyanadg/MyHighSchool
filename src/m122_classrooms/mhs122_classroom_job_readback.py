"""M122 live original-EA lesson membership versus two exact MHS rosters.

Read only; retains the M121 working thirteen-NPC admission separately.
The EA Class 1 has two alternative native paths (WithTrait/NoTrait), which
are the SAME intended MHS class; Class 2 has a separate original EA path.
A Base/Core job is school admission, never a classroom lesson job.
Original source: real M110 Mac phase observation and M111 readback.

No seat checks, no job/tuning changes, no guessed post-Bouncer success.
"""
# Original EA lesson Situation GUID -> MHS class, native student Job GUID
LESSON_SITUATIONS={
    304565:(1,277919), 304703:(1,277919),
    304567:(2,280777),
}
PREP_SITUATIONS={
    293815:(1,277919), 304701:(1,277919),
    297774:(2,277919),
}
MAX_SITUATIONS=64


def _guid(x):
    if x is None:
        return None
    for obj in (x,getattr(x,'tuned_class',None),type(x)):
        if obj is None:
            continue
        value=getattr(obj,'guid64',None)
        if type(value) is int and value>0:
            return value
    return None


def _ids(raw):
    if not isinstance(raw,(tuple,list)) or len(raw)!=2:
        return None
    groups=[]
    for group in raw:
        if not isinstance(group,(tuple,list)) or len(group)!=8:
            return None
        ids=tuple(str(x) for x in group)
        if (any(not x.isdigit() or int(x)<=0 or str(int(x))!=x
                for x in ids) or len(set(ids))!=8):
            return None
        groups.append(ids)
    if len(set(groups[0]+groups[1]))!=16:
        return None
    return tuple(groups)


def school_classroom_snapshot(classes, playable, sim_info_manager,
                              situation_manager, age, species, phase):
    """Read actual EA situations for exact 2x8 register: never assign Sims."""
    report={
        'kind':'M122_EA_TWO_CLASSROOM_NATIVE_JOB_SNAPSHOT',
        'status':'BLOCKED',
        'phase':phase,
        'selected_students':16,
        'playables_from_register_not_proof':3,
        'original_ea_lessons_modified':False,
        'all_playable_instances_verified':False,
        'exact_two_class_jobs_verified':False,
        'two_classroom_seating_verified':False,
        'full_school_day_verified':False,
    }
    classes=_ids(classes)
    pids=tuple(str(x) for x in playable) if isinstance(playable,(tuple,list)) else ()
    if (classes is None or len(pids)!=3 or len(set(pids))!=3
            or not set(pids)<=set(classes[0]+classes[1])
            or phase not in ('lesson','prepare')):
        report['status']='ROSTER_OR_PHASE_INVALID'
        return report
    mgr_get=getattr(sim_info_manager,'get',None)
    situations_for=getattr(situation_manager,'get_situations_sim_is_in',None)
    if not callable(mgr_get) or not callable(situations_for):
        report['status']='EA_NATIVE_MEMBERSHIP_API_UNAVAILABLE'
        return report
    mapping=(LESSON_SITUATIONS if phase=='lesson' else PREP_SITUATIONS)
    observed={1:set(),2:set()}
    wrong_jobs=[]
    membership_rows=[]
    errors=[]
    instanced=set()
    for sid in classes[0]+classes[1]:
        info=mgr_get(int(sid))
        if (info is None or getattr(info,'age',None)!=age
                or getattr(info,'species',None)!=species):
            errors.append((sid,'NOT_HUMAN_TEEN'))
            continue
        try:
            sim=info.get_sim_instance()
        except Exception:
            errors.append((sid,'INSTANCE_LOOKUP_FAILED'))
            continue
        if sim is None:
            continue
        instanced.add(sid)
        try:
            situations=tuple(situations_for(sim))
            if len(situations)>MAX_SITUATIONS:
                raise ValueError('TOO_MANY_SITUATIONS')
        except Exception:
            errors.append((sid,'EA_SITUATION_LIST_FAILED'))
            continue
        for situation in situations:
            guid=_guid(situation)
            if guid not in mapping:
                continue
            klass,required_job=mapping[guid]
            reader=getattr(situation,'get_current_job_for_sim',None)
            if not callable(reader):
                errors.append((sid,'JOB_READER_MISSING'))
                continue
            try:
                job=_guid(reader(sim))
            except Exception:
                errors.append((sid,'JOB_READER_FAILED'))
                continue
            membership_rows.append((sid,guid,klass,job))
            if job==required_job:
                observed[klass].add(sid)
            else:
                wrong_jobs.append((sid,guid,job,required_job))
    wrong_class=tuple((sid,klass) for klass in (1,2)
                      for sid in sorted(observed[klass],key=int)
                      if sid not in classes[klass-1])
    cross=tuple(sorted(observed[1]&observed[2],key=int))
    missing={klass:tuple(sid for sid in classes[klass-1]
                         if sid not in observed[klass])
             for klass in (1,2)}
    absent=tuple(sid for sid in classes[0]+classes[1] if sid not in instanced)
    available_playables=tuple(x for x in pids if x in instanced)
    report.update(
        status='NATIVE_LESSON_READBACK_RECORDED',
        registered_class1=classes[0],
        registered_class2=classes[1],
        playable_registered_ids=pids,
        playable_instanced_ids=available_playables,
        enrolled_instanced_count=len(instanced),
        missing_instanced_students=absent,
        native_class1_job_count=len(observed[1]),
        native_class2_job_count=len(observed[2]),
        native_class1_student_ids=tuple(sorted(observed[1],key=int)),
        native_class2_student_ids=tuple(sorted(observed[2],key=int)),
        missing_class1_job_ids=missing[1],
        missing_class2_job_ids=missing[2],
        wrong_class_memberships=wrong_class,
        cross_class_memberships=cross,
        wrong_native_job_guids=tuple(wrong_jobs),
        api_errors=tuple(errors),
        observed_native_lesson_rows=tuple(membership_rows),
        # Instances come from EA SimInfo, not class enrollment, but
        # an instance alone does not certify exact lot coordinates.
        all_playable_instances_verified=(len(available_playables)==3),
    )
    all_match=(len(instanced)==16
               and not errors and not wrong_jobs and not wrong_class
               and not cross and not missing[1] and not missing[2])
    if errors:
        report['status']='NATIVE_EA_CLASS_JOB_READ_INCOMPLETE'
    elif all_match:
        report['status']='TWO_NATIVE_CLASS_JOB_SETS_MATCH_OBSERVED'
        report['exact_two_class_jobs_verified']=True
    else:
        report['status']='NATIVE_CLASSROOM_JOB_MEMBERSHIPS_DIFFER'
    return report
