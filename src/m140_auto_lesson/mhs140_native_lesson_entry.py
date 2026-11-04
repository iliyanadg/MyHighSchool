"""M140 bounded original EA lesson-start playable assistance.

Never change admissions, situation jobs, NPC roles, school lot, or school
clock. Only ever enqueue the known official whiteboard interaction for a
selectable household teen that is in the exact saved MHS roster.
This is a first event-driven experiment, not proof of physical seating.
"""
def launch_once_at_native_lesson(klass,seen,rows,boards,affordance,
                                 context_factory,queue_func):
    """Native creation event is class-specific; no daily manual command.

    A second EA class creation event cannot enqueue the same playable again.
    Fail closed when class/boards/affordance are not validated.
    """
    if klass not in (1,2):
        return {'attempted':False,'reason':'NOT_OUR_LESSON','results':()}
    if klass in seen:
        return {'attempted':False,'reason':'CLASS_ALREADY_HANDLED','results':()}
    if affordance is None:
        return {'attempted':False,'reason':'EA_INTERACTION_MISSING','results':()}
    if set(boards or ())!={1,2} or any(len(boards[k])!=1 for k in (1,2)):
        return {'attempted':False,'reason':'BOARDS_NOT_UNIQUE','results':()}
    selected=tuple(row for row in rows
                   if row.get('registered_class')==klass)
    if any(not row.get('sim_id') for row in selected):
        return {'attempted':False,'reason':'INVALID_PLAYABLE_ID','results':()}
    # Only mark once real native lesson has already been created upstream.
    seen.add(klass)
    if not selected:
        return {'attempted':True,'reason':'NO_PLAYABLE_IN_CLASS','results':()}
    try:
        out=queue_func(selected,boards,affordance,context_factory)
    except Exception as exc:
        return {'attempted':True,
                'reason':'QUEUE_'+type(exc).__name__,'results':()}
    return {'attempted':True,'reason':out.get('reason','UNKNOWN'),
            'results':tuple(out.get('results',()))}
