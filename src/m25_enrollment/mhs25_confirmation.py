"""M25 limited in-game enrollment test.

The picker confirms a staged batch, not a saved assignment. A separate
explicit 'mhs25.commit conferma' console action atomically saves the batch
in a distinct M25 JSON folder. Never alters EA classes / .save directly.
"""
from interactions import ParticipantType
from interactions.base.immediate_interaction import ImmediateSuperInteraction
import sims4.commands
import inspect

from mhs_m2_selection_probe import collect_picked_ids, SelectionProbeError
from mhs_m2_game_bridge import current_slot, teenager_checker, BridgeError
from mhs_m2_store import RosterStore, EnrollmentService, StoreError
from mhs_m2_roster import RosterError
import os

_DATA_DIR = os.path.join(os.path.expanduser('~'), 'Documents',
                         'Electronic Arts', 'The Sims 4', 'MY_HIGH_SCHOOL_M25_TEST_DATA')
_STORE = RosterStore(_DATA_DIR)
_PENDING = None
_EVENTS = []


def _out(connection):
    return sims4.commands.CheatOutput(connection)


def _record(kind, klass=None, count=None, message=None):
    _EVENTS.append((kind, klass, count, message))
    if len(_EVENTS) > 20:
        del _EVENTS[:-20]


def stage_picker(klass, interaction):
    """Picker continuation: NO DISK I/O, may fail closed on unsaved game."""
    global _PENDING
    _PENDING = None  # discard any earlier batch before considering a new one
    try:
        picked = collect_picked_ids(interaction, ParticipantType.PickedSim)
        slot = current_slot()
        _PENDING = {'klass': klass, 'picked': picked, 'slot': slot}
        _record('READY', klass, len(picked),
                'Usa mhs25.preview; poi mhs25.commit conferma')
        return True
    except (SelectionProbeError, BridgeError, RosterError,
            ValueError, TypeError) as exc:
        _record('BLOCKED', klass, 0, str(exc))
    except Exception as exc:
        _record('BLOCKED', klass, 0, type(exc).__name__)
    return False


class MHS25StageConfirmClass1(ImmediateSuperInteraction):
    def _run_interaction_gen(self, timeline):
        stage_picker(1, self)
        base = super()._run_interaction_gen(timeline)
        if inspect.isgenerator(base):
            return (yield from base)
        return base


class MHS25StageConfirmClass2(ImmediateSuperInteraction):
    def _run_interaction_gen(self, timeline):
        stage_picker(2, self)
        base = super()._run_interaction_gen(timeline)
        if inspect.isgenerator(base):
            return (yield from base)
        return base


@sims4.commands.Command('mhs25.preview', command_type=sims4.commands.CommandType.Live)
def mhs25_preview(_connection=None):
    out = _out(_connection)
    if _PENDING is None:
        out('M25: nessuna selezione pronta. Apri il picker e premi la spunta.')
        if _EVENTS:
            out('Ultimo evento: {} | {}'.format(_EVENTS[-1][0], _EVENTS[-1][3]))
        return
    selected = _PENDING['picked']
    klass = _PENDING['klass']
    out('M25 TEST: Classe {} | {} selezionati | slot {}'.format(
        klass, len(selected), _PENDING['slot']))
    out('SOLO PREPARATI: nessuna iscrizione e stata scritta.')
    try:
        slot = current_slot()
        if slot != _PENDING['slot']:
            out('BLOCCATO: slot cambiato rispetto alla selezione.')
            return
        roster = _STORE.load(slot)
        out('Gia registrati: Classe 1={} /8, Classe 2={} /8.'.format(
            len(roster.class_members(1)), len(roster.class_members(2))))
        proposed, stats = roster.assign_many(klass, selected, teenager_checker)
        out('PREFLIGHT OK: cambiamenti {}, trasferiti {}, totale Classe {}={}/8'.format(
            stats['changed'], stats['moved'], klass, stats['class_size']))
        out('Per scrivere SOLO nella partita di prova: mhs25.commit conferma')
    except Exception as exc:
        out('NON SCRIVERE: verifica fallita ({})'.format(str(exc)[:140]))


@sims4.commands.Command('mhs25.commit', command_type=sims4.commands.CommandType.Live)
def mhs25_commit(confirmation: str='', _connection=None):
    global _PENDING
    out = _out(_connection)
    if str(confirmation or '').strip().casefold() != 'conferma':
        out('NESSUN DATO SCRITTO. Per il TEST usa: mhs25.commit conferma')
        return
    if _PENDING is None:
        out('NESSUN DATO SCRITTO: nessuna selezione da confermare.')
        return
    try:
        slot = current_slot()
        if slot != _PENDING['slot']:
            out('BLOCCATO: la partita e cambiata. Nessun dato scritto.')
            _PENDING = None
            return
        svc = EnrollmentService(_STORE, current_slot, teenager_checker)
        info = svc.enroll_selection(_PENDING['klass'], _PENDING['picked'])
        out('M25 REGISTRO TEST AGGIORNATO: Classe {} | {} nuovi/spostati | totale {}/8'.format(
            info['class'], info['changed'], info['class_size']))
        out('Registro JSON esterno alla partita. NON e frequenza scolastica reale.')
        _record('SAVED', info['class'], info['changed'], 'slot '+slot)
        _PENDING = None
    except Exception as exc:
        out('M25 BLOCCATO: nessun nuovo batch registrato ({})'.format(str(exc)[:140]))
        _record('REJECTED', _PENDING['klass'], len(_PENDING['picked']), type(exc).__name__)


@sims4.commands.Command('mhs25.roster', command_type=sims4.commands.CommandType.Live)
def mhs25_roster(_connection=None):
    out = _out(_connection)
    try:
        slot = current_slot()
        roster = _STORE.load(slot)
        out('MY HIGH SCHOOL M25 - Registro TEST slot {}'.format(slot))
        for klass in (1,2):
            ids=roster.class_members(klass)
            out('Classe {}: {}/8 iscritti nel JSON'.format(klass,len(ids)))
            for sid in ids:
                out('  Sim ID {}'.format(sid))
        out('Registro esterno; NON assegna situazioni scolastiche.')
    except Exception as exc:
        out('M25: nessun registro consultabile ({})'.format(str(exc)[:140]))


@sims4.commands.Command('mhs25.slot', command_type=sims4.commands.CommandType.Live)
def mhs25_slot(_connection=None):
    out = _out(_connection)
    try:
        slot=current_slot()
        out('M25: partita salvata identificata. Slot {}. Nessun dato modificato.'.format(slot))
    except Exception as exc:
        out('M25: SALVATAGGIO NON IDENTIFICATO. Salva una NUOVA partita di test, poi riprova.')
        out(type(exc).__name__)


@sims4.commands.Command('mhs25.discard', command_type=sims4.commands.CommandType.Live)
def mhs25_discard(_connection=None):
    global _PENDING
    _PENDING = None
    _out(_connection)('M25: selezione preparata cancellata, nessun dato scritto.')


@sims4.commands.Command('mhs25.report', command_type=sims4.commands.CommandType.Live)
def mhs25_report(_connection=None):
    out = _out(_connection)
    out('M25: ultimi {} eventi, solo registro test'.format(len(_EVENTS)))
    for kind, klass, count, message in _EVENTS[-6:]:
        out('{} | Classe {} | {} Sim | {}'.format(kind, klass, count, message))
    out('Lo stato e in memoria; il JSON si scrive solo con mhs25.commit conferma.')
