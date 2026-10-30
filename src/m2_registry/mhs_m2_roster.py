"""MY HIGH SCHOOL M2: pure-Python, transactional classroom enrollment.

Python 3.7 compatible. No game imports, side effects, attendance tracking
or interactions. M1 UI is NOT wired to this module yet.
"""
import json


class RosterError(ValueError):
    pass


def canonical_sim_id(value):
    if isinstance(value, bool) or not isinstance(value, (str, int)):
        raise RosterError('ID Sim non valido')
    value = str(value).strip()
    if not value.isdigit() or int(value) < 1 or str(int(value)) != value:
        raise RosterError('ID Sim non valido')
    return value


def canonical_save_slot(slot):
    if isinstance(slot, bool) or not isinstance(slot, (str, int)):
        raise RosterError('Salvataggio non valido')
    value = str(slot).strip()
    if not value.isdigit() or str(int(value)) != value:
        raise RosterError('Salvataggio non valido')
    if not (1 <= int(value) < 0xFFFFFFFE):
        raise RosterError('Salvataggio temporaneo o non disponibile')
    return value


class SchoolRoster(object):
    VERSION = 1
    CAPACITY = 8

    def __init__(self, slot, assignments=None):
        self.slot = canonical_save_slot(slot)
        self.assignments = {}
        for sim_id, klass in (assignments or {}).items():
            sid = canonical_sim_id(sim_id)
            self._class(klass)
            if sid in self.assignments:
                raise RosterError('ID duplicato')
            self.assignments[sid] = klass
        self._check_capacity()

    @staticmethod
    def _class(klass):
        if type(klass) is not int or klass not in (1, 2, 3):
            raise RosterError('Sono disponibili soltanto le Classi 1, 2 e 3')

    def _check_capacity(self):
        for klass in (1, 2, 3):
            if len(self.class_members(klass)) > self.CAPACITY:
                raise RosterError('Capienza Classe {} superata'.format(klass))

    def class_members(self, klass):
        self._class(klass)
        return sorted((sid for sid, value in self.assignments.items()
                       if value == klass), key=int)

    def assign_many(self, klass, chosen_ids, teen_eligibility):
        """Plan an entire selection without mutating the live roster.

        Add/move selected teens; nonselected students remain enrolled.
        If ANY selected ID is bad, ineligible, duplicated, or exceeds room
        capacity: no changes are applied or persisted. Calls validator for
        *every* Sim, including ones already enrolled.
        """
        self._class(klass)
        if not callable(teen_eligibility):
            raise RosterError('Verifica adolescenza non disponibile')
        if not isinstance(chosen_ids, (tuple, list)):
            raise RosterError('Selezione non valida')
        if not 1 <= len(chosen_ids) <= self.CAPACITY:
            raise RosterError('Scegli da 1 a 8 adolescenti')
        selected = [canonical_sim_id(sid) for sid in chosen_ids]
        if len(set(selected)) != len(selected):
            raise RosterError('Lo stesso Sim appare piu volte nella selezione')
        for sid in selected:
            try:
                accepted = teen_eligibility(sid)
            except Exception:
                raise RosterError('Impossibile verificare adolescente {}'.format(sid))
            if accepted is not True:
                raise RosterError('Sim {} non e un adolescente idoneo'.format(sid))

        proposed = dict(self.assignments)
        before = dict(self.assignments)
        for sid in selected:
            proposed[sid] = klass
        updated = SchoolRoster(self.slot, proposed)  # validate capacity atomically

        changed = sorted([sid for sid in selected if before.get(sid) != klass], key=int)
        moved = sorted([sid for sid in selected
                        if before.get(sid) in (1, 2, 3) and before[sid] != klass], key=int)
        return updated, {
            'slot': self.slot,
            'class': klass,
            'selected': len(selected),
            'changed': len(changed),
            'moved': len(moved),
            'already_in_class': len(selected) - len(changed),
            'class_size': len(updated.class_members(klass))
        }

    def swap_students(self, first, second, teen_eligibility):
        """Exchange two enrolled teenagers between distinct full or partial classes.
        
        Returns a new roster: no mutation or disk I/O until the caller saves.
        """
        a = canonical_sim_id(first)
        b = canonical_sim_id(second)
        if a == b or a not in self.assignments or b not in self.assignments:
            raise RosterError('Seleziona due studenti iscritti differenti')
        source = self.assignments[a]
        target = self.assignments[b]
        if source == target:
            raise RosterError('Gli studenti devono appartenere a classi diverse')
        if not callable(teen_eligibility):
            raise RosterError('Verifica adolescenti non disponibile')
        for sid in (a, b):
            try:
                valid = teen_eligibility(sid)
            except Exception:
                valid = False
            if valid is not True:
                raise RosterError('Studente non idoneo allo scambio: {}'.format(sid))
        result = dict(self.assignments)
        result[a], result[b] = target, source
        updated = SchoolRoster(self.slot, result)
        return updated, {'slot':self.slot, 'first':a, 'second':b,
                         'first_class':target, 'second_class':source}

    def to_dict(self):
        return {'schema': self.VERSION, 'slot': self.slot,
                'assignments': dict(self.assignments)}

    def to_json(self):
        return json.dumps(self.to_dict(), sort_keys=True, indent=2)

    @classmethod
    def from_json(cls, data):
        try:
            decoded = json.loads(data)
            if type(decoded) is not dict or type(decoded.get('schema')) is not int:
                raise RosterError('Struttura file sconosciuta')
            if decoded['schema'] != cls.VERSION or type(decoded['assignments']) is not dict:
                raise RosterError('Versione o struttura registro non supportata')
            if set(decoded) != {'schema', 'slot', 'assignments'}:
                raise RosterError('Campi inattesi nel registro')
            return cls(decoded['slot'], decoded['assignments'])
        except (ValueError, TypeError, KeyError) as exc:
            raise RosterError('Registro JSON non valido: {}'.format(type(exc).__name__))
