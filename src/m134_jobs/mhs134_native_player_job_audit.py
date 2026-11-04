"""M134: enumerate exact live EA jobs held by registered playable teens.

Read only. No assignment, spawning, retuning or interaction pushes.
"""
LESSON_GUIDS=(304565,304703,304567)
PREPARATION_GUIDS=(293815,304701,297774)

def guid(value):
    for obj in (value,getattr(value,'tuned_class',None),
                type(value) if value is not None else None):
        result=getattr(obj,'guid64',None) if obj is not None else None
        if type(result) is int and result>0:return result
    return None

def inspect_player_jobs(played,situation_manager,affordance):
    rows=[]
    method=getattr(situation_manager,'get_situations_sim_is_in',None)
    for playable in played:
        sid=playable['sim_id']
        info=playable['sim_info']
        row={'sim_id':sid,'registered_class':playable['registered_class'],
             'situation_jobs':[],'world_mutations':0}
        try:
            sim=info.get_sim_instance()
        except Exception:
            sim=None
        row['instanced']=sim is not None
        if sim is None or not callable(method):
            row['status']='NO_SIM_OR_MEMBERSHIP_API'
            rows.append(row)
            continue
        try:
            situations=tuple(method(sim))
            if len(situations)>64:
                raise ValueError('TOO_MANY_SITUATIONS')
        except Exception as exc:
            row['status']='READ_SITUATIONS_'+type(exc).__name__
            rows.append(row)
            continue
        for situation in situations:
            sit_guid=guid(situation)
            if sit_guid not in LESSON_GUIDS+PREPARATION_GUIDS:
                continue
            read=getattr(situation,'get_current_job_for_sim',None)
            try:
                job=guid(read(sim)) if callable(read) else None
            except Exception:
                job=None
            row['situation_jobs'].append({
                'situation_guid':sit_guid,'job_guid':job,
                'is_lesson':sit_guid in LESSON_GUIDS,
                'is_preparation':sit_guid in PREPARATION_GUIDS})
        row['status']='EA_MEMBERSHIPS_READ'
        rows.append(row)
    refs=[]
    if affordance is not None:
        for key in ('test_globals','_test_globals','tests','test_set'):
            value=getattr(affordance,key,None)
            if value is None:continue
            refs.append({'attribute':key,'type':type(value).__name__,
                         'summary':str(value)[:250]})
    return {'kind':'M134_NATIVE_PLAYER_JOB_MEMBERSHIP',
            'students':rows,'affordance_test_metadata':refs,
            'game_mutations':0,
            'job_requirement_not_inferred':True}
