"""MY HIGH SCHOOL — deterministic seat plan, Python 3.7.

OFFLINE ONLY. Does not import or hook EA gameplay code, and is NOT a game mod.
Input is a per-save custom roster and independently observed occupancy. Existing
EA situation membership must be read/mutated by a separately tested adapter.
"""
from collections import OrderedDict

MAX_CLASS = 8
SUPPORTED_CLASSES = (1, 2)

class SeatPlanError(ValueError):
    pass


def seat_plan(roster, class_occupants=None, known_teens=None):
    """Return a purely advisory plan prioritizing enrolled teens for 2 classes.

    roster: mapping of Sim ID -> class (1 or 2)
    class_occupants: mapping of class -> ordered list of observed IDs already
        occupying a desk as student. The caller must obtain reliable real
        phase membership, NOT just presence on the lot or a hidden trait.
    known_teens: optional set of Sims known to be teens; reject stale roster.

    Never silently evicts an existing EA student. For that reason, a class with
    no free physical place is returned as BLOCKED, not made over-capacity.
    """
    occupants = class_occupants or {}
    enrolled = {k: [] for k in SUPPORTED_CLASSES}
    seen = set()
    for raw_id, klass in roster.items():
        sid = str(raw_id)
        if not sid.isdigit() or int(sid) <= 0 or klass not in SUPPORTED_CLASSES:
            raise SeatPlanError('Roster contains invalid Sim ID or class')
        if sid in seen:
            raise SeatPlanError('Duplicate Sim ID')
        if known_teens is not None and sid not in {str(v) for v in known_teens}:
            raise SeatPlanError('Not a currently eligible teenage Sim: ' + sid)
        seen.add(sid)
        enrolled[klass].append(sid)
    result = OrderedDict()
    for klass in SUPPORTED_CLASSES:
        planned = sorted(enrolled[klass], key=int)
        if len(planned) > MAX_CLASS:
            raise SeatPlanError('More than eight enrolled in class {}'.format(klass))
        current = [str(v) for v in occupants.get(klass, ())]
        if len(current) != len(set(current)):
            raise SeatPlanError('Duplicate Sim observed in class {}'.format(klass))
        if len(current) > MAX_CLASS:
            result[klass] = {'status': 'OVER_CAPACITY', 'desired': planned,
                             'already_correct': [], 'missing': planned,
                             'unregistered_occupants': current, 'free_seats': 0}
            continue
        current_set = set(current)
        right = [sid for sid in planned if sid in current_set]
        missing = [sid for sid in planned if sid not in current_set]
        foreign = [sid for sid in current if sid not in planned]
        free = MAX_CLASS - len(current)
        status = 'READY' if len(missing) <= free else 'NEEDS_SAFE_REPLACEMENT'
        result[klass] = {'status': status, 'desired': planned,
                         'already_correct': right, 'missing': missing,
                         'unregistered_occupants': foreign, 'free_seats': free}
    return result
