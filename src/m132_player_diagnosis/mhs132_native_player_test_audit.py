"""M132 read-only EA player lesson entry examination.

Never changes the student's class, queues, motives, buffs, or world state.
Report the *actual* EA affordance test result when that method is available.
Methods unavailable in the running game are reported, not guessed.
"""
PLAYER_ROLE_BUFF=276710


def _name(value):
    return type(value).__module__+'.'+type(value).__name__ if value is not None else None


def _small(value):
    try:
        return str(value)[:360]
    except Exception:
        return 'UNPRINTABLE'


def _has_player_role_buff(sim,info,buff):
    if buff is None:
        return None
    for candidate in (sim,info):
        if candidate is None:
            continue
        check=getattr(candidate,'has_buff',None)
        if callable(check):
            try: return bool(check(buff))
            except Exception: pass
    return None


def inspect_native_player_tests(played,boards,affordance,buff,context_factory):
    output=[]
    for row in played:
        info=row['sim_info']
        try: sim=info.get_sim_instance()
        except Exception:sim=None
        klass=row['registered_class']
        board=boards.get(klass,[None])[0] if len(boards.get(klass,()))==1 else None
        entry={'sim_id':row['sim_id'],'registered_class':klass,
            'instanced':sim is not None,'board_id':str(getattr(board,'id',None)),
            'player_role_buff':_has_player_role_buff(sim,info,buff),
            'readonly':True}
        if sim is None or board is None or affordance is None:
            entry['status']='MISSING_SIM_BOARD_OR_AFFORDANCE'
            output.append(entry)
            continue
        try:
            running=getattr(getattr(sim,'queue',None),'running',None)
            entry['running_action']=_name(running)
            entry['running_target']=_name(getattr(running,'target',None))
            entry['running_target_id']=str(
                getattr(getattr(running,'target',None),'id',None))
        except Exception as exc:
            entry['running_error']=type(exc).__name__
        try:
            context=context_factory(sim)
            tester=getattr(affordance,'test',None)
            if not callable(tester):
                entry['status']='AFFORDANCE_TEST_UNAVAILABLE'
            else:
                result=tester(board,context)
                entry['status']='EA_TEST_RETURNED'
                entry['test_passed']=bool(result)
                entry['test_result_type']=_name(result)
                entry['test_result_details']=_small(result)
                entry['reason']=_small(getattr(result,'reason',None))
        except Exception as exc:
            entry['status']='EA_TEST_EXCEPTION'
            entry['test_error']=type(exc).__name__
            entry['test_error_text']=_small(exc)
        output.append(entry)
    return {'kind':'M132_PLAYER_NATIVE_EA_TEST_RESULT',
        'player_count':len(output),
        'students':output,
        'game_mutations':0,
        'does_not_claim_accepted_queue_or_seating':True}
