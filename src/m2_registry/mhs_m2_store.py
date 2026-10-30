"""MY HIGH SCHOOL M2: independent, atomic JSON test registry per save slot.

This external file is NOT embedded in The Sims 4 .save and does NOT follow
the game's Save As/revert-to-older-save lifecycle. Only use test saves.
"""
import os
import tempfile

from mhs_m2_roster import SchoolRoster, RosterError, canonical_save_slot


class StoreError(RuntimeError):
    pass


class RosterStore(object):
    def __init__(self, directory):
        if not directory:
            raise StoreError('Indicare una cartella dati separata per il registro M2')
        self.directory = os.path.abspath(directory)

    def path(self, slot):
        value = canonical_save_slot(slot)
        return os.path.join(self.directory, 'Registro_slot_{}.json'.format(value))

    def load(self, slot):
        normalized = canonical_save_slot(slot)
        filepath = self.path(normalized)
        if not os.path.isfile(filepath):
            return SchoolRoster(normalized)
        try:
            with open(filepath, 'r', encoding='utf-8') as stream:
                roster = SchoolRoster.from_json(stream.read())
        except (OSError, UnicodeError, RosterError) as exc:
            raise StoreError('Registro esistente danneggiato; non sovrascrivere: {}'
                             .format(type(exc).__name__))
        if roster.slot != normalized:
            raise StoreError('Registro di un altro salvataggio; lettura bloccata')
        return roster

    def save(self, slot, roster):
        normalized = canonical_save_slot(slot)
        if not isinstance(roster, SchoolRoster) or roster.slot != normalized:
            raise StoreError('ID salvataggio diverso; dati non scritti')
        filepath = self.path(normalized)
        temporary = None
        try:
            if not os.path.isdir(self.directory):
                os.makedirs(self.directory)
            fd, temporary = tempfile.mkstemp(prefix='.mhs2_', suffix='.tmp',
                                               dir=self.directory)
            with os.fdopen(fd, 'w', encoding='utf-8') as stream:
                stream.write(roster.to_json())
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, filepath)
            temporary = None
        except OSError as exc:
            raise StoreError('Scrittura atomica fallita: {}'.format(type(exc).__name__))
        finally:
            if temporary and os.path.exists(temporary):
                try:
                    os.unlink(temporary)
                except OSError:
                    pass
        return filepath


class EnrollmentService(object):
    """Dependency-injected bridge target for future M1 confirmation callbacks."""
    def __init__(self, store, slot_provider, is_teen):
        if not callable(slot_provider) or not callable(is_teen):
            raise StoreError('Mancano i servizi di lettura e verifica Sim')
        self.store = store
        self.slot_provider = slot_provider
        self.is_teen = is_teen

    def enroll_selection(self, klass, sim_ids):
        # Never fall back to a stale last-known slot while writing.
        slot = canonical_save_slot(self.slot_provider())
        existing = self.store.load(slot)
        proposed, result = existing.assign_many(klass, sim_ids, self.is_teen)
        if result['changed']:
            self.store.save(slot, proposed)
        return result
