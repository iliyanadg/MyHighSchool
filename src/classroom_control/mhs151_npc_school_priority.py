"""M151: bounded native EA NPC preclass request when school football lingers.

Eligibility is intentionally narrow: exactly one of two assigned classrooms,
registered human teen NPC, EA preparation job for this class, a running high
school football idle, unblocked queue, and 09:35--09:49 processed sim clock.
No cancellation, teleportation, bypassed EA interaction tests or false
claims that accepted queue means student entered class.
"""
PREP_ROLES={1:frozenset(((293815,277919),(304701,277919))),
            2:frozenset(((297774,277919),))}
FOOTBALL_IDLE=frozenset(('throwFootballMixers_Idle_X',
                         'throwFootballMixers_Idle_Y'))
BLOCKED_QUEUE_TOKENS=('detention','catchtruant','trytoavoiddetention',
                      'food_eat','generic_consume_food','toilet','sleep',
                      'shower','highschool_active_whiteboard_',
                      'highschool_active_attendclass_npc',
                      'highschool_active_usebook_class',
                      'highschool_active_createbook_class')


def native_prep_role(klass,jobs):
    if klass not in PREP_ROLES or not isinstance(jobs,(tuple,list)):
        return False
    return any(isinstance(job,dict) and
               (job.get('situation_guid'),job.get('job_guid'))
               in PREP_ROLES[klass] for job in jobs)


def eligible_football_preclass(clock,klass,registered,selectable,
                               native_role,board_verified,queue_available,
                               running_name,queued_names,attempts):
    if registered is not True or selectable is not False or klass not in (1,2):
        return False,'NOT_ENROLLED_NPC'
    if not isinstance(clock,dict) or type(clock.get('hour')) is not int or (
            type(clock.get('minute')) is not int):
        return False,'SIM_CLOCK_UNAVAILABLE'
    if clock['hour']!=9 or not 35<=clock['minute']<=49:
        return False,'OUTSIDE_NATIVE_PREPARATION'
    if native_role is not True or board_verified is not True:
        return False,'EA_PREPARATION_OR_BOARD_UNVERIFIED'
    if attempts>=2:
        return False,'BOUNDED_ATTEMPTS_EXHAUSTED'
    if queue_available is not True or not isinstance(queued_names,(tuple,list)):
        return False,'EA_QUEUE_UNAVAILABLE'
    if any(not isinstance(x,str) for x in queued_names):
        return False,'EA_QUEUE_UNREADABLE'
    if any(any(token in name.lower() for token in BLOCKED_QUEUE_TOKENS)
           for name in queued_names):
        return False,'CLASS_OR_PROTECTED_ACTION_QUEUED'
    if running_name not in FOOTBALL_IDLE:
        return False,'NOT_STILL_PLAYING_FOOTBALL'
    return True,'ORIGINAL_EA_NPC_ATTEND_TEST_REQUIRED'
