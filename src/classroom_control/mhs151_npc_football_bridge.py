"""M151 original-EA-only rescue for a registered NPC still playing football.

Controller provides all verified native APIs. No imports of Sims 4 here,
no artificial class jobs, direct cancellations, teleports or forced success.
An EA-accepted interaction is a queued request, never proof of a real lesson.
"""
from mhs151_npc_school_priority import (
    eligible_football_preclass,native_prep_role,FOOTBALL_IDLE)


def attempt_football_npcs(runtime,clock,info_manager,situation_manager,
                          affordance,boards,queue_reader,membership_reader,
                          context_factory):
    if (not runtime.active or runtime.lesson_classes is None or
            not isinstance(boards,dict) or
            getattr(affordance,'guid64',None)!=297779):
        return False
    if not (isinstance(clock,dict) and clock.get('hour')==9 and
            type(clock.get('minute')) is int and
            35<=clock['minute']<=49):
        return False
    if any(len(boards.get(klass,()))!=1 for klass in (1,2)):
        return False
    any_queued=False
    for klass,ids in enumerate(runtime.lesson_classes,1):
        if klass not in runtime.prep_created:
            continue
        board=boards[klass][0]
        for sid in ids:
            sid=str(sid)
            if sid in runtime.m151_npc_accepted:
                continue
            attempts=runtime.m151_npc_attempts.get(sid,0)
            if attempts>=2:
                continue
            try:
                info=info_manager.get(int(sid))
                if info is None or getattr(info,'is_selectable',None) is not False:
                    continue
                sim=info.get_sim_instance()
                if sim is None:
                    continue
                queue=queue_reader(sim)
                if queue.get('available') is not True:
                    continue
                running=queue.get('running')
                running_name=type(running).__name__ if running is not None else ''
                if running_name not in FOOTBALL_IDLE:
                    continue
                native=membership_reader(sim,situation_manager)
                verified=bool(native.get('available')) and native_prep_role(
                    klass,native.get('jobs') or ())
                permitted,reason=eligible_football_preclass(
                    clock,klass,True,False,verified,True,
                    queue.get('available'),running_name,
                    queue.get('queued_names'),attempts)
                if not permitted:
                    if len(runtime.m151_npc_reports)<32:
                        runtime.m151_npc_reports.append({
                            'clock':clock,'sim_id':sid,'class':klass,
                            'attempted':False,'reason':reason})
                    continue
                row={'clock':clock,'sim_id':sid,'class':klass,
                     'attempted':True,'native_ea_test_passed':False,
                     'queued':False,'lesson_completion_unverified':True}
                try:
                    context=context_factory(sim)
                    tested=affordance.test(board,context)
                    row['native_ea_test_passed']=bool(tested)
                    row['native_test_detail']=str(tested)[:160]
                    if tested:
                        push=getattr(sim,'push_super_affordance',None)
                        if callable(push):
                            result=push(affordance,board,context,picked_object=board)
                            row['queued']=bool(result)
                            row['reason']=('EA_NPC_REQUEST_ACCEPTED_NOT_SEATED'
                                           if result else 'EA_NPC_PUSH_REJECTED')
                        else:
                            row['reason']='EA_NPC_PUSH_MISSING'
                    else:
                        row['reason']='ORIGINAL_EA_NPC_TEST_REFUSED'
                except Exception as exc:
                    row['reason']='EA_NATIVE_REQUEST_'+type(exc).__name__
                runtime.m151_npc_attempts[sid]=attempts+1
                if row['queued']:
                    runtime.m151_npc_accepted.add(sid)
                    any_queued=True
                if len(runtime.m151_npc_reports)<32:
                    runtime.m151_npc_reports.append(row)
            except Exception as exc:
                if len(runtime.m151_npc_reports)<32:
                    runtime.m151_npc_reports.append({
                        'clock':clock,'sim_id':sid,'class':klass,
                        'attempted':False,
                        'reason':'READ_'+type(exc).__name__})
    return any_queued
