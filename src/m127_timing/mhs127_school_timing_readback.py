"""M127 non-invasive timing and routing target evidence for EA school.

Records original EA pre-class situation creation times, student running
interaction target, school role states and posture. Does not force or
cancel actions. Target names are diagnostic only: never infer a seat
solely from an interaction or target.
"""
from mhs124_lesson_action_readback import inspect_sixteen_lesson_actions
from mhs126_early_preparation_projection import PREP_JOBS
from mhs123_lesson_guest_projection import LESSON_JOBS


def game_clock(time_service):
    try:
        now=time_service.sim_now
        if callable(now):
            now=now()
        result={'repr':str(now)[:140]}
        for attr in ('hour','minute','absolute_ticks'):
            method=getattr(now,attr,None)
            if callable(method):
                value=method()
            else:
                value=method
            if type(value) is int or type(value) is float:
                result[attr]=value
        return result
    except Exception as exc:
        return {'repr':'CLOCK_UNAVAILABLE_'+type(exc).__name__}


def inspect_action_target(sim):
    if sim is None:
        return {'state':'NOT_INSTANCED'}
    try:
        queue=getattr(sim,'queue',None)
        interaction=getattr(queue,'running',None)
        if interaction is None:
            return {'state':'NOT_RUNNING'}
        target=getattr(interaction,'target',None)
        outcome={
            'state':'RUNNING',
            'interaction_type':type(interaction).__module__+'.'+
                               type(interaction).__name__,
            'target_type':None if target is None else
                          type(target).__module__+'.'+
                          type(target).__name__,
        }
        # No object mutation, no fetching target lists or routes.
        if target is not None:
            for field in ('id','definition','catalog_name'):
                value=getattr(target,field,None)
                if type(value) in (str,int,float,bool):
                    outcome['target_'+field]=value
        posture=getattr(sim,'posture',None)
        outcome['posture_type']=None if posture is None else (
            type(posture).__module__+'.'+type(posture).__name__)
        # Critical: no claim of being seated without a real-world
        # verified posture AND desk location. This module does not do it.
        outcome['physically_seated_verified']=False
        return outcome
    except Exception as exc:
        return {'state':'READ_ERROR_'+type(exc).__name__}


def timed_roster_snapshot(groups,sim_info_manager,situation_manager,
                          time_service,age,species):
    school=inspect_sixteen_lesson_actions(
        groups,sim_info_manager,situation_manager,age,species)
    targets=[]
    for row in school.get('rows',()):
        try:
            info=sim_info_manager.get(int(row['sim_id']))
            sim=info.get_sim_instance() if info else None
            item=inspect_action_target(sim)
        except Exception as exc:
            item={'state':'LOOKUP_ERROR_'+type(exc).__name__}
        targets.append({'sim_id':row['sim_id'],
                        'registered_class':row['registered_class'],
                        'native_job_state':row['state'],
                        'running':row['running_interaction'],
                        'target':item})
    return {
        'kind':'M127_SCHOOL_EARLY_TIMING_AND_ROUTE_SNAPSHOT',
        'clock':game_clock(time_service),
        'school_job_count':school.get(
            'native_correct_class_job_count',0),
        'school_readback_status':school['status'],
        'students':tuple(targets),
        'early_prep_guid_list':tuple(sorted(PREP_JOBS)),
        'native_lesson_guid_list':tuple(sorted(LESSON_JOBS)),
        'game_actions_modified':False,
        'auto_seating_claimed':False,
    }
