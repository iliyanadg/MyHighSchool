"""M124: real EA student lesson job vs role-state and interaction progress.

READ ONLY. BaseSituation.get_current_role_state_for_sim and
get_current_role_state_instance_for_sim come from the original EA
base_situation.py provided by the user (2026-11-02). Job membership
alone does NOT prove a teen is following or sitting in class.

Describe interactions as observational class names only. Do not infer
seat/school attendance from arbitrary interaction names or coordinates.
"""
from mhs122_classroom_job_readback import LESSON_SITUATIONS


def _guid(obj):
    if obj is None:
        return None
    for x in (obj,getattr(obj,'tuned_class',None),type(obj)):
        result=getattr(x,'guid64',None)
        if type(result) is int and result>0:
            return result
    return None


def _name(value):
    if value is None:
        return 'NONE'
    obj=type(value)
    return (getattr(obj,'__module__','?')+'.'+
            getattr(obj,'__name__','?'))[:140]


def _active_interaction(sim):
    # The EA active interaction is an observation, never a prompt to
    # cancel a player's action or to push a potentially wrong affordance.
    try:
        queue=getattr(sim,'queue',None)
        if queue is None:
            return 'UNAVAILABLE'
        running=getattr(queue,'running',None)
        if running is None:
            return 'NONE'
        return _name(running)
    except Exception:
        return 'READ_ERROR'


def _waiting_interactions(sim):
    try:
        queue=getattr(sim,'queue',None)
        if queue is None:
            return ('UNAVAILABLE',)
        # Do not consume iterators that can change live game state.
        elements=getattr(queue,'_queue',None)
        if type(elements) not in (tuple,list):
            return ('NOT_EXPOSED',)
        return tuple(_name(x) for x in elements[:5])
    except Exception:
        return ('READ_ERROR',)


def inspect_sixteen_lesson_actions(groups,sim_info_manager,
                                   situation_manager,age,species):
    report={
        'kind':'M124_ORIGINAL_EA_LESSON_ROLE_AND_INTERACTION_SNAPSHOT',
        'status':'INVALID_ROSTER',
        'game_modified':False,
        'cancelled_actions':False,
        'pushed_interactions':False,
        'lessons_seated_verified':False,
        'teacher_to_room_mapping_verified':False,
        'native_assigned_job_does_not_prove_seating':True,
        'rows':(),
    }
    if (type(groups) not in (tuple,list) or len(groups)!=2
            or any(type(x) not in (tuple,list) or len(x)!=8 for x in groups)):
        return report
    strings=tuple(str(v) for group in groups for v in group)
    if (len(set(strings))!=16 or any(not x.isdigit() or
            int(x)<=0 or str(int(x))!=x for x in strings)):
        return report
    lookup=getattr(sim_info_manager,'get',None)
    memberships=getattr(situation_manager,'get_situations_sim_is_in',None)
    if not callable(lookup) or not callable(memberships):
        report['status']='EA_MEMBERSHIP_API_UNAVAILABLE'
        return report
    rows=[]
    for klass,group in enumerate(groups,1):
        for raw in group:
            sid=str(raw)
            row={
                'sim_id':sid,'registered_class':klass,
                'native_lesson_situation_guids':(),
                'native_jobs':(),
                'native_role_states':(),
                'native_role_instances':(),
                'running_interaction':'NOT_INSTANCED',
                'queued_interactions':(),
                'state':'SIM_NOT_INSTANCED',
            }
            try:
                info=lookup(int(sid))
                if (info is None or getattr(info,'age',None)!=age
                        or getattr(info,'species',None)!=species):
                    row['state']='INVALID_SIM_INFO'
                    rows.append(row)
                    continue
                sim=info.get_sim_instance()
                if sim is None:
                    rows.append(row)
                    continue
                row['running_interaction']=_active_interaction(sim)
                row['queued_interactions']=_waiting_interactions(sim)
                native=[]
                for situation in tuple(memberships(sim)):
                    guid=_guid(situation)
                    if guid not in LESSON_SITUATIONS:
                        continue
                    job_reader=getattr(situation,'get_current_job_for_sim',None)
                    role_reader=getattr(
                        situation,'get_current_role_state_for_sim',None)
                    role_instance_reader=getattr(
                        situation,'get_current_role_state_instance_for_sim',
                        None)
                    if not all(callable(f) for f in (
                            job_reader,role_reader,role_instance_reader)):
                        row['state']='EA_ROLE_API_UNAVAILABLE'
                        continue
                    job=_guid(job_reader(sim))
                    role=role_reader(sim)
                    instance=role_instance_reader(sim)
                    native.append((guid,job,_guid(role),
                                   _name(role),_name(instance)))
                row['native_lesson_situation_guids']=tuple(x[0] for x in native)
                row['native_jobs']=tuple(x[1] for x in native)
                row['native_role_states']=tuple((x[2],x[3]) for x in native)
                row['native_role_instances']=tuple(x[4] for x in native)
                if row['state']=='EA_ROLE_API_UNAVAILABLE':
                    pass
                elif not native:
                    row['state']='NO_NATIVE_LESSON_SITUATION'
                elif all(LESSON_SITUATIONS[n[0]]==(
                        klass,n[1]) for n in native):
                    row['state']='NATIVE_LESSON_JOB_ASSIGNED_ACTION_UNVERIFIED'
                else:
                    row['state']='OTHER_CLASS_OR_JOB_ASSIGNED'
            except Exception as exc:
                row['state']='READ_ERROR_'+type(exc).__name__
            rows.append(row)
    report['rows']=tuple(rows)
    report['native_correct_class_job_count']=sum(
        x['state']=='NATIVE_LESSON_JOB_ASSIGNED_ACTION_UNVERIFIED'
        for x in rows)
    report['with_running_action']=sum(
        x['running_interaction'] not in (
            'NONE','UNAVAILABLE','NOT_INSTANCED','READ_ERROR')
        for x in rows)
    report['no_running_action']=tuple(x['sim_id'] for x in rows
        if x['running_interaction']=='NONE')
    report['not_in_correct_class_job']=tuple(x['sim_id'] for x in rows
        if x['state']!='NATIVE_LESSON_JOB_ASSIGNED_ACTION_UNVERIFIED')
    report['status']='NATIVE_EA_ACTION_SNAPSHOT_CAPTURED'
    if any(x['state'].startswith('READ_ERROR_') for x in rows):
        report['status']='PARTIAL_EA_ACTION_READ'
    return report
