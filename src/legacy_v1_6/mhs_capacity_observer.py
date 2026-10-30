"""MY HIGH SCHOOL v1.5 - read-only class capacity audit.

EA's high-school classroom *phase* situations do not necessarily include
playable household teens, so playable teens are NEVER assigned a classroom
based on an assumption. A user-supplied classroom count is explicitly
labelled a visual estimate, and can never change actual school selection.
School staff are excluded because only Age.TEEN SimInfos enter the phase scan.
No persistence, situation mutation, trait mutation or spawn.
"""

from mhs_live_seat_adapter import read_assignments

MAX_STUDENTS = 8


class CapacityObservationError(ValueError):
    pass


def _sid(value):
    try:
        sid = str(int(value))
    except (ValueError, TypeError, OverflowError):
        raise CapacityObservationError('ID adolescente non valido')
    if sid == '0' or str(value) != sid:
        raise CapacityObservationError('ID adolescente non valido')
    return sid


def summarize_observation(observation, playable_ids, proposed_counts=None):
    """Return a conservative audit. No modification to observation or game.

    observed members: class-phase participants, NOT proven physical seats.
    known_playable: players whose EA classroom phase can be observed.
    unplaced_playable: loaded playables NOT identified in classroom phase.
    proposed_counts: optional visual confirmation from user, ONLY those unplaced.
    """
    if not isinstance(observation, dict):
        raise CapacityObservationError('Osservazione EA mancante')
    phase = observation.get('phase')
    if phase not in ('lezione','preparazione'):
        raise CapacityObservationError('Non e stata rilevata una fase scolastica valida')
    if observation.get('ambiguous'):
        raise CapacityObservationError('Sim presenti in due classi: risultati non affidabili')
    if observation.get('errors'):
        raise CapacityObservationError('Lettura delle situazioni EA incompleta')
    mapping = observation.get('members')
    if not isinstance(mapping, dict) or 1 not in mapping or 2 not in mapping:
        raise CapacityObservationError('Gruppi EA delle classi mancanti')
    first = set(_sid(v) for v in mapping[1])
    second = set(_sid(v) for v in mapping[2])
    if first.intersection(second):
        raise CapacityObservationError('Adolescente presente in entrambe le classi')
    played = set(_sid(v) for v in playable_ids)
    played_seen = (first | second) & played
    played_unknown = played - played_seen
    npc = {1: len(first - played), 2: len(second - played)}
    observed_playable = {1: len(first & played), 2: len(second & played)}
    total_known = {1: npc[1]+observed_playable[1], 2: npc[2]+observed_playable[2]}
    if proposed_counts is not None:
        if (not isinstance(proposed_counts, (tuple,list)) or len(proposed_counts) != 2 or
                any(type(c) is not int or c < 0 for c in proposed_counts)):
            raise CapacityObservationError('Conteggio manuale giocabili non valido')
        if sum(proposed_counts) != len(played_unknown):
            raise CapacityObservationError('I giocabili indicati non coincidono con quelli caricati e senza aula EA ({})'.format(len(played_unknown)))
        estimated = {1: total_known[1]+proposed_counts[0], 2: total_known[2]+proposed_counts[1]}
    else:
        estimated = None
    return {
        'phase':phase,
        'npc':npc,
        'played_in_ea':observed_playable,
        'played_unknown':len(played_unknown),
        'played_loaded':len(played),
        'phase_total':total_known,
        'estimated':estimated,
        'free':None if estimated is None else {1:MAX_STUDENTS-estimated[1],2:MAX_STUDENTS-estimated[2]},
    }


def observe_school(situation_manager, teenage_infos, playable_ids, proposed_counts=None):
    observation = read_assignments(situation_manager, teenage_infos)
    return summarize_observation(observation,playable_ids,proposed_counts)
