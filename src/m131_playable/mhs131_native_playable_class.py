"""M131 opt-in native playable lesson entry; refusal is safer than wrong room.

The official player affordance 276774 (Whiteboard_Class_Start) is used.
MHS enrolled class, not EA's random roster, chooses the board. Object
state must positively identify class, so we never route on a guess.
"""
CLASS1_WHITEBOARD_TRUE=276075
CLASS2_WHITEBOARD_TRUE=276077
PLAYER_CLASS_START=276774


def _state_guid(obj):
    return getattr(obj,'guid64',None)


def safe_class_board_candidates(objects,whiteboard_name,
                                class1state,class2state):
    """Require exactly one board with mutually-exclusive EA True state per class."""
    found={1:[],2:[]}
    if class1state is None or class2state is None:
        return found,'STATE_TUNING_NOT_LOADED'
    for obj in objects:
        if whiteboard_name not in type(obj).__name__:
            continue
        active=getattr(obj,'state_value_active',None)
        if not callable(active):
            continue
        try:
            is_one=bool(active(class1state))
            is_two=bool(active(class2state))
        except Exception:
            continue
        if is_one==is_two:
            continue
        found[1 if is_one else 2].append(obj)
    if any(len(found[k])!=1 for k in (1,2)):
        return found,'REQUIRE_EXACTLY_ONE_EA_BOARD_PER_CLASS'
    if found[1][0] is found[2][0]:
        return found,'SHARED_BOARD_REFUSED'
    return found,'TWO_VALIDATED_EA_CLASS_BOARDS'


def find_playable_entry(groups,sim_info_manager,active_household):
    """Read household membership; return registered teen IDs only."""
    if (len(groups)!=2 or any(len(x)!=8 for x in groups)
            or len(set(str(s) for g in groups for s in g))!=16):
        raise ValueError('REQUIRE_EXACT_8_8_REGISTRY')
    membership={}
    for klass,ids in enumerate(groups,1):
        for sid in ids:
            membership[str(sid)]=klass
    rows=[]
    for info in active_household.sim_info_gen():
        sid=str(getattr(info,'sim_id',None))
        klass=membership.get(sid)
        if klass is None:
            continue
        if not getattr(info,'is_selectable',False):
            continue
        rows.append({'sim_id':sid,'registered_class':klass,
                     'sim_info':info})
    return rows


def queue_playable_class(played,boards,affordance,context_factory):
    """Queue EA player interaction only, never cancel or teleport Sims."""
    if affordance is None:
        return {'success':False,'reason':'PLAYER_EA_AFFORDANCE_UNAVAILABLE'}
    for row in played:
        if row['registered_class'] not in boards or len(
                boards[row['registered_class']])!=1:
            return {'success':False,'reason':'BOARD_NOT_UNIQUE'}
    results=[]
    for row in played:
        sim_info=row['sim_info']
        try:
            sim=sim_info.get_sim_instance()
        except Exception:
            sim=None
        if sim is None:
            results.append({'sim_id':row['sim_id'],
                            'queued':False,'reason':'NOT_INSTANCED'})
            continue
        target=boards[row['registered_class']][0]
        try:
            queue=getattr(sim,'queue',None)
            running=getattr(queue,'running',None)
            running_name=type(running).__name__ if running else ''
            # Never interrupt existing school player lesson or protected needs.
            if (('HighSchool_Active_Whiteboard_' in running_name
                    or 'HighSchool_Active_UseBook_Class' in running_name
                    or 'HighSchool_Active_CreateBook_Class' in running_name
                    or 'HighSchool_Active_WriteOnBook' in running_name
                    or 'HighSchool_Active_Listen_' in running_name
                    or any(token in running_name.lower() for token in (
                        'toilet','detention','catchtruant','trytoavoiddetention',
                        'social_highschool_active','sleep','shower',
                        'food_eat','generic_consume_food','orderfood')))):
                results.append({'sim_id':row['sim_id'],
                    'queued':False,'reason':'EXISTING_PROTECTED_ACTION'})
                continue
            push=getattr(sim,'push_super_affordance',None)
            if not callable(push):
                results.append({'sim_id':row['sim_id'],
                    'queued':False,'reason':'PUSH_API_UNAVAILABLE'})
                continue
            context=context_factory(sim)
            result=push(affordance,target,context,picked_object=target)
            results.append({'sim_id':row['sim_id'],
                'queued':bool(result),
                'reason':'EA_ACCEPTED' if result else 'EA_REJECTED'})
        except Exception as exc:
            results.append({'sim_id':row['sim_id'],
                'queued':False,'reason':'EA_PUSH_'+type(exc).__name__})
    return {'success':all(r['queued'] for r in results),
            'reason':'EA_PUSH_ATTEMPT_COMPLETE','results':results,
            'guaranteed_physically_seated':False}
