"""MY HIGH SCHOOL M2: independent, atomic JSON test registry per save slot.

This external file is NOT embedded in The Sims 4 .save and does NOT follow
the game's Save As/revert-to-older-save lifecycle. Only use test saves.
"""
import os
import tempfile
import hashlib
import json

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

    def journal_path(self, slot):
        """Single-step undo journal, scoped to the same save slot."""
        value = canonical_save_slot(slot)
        return os.path.join(self.directory, 'Ultima_modifica_slot_{}.json'.format(value))

    def _atomic_write(self, path, body):
        temp = None
        try:
            if not os.path.isdir(self.directory):
                os.makedirs(self.directory)
            fd, temp = tempfile.mkstemp(prefix='.mhs2_', suffix='.tmp',
                                       dir=self.directory)
            with os.fdopen(fd, 'w', encoding='utf-8') as stream:
                stream.write(body)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temp, path)
            temp = None
        except OSError as exc:
            raise StoreError('Scrittura atomica fallita: {}'.format(type(exc).__name__))
        finally:
            if temp and os.path.exists(temp):
                try:
                    os.unlink(temp)
                except OSError:
                    pass

    def save(self, slot, roster, record_undo=True):
        """Save a validated roster; create an undo snapshot before changing it.

        Writing the undo record first means an interrupted save can only
        leave a *stale* undo entry, which undo_last rejects by checksum.
        """
        normalized = canonical_save_slot(slot)
        if not isinstance(roster, SchoolRoster) or roster.slot != normalized:
            raise StoreError('ID salvataggio diverso; dati non scritti')
        original = self.load(normalized)
        before = original.to_json()
        after = roster.to_json()
        target = self.path(normalized)
        if before != after:
            # M34 includes this runtime-only gate in its .ts4script; legacy
            # M25–M33 bundles don't include it and retain their old behavior.
            try:
                from mhs34_runtime_gate import validate_roster_write
            except ImportError:
                pass
            else:
                validate_roster_write(self.directory, normalized, original, roster)
        if before == after and os.path.isfile(target):
            return target
        if record_undo:
            self._atomic_write(self.journal_path(normalized), json.dumps({
                'schema': 1,
                'slot': normalized,
                'before': before,
                'after_sha256': hashlib.sha256(after.encode('utf-8')).hexdigest()
            }, sort_keys=True))
        self._atomic_write(target, after)
        return target

    def undo_last(self, slot):
        """Undo last TEST-register write, only if no subsequent edit occurred.

        Never touches the .save file or any EA character. A corrupted/stale
        journal fails closed. Does not create another undo checkpoint.
        """
        normalized = canonical_save_slot(slot)
        name = self.journal_path(normalized)
        if not os.path.isfile(name):
            raise StoreError('Nessuna ultima modifica da annullare per questa partita')
        try:
            with open(name, 'r', encoding='utf-8') as file:
                data = json.load(file)
        except (OSError, ValueError, UnicodeError, TypeError):
            raise StoreError('Cronologia annullamento danneggiata; nessun dato scritto')
        if (type(data) is not dict or
                set(data) != {'schema','slot','before','after_sha256'} or
                data['schema'] != 1 or data['slot'] != normalized or
                type(data['before']) is not str or
                type(data['after_sha256']) is not str):
            raise StoreError('Cronologia annullamento non valida; nessun dato scritto')
        old = SchoolRoster.from_json(data['before'])
        if old.slot != normalized:
            raise StoreError('Cronologia di un altro salvataggio; operazione bloccata')
        current = self.load(normalized)
        fingerprint = hashlib.sha256(current.to_json().encode('utf-8')).hexdigest()
        if fingerprint != data['after_sha256']:
            raise StoreError('Registro cambiato: non posso annullare senza rischi')
        self.save(normalized, old, record_undo=False)
        try:
            os.unlink(name)
        except OSError:
            # The stale journal cannot be reused: current state no longer
            # has the after_sha256 fingerprint.
            pass
        return old


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
