"""M144 native EA Class2 NPC attendance-route adapter for played teens.

Never changes EA test hierarchy. A same-day Class2 NPC must be *observed*
running the actual tuned EA super_HighSchool_Active_AttendClass_NPC on the
verified Class2 board before attempting the same native interaction on a
registered, selectable class-two teen. Native EA test must pass first.
The NPC source is not copied to any Sim outside MHS's 8-seat Class2 roster.
"""
KNOWN_EA_CLASS_NPC_GUID=297779
CLASS_NPC_NAME='super_HighSchool_Active_AttendClass_NPC'
PREP_JOB=(297774,277919)
CLASS_JOB=(304567,280777)
CLASS_RUNNING=('HighSchool_Active_Whiteboard_Attend_',
               'HighSchool_Active_UseBook_Class',
               'HighSchool_Active_AttendClass_NPC',
               'HighSchool_Active_CreateBook_Class',
               'HighSchool_Active_WriteOnBook',
               'HighSchool_Active_Listen_')
PROTECTED=('toilet','Toilet','Shower','Sleep')


def classify_phase(clock):
    if not isinstance(clock,dict):
        return None
    h,m=clock.get('hour'),clock.get('minute')
    if type(h) is not int or type(m) is not int:
        return None
    if (h==9 or h==13) and 35<=m<=58:
        return 'preparation'
    if (h==10 or h==14) and 7<=m<=24:
        return 'lesson'
    return None


def valid_job_for_phase(jobs,phase):
    pair=PREP_JOB if phase=='preparation' else CLASS_JOB
    return any((j.get('situation_guid'),j.get('job_guid'))==pair
               for j in (jobs or ()) if isinstance(j,dict))


def can_attempt_class2(clock,row,job_rows,already_queued,attempted,
                       running_name,board_is_class2=True):
    if not isinstance(row,dict) or row.get('registered_class')!=2:
        return False,'NOT_REGISTERED_CLASS2_PLAYABLE'
    if not row.get('sim_id') or not row.get('sim_info'):
        return False,'SIM_INFO_NOT_AVAILABLE'
    if not board_is_class2:
        return False,'CLASS2_BOARD_NOT_VERIFIED'
    phase=classify_phase(clock)
    if phase is None:
        return False,'OUTSIDE_EA_CLASS_WINDOWS'
    if not valid_job_for_phase(job_rows,phase):
        return False,'EA_CLASS2_SITUATION_JOB_MISSING'
    if (phase, str(row['sim_id'])) in attempted:
        return False,'CLASS2_NATIVE_ATTEMPT_ALREADY_USED'
    if any(x in str(running_name or '') for x in CLASS_RUNNING):
        return False,'ALREADY_IN_REAL_CLASS_ACTION'
    if any(x in str(running_name or '') for x in PROTECTED):
        return False,'DO_NOT_INTERRUPT_PROTECTED_ACTION'
    if already_queued and phase=='preparation':
        return False,'PREPARATION_ALREADY_ENTERED'
    return True,'CLASS2_NATIVE_EA_TEST_REQUIRED'


def is_real_class2_npc_source(interaction,target,board_id):
    if interaction is None or target is None:
        return False
    native=type(interaction)
    return (getattr(native,'__name__',None)==CLASS_NPC_NAME
            and getattr(native,'guid64',None)==KNOWN_EA_CLASS_NPC_GUID
            and callable(getattr(native,'test',None))
            and str(getattr(target,'id',None))==str(board_id))


def source_from_registered_class2_npcs(npc_rows,expected_board_id):
    """Return one unique EA tuning, taken from an NPC already using Class 2.

    This is not sourced from the playable Class 1 Whiteboard_Attend affordance,
    which EA hardcodes to the Class1_True object state.
    """
    found={}
    for row in npc_rows:
        if row.get('selectable') is not False or row.get('registered_class')!=2:
            continue
        info=row.get('sim_info')
        if info is None:
            continue
        try:
            sim=info.get_sim_instance()
            running=getattr(getattr(sim,'queue',None),'running',None)
            target=getattr(running,'target',None)
            if is_real_class2_npc_source(running,target,expected_board_id):
                cls=type(running)
                found[cls.guid64]=cls
        except Exception:
            pass
    if len(found)!=1:
        return None,'NO_UNIQUE_EA_CLASS2_NPC_SOURCE'
    return next(iter(found.values())),'OBSERVED_EA_NATIVE_CLASS2_NPC_ATTEND'


def compact_native_result(value):
    try: return str(value)[:360]
    except Exception: return 'NATIVE_RESULT_UNPRINTABLE'
