"""MY HIGH SCHOOL v0.4 — experimental external roster persistence.

Stores only custom roster JSON, per in-game save-slot ID. Does not write to
The Sims 4 .save files or change any school tuning or actor. This is NOT
integrated with the game's own save/restore operations.
"""
import os
import tempfile

from mhs_registry import SchoolRoster, RosterError


class SaveDataError(RuntimeError):
    pass


def current_slot():
    """Use the same persistence-service public accessors used by TS4 tools.

    Invalid/scratch slots fail closed instead of merging data across saves.
    """
    try:
        import services
        service = services.get_persistence_service()
        proto = service.get_save_slot_proto_buff() if service is not None else None
        slot = int(getattr(proto, 'slot_id', 0))
    except Exception:
        raise SaveDataError('Impossibile leggere ID salvataggio. Carica una partita e riprova.')
    if slot <= 0 or slot >= 0xFFFFFFFE:
        raise SaveDataError('ID salvataggio non valido o temporaneo: {}. Nessun dato scritto.'.format(slot))
    return str(slot)


class RosterStore(object):
    def __init__(self, game_root=None):
        self.root = os.path.abspath(game_root or os.path.join(os.path.expanduser('~'), 'Documents',
                                                               'Electronic Arts', 'The Sims 4'))

    def _data_dir(self):
        if not os.path.isdir(self.root):
            raise SaveDataError('Cartella The Sims 4 non trovata: {}'.format(self.root))
        return os.path.join(self.root, 'MY_HIGH_SCHOOL_Data')

    def path(self, slot):
        if not str(slot).isdigit() or not int(slot):
            raise SaveDataError('ID salvataggio non valido')
        return os.path.join(self._data_dir(), 'Registro_slot_{}.json'.format(int(slot)))

    def load(self, slot):
        location = self.path(slot)
        if not os.path.isfile(location):
            return SchoolRoster(str(slot), {1: 8, 2: 8})
        try:
            with open(location, 'r', encoding='utf-8') as stream:
                raw = stream.read()
            roster = SchoolRoster.from_json(raw)
            if roster.save_key != str(slot):
                raise SaveDataError('ID partita differente nel file: lettura bloccata.')
            return roster
        except (ValueError, TypeError, KeyError, RosterError, OSError) as exc:
            raise SaveDataError('File registro illeggibile: {}. NON sovrascritto.'.format(type(exc).__name__))

    def save(self, slot, roster):
        if roster.save_key != str(slot):
            raise SaveDataError('ID partita non corrispondente. Nessun dato scritto.')
        folder = self._data_dir()
        os.makedirs(folder, exist_ok=True)
        location = self.path(slot)
        temporary = None
        try:
            fd, temporary = tempfile.mkstemp(prefix='.mhs_', suffix='.tmp', dir=folder)
            with os.fdopen(fd, 'w', encoding='utf-8') as stream:
                stream.write(roster.to_json())
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, location)
            temporary = None
        except (OSError, ValueError) as exc:
            raise SaveDataError('Scrittura registro fallita: {}'.format(type(exc).__name__))
        finally:
            if temporary and os.path.exists(temporary):
                try:
                    os.unlink(temporary)
                except OSError:
                    pass
        return location
