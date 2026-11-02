"""M99 read-only lifecycle tracing for ONE explicitly requested EA student.

Read-only, pure Python 3.7. Its caller supplies a situation manager, a
SimInfo and the situation ID returned by create_situation. Optional EA
accessors are probed defensively; UNKNOWN means no evidence, never FAILURE.
This code does NOT create/destroy situations or spawn/teleport Sims.
"""
BASE_STUDENT=277733

def _id(value):
    if type(value) is int and value>0:
        return value
    return None

def _guid(value):
    for item in (type(value),getattr(value,'situation_type',None),value):
        if item is None:
            continue
        raw=getattr(item,'guid64',None)
        if type(raw) is int and raw>0:
            return raw
    return None

def _member_ids(sims):
    result=[]
    try:
        for sim in tuple(sims):
            info=getattr(sim,'sim_info',sim)
            sid=getattr(info,'sim_id',None)
            if type(sid) is int and sid>0:
                result.append(sid)
    except Exception:
        return None
    return tuple(sorted(set(result)))

def snapshot(situation_manager,info,created_situation_id):
    """Report only properties the live EA runtime really exposes."""
    result={'created_situation_id':_id(created_situation_id),
            'situation_lookup':'NOT_CHECKED',
            'situation_active':None,
            'situation_guid':None,
            'on_lot':None,
            'in_school_situation':None,
            'situation_member_ids':None,
            'guest_sim_ids':None,
            'phase':'UNKNOWN',
            'error':None}
    try:
        sid=getattr(info,'sim_id',None)
        sim=info.get_sim_instance() if info is not None else None
        result['on_lot']=sim is not None
        if result['created_situation_id'] is None:
            result['phase']='INVALID_CREATE_RESULT'
            return result
        lookup=getattr(situation_manager,'get',None)
        if not callable(lookup):
            result['situation_lookup']='UNAVAILABLE'
            result['phase']='SITUATION_LOOKUP_UNAVAILABLE'
            return result
        try:
            situation=lookup(result['created_situation_id'])
        except (KeyError,LookupError):
            situation=None
        if situation is None:
            result['situation_lookup']='NOT_FOUND'
            result['situation_active']=False
            result['phase']='SIM_PRESENT_SITUATION_GONE' if sim is not None else 'SITUATION_GONE_SIM_ABSENT'
            return result
        result['situation_lookup']='FOUND'
        result['situation_active']=True
        result['situation_guid']=_guid(situation)
        # EA API names differ between game patches, and not every
        # situation type exposes its participants or guest list.
        guest_list=getattr(situation,'_guest_list',None)
        if guest_list is not None:
            iterator=getattr(guest_list,'guest_info_gen',None)
            if callable(iterator):
                try:
                    guest_ids=_member_ids(tuple(iterator()))
                    result['guest_sim_ids']=guest_ids
                except Exception:
                    pass
        member_getter=getattr(situation,'get_sims_in_situation',None)
        if callable(member_getter):
            try:
                members=_member_ids(member_getter())
                result['situation_member_ids']=members
            except Exception:
                pass
        # Strongest evidence of enrollment is the game manager's
        # membership relationship for the explicitly requested Sim.
        if sim is not None:
            get_for_sim=getattr(situation_manager,'get_situations_sim_is_in',None)
            if callable(get_for_sim):
                try:
                    situations=tuple(get_for_sim(sim) or ())
                    result['in_school_situation']=any(
                        s is situation or getattr(s,'id',None)==created_situation_id
                        for s in situations)
                except Exception:
                    pass
        if sim is None:
            result['phase']='SITUATION_ACTIVE_SIM_NOT_SPAWNED'
        elif result['in_school_situation'] is True:
            result['phase']='SIM_PRESENT_AND_IN_REQUESTED_SITUATION'
        else:
            result['phase']='SIM_PRESENT_MEMBERSHIP_UNVERIFIED'
        return result
    except Exception as exc:
        result['phase']='INSPECTION_ERROR'
        result['error']=type(exc).__name__
        return result
