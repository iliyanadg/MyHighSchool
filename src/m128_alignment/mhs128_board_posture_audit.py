"""Read-only EA board and posture audit for the sixteen enrolled Sims.

The MHS registration is the only truth for class membership. Identify
whiteboard targets of live interactions, compare to the two class board
object IDs, and inspect actual posture target. No game action is changed.
"""
def _type(obj):
    if obj is None:
        return None
    c=type(obj)
    return c.__module__+'.'+c.__name__


def _object_id(obj):
    if obj is None:
        return None
    value=getattr(obj,'id',None)
    return str(value) if isinstance(value,int) else None


def _safe_position(obj):
    if obj is None:
        return None
    try:
        v=getattr(obj,'position',None)
        if v is None:
            return None
        return {'x':round(float(v.x),2),
                'y':round(float(v.y),2),
                'z':round(float(v.z),2)}
    except Exception:
        return None


def _read_target(sim):
    if sim is None:
        return {'instance':'MISSING'}
    try:
        queue=getattr(sim,'queue',None)
        running=getattr(queue,'running',None)
        target=getattr(running,'target',None)
        posture=getattr(sim,'posture',None)
        seat=getattr(posture,'target',None)
        result={
            'instance':'PRESENT',
            'running_type':_type(running),
            'interaction_target_type':_type(target),
            'interaction_target_id':_object_id(target),
            'interaction_target_position':_safe_position(target),
            'posture_type':_type(posture),
            'posture_target_type':_type(seat),
            'posture_target_id':_object_id(seat),
            'posture_target_position':_safe_position(seat),
            'sim_position':_safe_position(sim),
            'sitting_at_correct_class_desk_proven':False,
        }
        return result
    except Exception as exc:
        return {'instance':'ERROR_'+type(exc).__name__}


def audit_classroom_targets(groups,sim_info_manager,trait):
    """All sixteen, no auto-assignments, no world mutation."""
    if (len(groups)!=2 or len(groups[0])!=8 or len(groups[1])!=8
            or len(set(str(v) for g in groups for v in g))!=16):
        raise ValueError('MHS_REGISTRY_NOT_EXACT_TWO_BY_EIGHT')
    rows=[]
    boards={1:{},2:{}}
    for cls,group in enumerate(groups,1):
        for value in group:
            sid=str(value)
            info=sim_info_manager.get(int(sid))
            if info is None:
                entry={'sim_id':sid,'registered_class':cls,
                       'error':'SIM_INFO_MISSING'}
                rows.append(entry)
                continue
            tracker=getattr(info,'trait_tracker',None)
            method=getattr(tracker,'has_trait',None)
            has_trait=None
            if trait is not None and callable(method):
                try: has_trait=bool(method(trait))
                except Exception: pass
            try: sim=info.get_sim_instance()
            except Exception: sim=None
            details=_read_target(sim)
            target_type=details.get('interaction_target_type') or ''
            board_id=(details.get('interaction_target_id')
                      if 'object_HighSchool_Active_Whiteboard' in target_type
                      else None)
            if board_id is not None:
                boards[cls][board_id]=boards[cls].get(board_id,0)+1
            rows.append({'sim_id':sid,'registered_class':cls,
                'class1_trait_present':has_trait,
                'class1_trait_expected':cls==1,
                'trait_matches':None if has_trait is None
                                  else has_trait==(cls==1),
                'target_whiteboard_id':board_id,
                'interaction':details})
    # Do NOT infer classroom physical mapping from majority selection:
    # if EA has already misrouted everyone, it could be wrong.
    shared=set(boards[1]).intersection(boards[2])
    return {'kind':'M128_CLASSROOM_TARGET_AUDIT',
            'students':rows,'target_counts_by_registered_class':boards,
            'board_ids_targeted_by_both_classes':sorted(shared),
            'count':len(rows),
            'trait_mismatches':sum(row.get('trait_matches') is False
                                   for row in rows),
            'sitting_at_correct_desks_verified':False,
            'game_mutations':0}
