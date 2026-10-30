"""Read-only adapter: EA live CLASS PHASE memberships -> offline seat planner.

No traits, situation jobs, schedules, or Sim persistence are modified here.
Counting members of EA background class-phase situations is NOT counting
physical desks or playable Sims who use other school phases.
"""
from mhs_seat_planner import seat_plan
from mhs_school_diagnostics import situation_guid

# Tuning GUIDs identified in the player's original EA XML exports.
GO_CLASS_1 = (293815, 304701)
GO_CLASS_2 = (297774,)
ATTEND_CLASS_1 = (304565, 304703)
ATTEND_CLASS_2 = (304567,)


def _sim_id(info):
    value = getattr(info, 'sim_id', None)
    if value is None:
        value = getattr(info, 'id', None)
    if value is None or not str(value).isdigit() or int(value) <= 0:
        return None
    return str(int(value))


def read_assignments(situation_manager, teen_infos):
    """Read active NPC class phase memberships.

    The phase is chosen only from live situation membership. During transitions
    both GO and ATTEND may coexist; ATTEND is the authoritative current phase.
    Sim present in both different-class situations is flagged ambiguous and
    excluded from seat totals (cannot safely assign on ambiguous information).
    """
    if situation_manager is None:
        raise RuntimeError('SituationManager non disponibile')
    getter = getattr(situation_manager, 'get_situations_sim_is_in', None)
    if not callable(getter):
        raise RuntimeError('API get_situations_sim_is_in non disponibile')
    all_rows = []
    errors = []
    for info in teen_infos:
        sid = _sim_id(info)
        if sid is None:
            continue
        get_inst = getattr(info, 'get_sim_instance', None)
        if not callable(get_inst):
            continue
        try:
            sim = get_inst()
            if sim is None:
                continue
            guids = set()
            for situation in tuple(getter(sim) or ()):
                guid = situation_guid(situation)
                if guid is not None:
                    guids.add(guid)
        except Exception as exc:
            errors.append('{}: {}'.format(sid, type(exc).__name__))
            continue
        all_rows.append((sid, guids))
    phase = 'lezione' if any(set(g) & (set(ATTEND_CLASS_1) | set(ATTEND_CLASS_2)) for _, g in all_rows) else \
            ('preparazione' if any(set(g) & (set(GO_CLASS_1) | set(GO_CLASS_2)) for _, g in all_rows) else 'non rilevata')
    mapping = ({1: ATTEND_CLASS_1, 2: ATTEND_CLASS_2} if phase == 'lezione' else
               {1: GO_CLASS_1, 2: GO_CLASS_2})
    result = {1: [], 2: []}
    ambiguous = []
    for sid, guids in all_rows:
        in1 = bool(set(guids) & set(mapping[1]))
        in2 = bool(set(guids) & set(mapping[2]))
        if in1 and in2:
            ambiguous.append(sid)
        elif in1:
            result[1].append(sid)
        elif in2:
            result[2].append(sid)
    return {'phase': phase, 'members': result, 'ambiguous': sorted(ambiguous),
            'loaded': len(all_rows), 'errors': errors}


def plan_live(roster_assignments, situation_manager, teen_infos):
    observation = read_assignments(situation_manager, teen_infos)
    if observation['phase'] == 'non rilevata':
        return {'observation': observation, 'plan': None}
    if observation['ambiguous'] or observation['errors']:
        return {'observation': observation, 'plan': None}
    # Despite the name, free_seats in the pure planner refers ONLY to observed
    # NPC phase positions, not available physical classroom desks.
    advice = seat_plan(roster_assignments, observation['members'])
    return {'observation': observation, 'plan': advice}
