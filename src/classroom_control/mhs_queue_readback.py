"""Read-only EA InteractionQueue inspection; never peek/get_head or cancel.

Verified from the player's Python 3.7 InteractionQueue: __iter__ yields running
then all buckets, skipping a duplicate running object. Reading _queue as a
list is not this API. Bound iteration; incomplete/unknown reads fail closed.
"""
MAX_QUEUE_ITEMS = 64


def _parent_names(action):
    names=[]
    seen={id(action)}
    for _ in range(8):
        parent=getattr(action,'super_interaction',None)
        if parent is None or id(parent) in seen:
            return tuple(names)
        seen.add(id(parent))
        names.append(type(parent).__name__)
        action=parent
    raise ValueError('EA_INTERACTION_PARENT_CHAIN_LIMIT')


def queue_snapshot(sim):
    try:
        queue = getattr(sim, 'queue', None)
        if queue is None or not callable(getattr(type(queue), '__iter__', None)):
            return {'available': False, 'reason': 'EA_QUEUE_ITERATOR_UNAVAILABLE'}
        running = getattr(queue, 'running', None)
        waiting = []
        seen = set()
        for count, action in enumerate(queue):
            if count >= MAX_QUEUE_ITEMS:
                return {'available': False, 'reason': 'EA_QUEUE_READ_LIMIT'}
            if action is None or action is running or id(action) in seen:
                continue
            seen.add(id(action))
            waiting.append(action)
        return {'available': True, 'reason': 'EA_QUEUE_READ_ONLY',
                'running': running, 'waiting': tuple(waiting),
                'running_name': type(running).__name__ if running is not None else '',
                'active_parent_names': _parent_names(running) if running is not None else (),
                'queued_names': tuple(type(action).__name__ for action in waiting)}
    except Exception as exc:
        return {'available': False, 'reason': 'EA_QUEUE_READ_' + type(exc).__name__}
