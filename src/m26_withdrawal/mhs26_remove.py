"""M26: safe, pure-Python removal from an enrolled class.

This is NOT the in-game picker: use the class-specific member list to
construct that picker, then recheck the saved roster at confirmation.
No game imports or file I/O in this module.
"""
import hashlib

from mhs_m2_roster import SchoolRoster, RosterError, canonical_sim_id, canonical_save_slot


class RemovalError(ValueError):
    pass


def class_member_ids(roster, klass):
    if not isinstance(roster, SchoolRoster):
        raise RemovalError('Registro non disponibile')
    roster._class(klass)
    return tuple(roster.class_members(klass))


def candidate_rows(roster, klass, lookup):
    """Data for native SimPicker: ONLY members currently enrolled in klass.

    The lookup yields real SimInfo; skips missing Sims rather than inventing
    portraits or accidentally showing an unregistered NPC.
    """
    if not callable(lookup):
        raise RemovalError('Ricerca Sim non disponibile')
    entries = []
    for sid in class_member_ids(roster, klass):
        sim_info = lookup(sid)
        if sim_info is None:
            continue
        candidate_id = getattr(sim_info, 'sim_id', None)
        if candidate_id is None:
            candidate_id = getattr(sim_info, 'id', None)
        try:
            valid = canonical_sim_id(candidate_id)
        except RosterError:
            continue
        if valid == sid:
            entries.append(sim_info)
    return tuple(entries)


def plan_removal(roster, klass, selected_ids):
    """Atomic class-scoped withdrawal; return new roster and result.

    Never deletes a Sim or changes the other class. Selection is rejected
    if ANY chosen ID is not currently enrolled in this exact class.
    """
    if not isinstance(roster, SchoolRoster):
        raise RemovalError('Registro non disponibile')
    roster._class(klass)
    if type(selected_ids) not in (list, tuple) or not 1 <= len(selected_ids) <= 8:
        raise RemovalError('Seleziona da 1 a 8 studenti iscritti')
    try:
        selected = tuple(canonical_sim_id(sid) for sid in selected_ids)
    except RosterError:
        raise RemovalError('ID studente non valido')
    if len(set(selected)) != len(selected):
        raise RemovalError('Studente ripetuto nella selezione')
    before = roster.assignments
    for sid in selected:
        if before.get(sid) != klass:
            raise RemovalError('Studente non iscritto alla Classe {}'.format(klass))
    proposed = {sid: number for sid, number in before.items()
                if sid not in selected}
    updated = SchoolRoster(roster.slot, proposed)
    return updated, {
        'slot': roster.slot,
        'class': klass,
        'removed': len(selected),
        'remaining': len(updated.class_members(klass)),
        'ids': selected
    }


def roster_fingerprint(roster):
    """Detect changes between the picker opening and explicit confirmation."""
    if not isinstance(roster, SchoolRoster):
        raise RemovalError('Registro non valido')
    return hashlib.sha256(roster.to_json().encode('utf-8')).hexdigest()


class RemovalService(object):
    """Test-registry adapter: no writes before an explicit commit."""
    def __init__(self, store):
        self.store = store

    def preview(self, slot, klass, selected_ids):
        normalized = canonical_save_slot(slot)
        current = self.store.load(normalized)
        _, stats = plan_removal(current, klass, selected_ids)
        return {
            'slot': normalized, 'class': klass, 'selected': tuple(stats['ids']),
            'removed': stats['removed'], 'remaining': stats['remaining'],
            'snapshot': roster_fingerprint(current),
        }

    def commit(self, preview, slot):
        if type(preview) is not dict:
            raise RemovalError('Anteprima inesistente')
        normalized = canonical_save_slot(slot)
        if normalized != preview.get('slot'):
            raise RemovalError('Partita cambiata: rimozione bloccata')
        current = self.store.load(normalized)
        if roster_fingerprint(current) != preview.get('snapshot'):
            raise RemovalError('Registro cambiato dall anteprima: riprova')
        updated, result = plan_removal(
            current, preview.get('class'), preview.get('selected'))
        self.store.save(normalized, updated)
        return result
