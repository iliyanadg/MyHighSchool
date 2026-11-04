"""M146: conservative native class-preparation policy and school-day evidence.

Observed in M145d: class2 playable students have native preparation situation
297774/job277919 at 09:37 but remain idle until EA Class_Start push at 10:00.
Class1 playable already follows native EA flow around 09:37.
Pre-lesson requests here operate ONLY for class2 playables, AFTER EA provides
the native class2 preparation role. They use EA 276774 on the exact EA state
Class2 board. Never move an NPC, bypass a test, force a posture, change a
schedule, or alter real truancy/detention gameplay.
"""
PREP_CLASS2_SITUATION = 297774
PREP_CLASS2_JOB = 277919
PROTECTED_ACTION_TOKENS = (
    'HighSchool_Active_Whiteboard_', 'HighSchool_Active_UseBook_Class',
    'HighSchool_Active_CreateBook_Class', 'HighSchool_Active_WriteOnBook',
    'HighSchool_Active_Listen_', 'toilet', 'Toilet', 'Shower', 'Sleep',
    'Social_HighSchool_Active', 'Detention', 'CatchTruant',
)
TRUANCY_ACTION_TOKENS = ('CatchTruant', 'TryToAvoidDetention', 'Detention')


def minute_of_day(clock):
    if not isinstance(clock, dict):
        return None
    h, m = clock.get('hour'), clock.get('minute')
    if type(h) is not int or type(m) is not int:
        return None
    if not (0 <= h < 24 and 0 <= m < 60):
        return None
    return h * 60 + m


def preparation_period(clock):
    """Native GetReady for Class starts at 09:30 and 13:30.

    Hold a bounded gap after start for EA to attach preparation roles.
    Never touch lunch, class end at 14:55 or anything after 15:00.
    """
    m=minute_of_day(clock)
    if m is None:
        return None
    if 9*60+35 <= m <= 9*60+49:
        return 'morning'
    if 13*60+35 <= m <= 13*60+49:
        return 'afternoon'
    return None


def can_early_request(klass, native_jobs, clock, running_name,
                      already_attempted):
    period=preparation_period(clock)
    if period is None:
        return False,'OUTSIDE_EA_PREPARATION'
    if klass != 2:
        return False,'CLASS1_NATIVE_PREPARATION_UNCHANGED'
    if already_attempted:
        return False,'PRECLASS_ALREADY_REQUESTED'
    if running_name and any(token in str(running_name)
                            for token in PROTECTED_ACTION_TOKENS):
        return False,'EXISTING_OR_PROTECTED_ACTION'
    if not isinstance(native_jobs,(list,tuple)):
        return False,'NATIVE_PREPARATION_ROLE_UNAVAILABLE'
    role_found=any(
        isinstance(r,dict) and
        r.get('situation_guid')==PREP_CLASS2_SITUATION and
        r.get('job_guid')==PREP_CLASS2_JOB and
        r.get('is_preparation') is True
        for r in native_jobs)
    if not role_found:
        return False,'EA_CLASS2_PREPARATION_ROLE_MISSING'
    return True,'CLASS2_EA_PREPARATION_VERIFIED'


def validate_anchors(boards):
    """Do not invent classroom locations without exactly two native boards."""
    try:
        ids=set()
        anchors={}
        for klass in (1,2):
            if klass not in boards or len(boards[klass])!=1:
                return None,'REQUIRE_ONE_BOARD_PER_CLASS'
            obj=boards[klass][0]
            ident=getattr(obj,'id',None)
            pos=getattr(obj,'position',None)
            if ident is None or pos is None:
                return None,'BOARD_WITHOUT_POSITION'
            if str(ident) in ids:
                return None,'BOARD_IDS_NOT_EXCLUSIVE'
            ids.add(str(ident))
            coords={axis:round(float(getattr(pos,axis)),3)
                    for axis in ('x','y','z')}
            anchors[klass]={'id':str(ident),'position':coords}
        return anchors,'TWO_DISTINCT_EA_CLASSROOM_ANCHORS'
    except (AttributeError,TypeError,ValueError,OverflowError):
        return None,'BOARD_POSITION_NOT_READABLE'


def truant_evidence(samples):
    """Classroom absence is not necessarily failed admission.

    An observed EA principal/detention incident is protected gameplay; the
    controller must never silently force this student into class.
    """
    affected={}
    for record in samples:
        clock=record.get('clock') or {}
        period=minute_of_day(clock)
        if period is None or not (9*60+30 <= period < 15*60):
            continue
        for student in record.get('students') or ():
            if student.get('selectable') is not False:
                continue
            name=str(student.get('running_action') or '')
            if not any(token in name for token in TRUANCY_ACTION_TOKENS):
                continue
            sid=str(student.get('sim_id'))
            entry=affected.setdefault(sid,{
                'class':student.get('registered_class'),
                'first_observed_at':clock.get('repr'),
                'last_observed_at':clock.get('repr'),
                'incident_actions':[]})
            entry['last_observed_at']=clock.get('repr')
            action=name.split('.')[-1]
            if action not in entry['incident_actions']:
                entry['incident_actions'].append(action)
    return {'students':affected,
            'observed_incident_not_proof_of_official_detention':True,
            'npc_disruptions_not_overridden_by_mhs':True}
