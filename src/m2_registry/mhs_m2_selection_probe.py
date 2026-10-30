"""M2 Step 23: read native SimPicker continuation's PickedSim participants.

No Sims4 imports, no file I/O. Collecting participants is NOT evidence
that a multi-selection is complete. Caller must validate complete_count
from an independently verified picker event before saving to M2 roster.
Python 3.7-compatible.
"""
from mhs_m2_roster import canonical_sim_id, RosterError


class SelectionProbeError(ValueError):
    pass


def _id_from_participant(participant):
    """Accept SimInfo or Sim instance, never arbitrary textual target IDs."""
    if participant is None or isinstance(participant, (bool, str, int)):
        raise SelectionProbeError("PickedSim vuoto o non e un oggetto Sim")
    info = getattr(participant, "sim_info", None)
    if info is None:
        info = participant
    if info is None or isinstance(info, (str, int, bool)):
        raise SelectionProbeError("PickedSim non contiene una SimInfo valida")
    raw = getattr(info, "sim_id", None)
    if raw is None:
        raw = getattr(info, "id", None)
    try:
        return canonical_sim_id(raw)
    except RosterError:
        raise SelectionProbeError("PickedSim privo di ID Sim valido")


def collect_picked_ids(interaction, picked_participant_type):
    """Collect *only* PickedSim from interaction continuation.

    Never guess that Actor, TargetSim or context.pick is a chosen Sim.
    Fails closed for missing data, duplicates, unexpected types or >8.
    A tuple of IDs is NOT permission to write a class registry.
    """
    if interaction is None or picked_participant_type is None:
        raise SelectionProbeError("Contesto PickedSim mancante")
    getter = getattr(interaction, "get_participants", None)
    if not callable(getter):
        raise SelectionProbeError("Interazione senza get_participants")
    try:
        participants = getter(picked_participant_type)
    except Exception:
        raise SelectionProbeError("Impossibile recuperare PickedSim dal gioco")
    if participants is None or not isinstance(participants, (tuple, list, set, frozenset)):
        raise SelectionProbeError("Risultato PickedSim non disponibile o inatteso")
    if not 1 <= len(participants) <= 8:
        raise SelectionProbeError("PickedSim deve contenere da 1 a 8 Sim")
    identifiers = [_id_from_participant(entry) for entry in participants]
    if len(identifiers) != len(set(identifiers)):
        raise SelectionProbeError("Sim ripetuto nell'interazione")
    return tuple(sorted(identifiers, key=int))


def require_complete_selection(interaction, picked_type, expected_count,
                               confirmation_of_full_batch=False):
    """Fail closed until runtime capture can prove selected_count is authoritative.

    M1's actor_continuation is observed to show a notification after user
    confirmation, but it is NOT YET known whether one continuation happens
    per selected Sim or preserves all selected Sim IDs in one call.
    """
    if confirmation_of_full_batch is not True:
        raise SelectionProbeError("Selezione completa NON verificata: scrittura bloccata")
    if type(expected_count) is not int or not 1 <= expected_count <= 8:
        raise SelectionProbeError("Numero scelti non verificabile")
    ids = collect_picked_ids(interaction, picked_type)
    if len(ids) != expected_count:
        raise SelectionProbeError("Il gioco ha passato {} Sim ma ne risultano scelti {}"
                                  .format(len(ids), expected_count))
    return ids


def enroll_confirmed_batch(klass, interaction, picked_type, expected_count,
                           confirmed_full_batch, store, slot_provider, is_teen):
    """Real M2 save path, guarded by independently verified picker count.

    This is NOT hooked to the game in M1/M2 yet. No callback sets the
    confirmed_full_batch flag in production. Offline tests may supply it.
    """
    ids = require_complete_selection(interaction, picked_type, expected_count,
                                     confirmed_full_batch)
    from mhs_m2_store import EnrollmentService
    service = EnrollmentService(store, slot_provider, is_teen)
    return service.enroll_selection(klass, ids)
