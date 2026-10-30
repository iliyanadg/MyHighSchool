"""M28 experimental combined controls for MY HIGH SCHOOL.

All changes affect ONLY the external M25 isolated JSON test register.
Does not control EA attendance or modify saved game data.
"""
import inspect
import os

import sims4.commands
from interactions.base.immediate_interaction import ImmediateSuperInteraction
from mhs25_confirmation import stage_picker
from mhs27_remove_ui import open_remove_picker, _lookup_sim_info
from mhs_m2_game_bridge import current_slot, teenager_checker
from mhs_m2_roster import RosterError, canonical_sim_id
from mhs_m2_store import RosterStore
from mhs26_remove import roster_fingerprint

_DATA_DIR = os.path.join(os.path.expanduser('~'), 'Documents',
                         'Electronic Arts', 'The Sims 4',
                         'MY_HIGH_SCHOOL_M25_TEST_DATA')
_STORE = RosterStore(_DATA_DIR)
_PENDING_SWAP = None


class MHS28StageConfirmClass3(ImmediateSuperInteraction):
    def _run_interaction_gen(self, timeline):
        stage_picker(3, self)
        base = super()._run_interaction_gen(timeline)
        if inspect.isgenerator(base):
            return (yield from base)
        return base


class MHS28RemoveClass3(ImmediateSuperInteraction):
    def _run_interaction_gen(self, timeline):
        open_remove_picker(3, self)
        base = super()._run_interaction_gen(timeline)
        if inspect.isgenerator(base):
            return (yield from base)
        return base


def _sim_label(sid):
    info = _lookup_sim_info(sid)
    if info is None:
        return 'Sim non disponibile'
    first = str(getattr(info, 'first_name', '') or '').strip()
    last = str(getattr(info, 'last_name', '') or '').strip()
    return ('{} {}'.format(first, last)).strip() or 'Sim senza nome'


@sims4.commands.Command('mhs28.roster', command_type=sims4.commands.CommandType.Live)
def mhs28_roster(_connection=None):
    out = sims4.commands.CheatOutput(_connection)
    try:
        slot = current_slot()
        roster = _STORE.load(slot)
        out('MY HIGH SCHOOL M28 | REGISTRO TEST | Slot {}'.format(slot))
        for klass in (1, 2, 3):
            members = roster.class_members(klass)
            out('Classe {}: {}/8 iscritti | {} posti liberi'.format(
                klass, len(members), 8-len(members)))
            for sid in members:
                out(' - {} | Sim ID {}'.format(_sim_label(sid), sid))
        out('Questo registro esterno NON controlla la frequenza reale.')
    except Exception as exc:
        out('M28 REGISTRO BLOCCATO: {}'.format(str(exc)[:120]))


@sims4.commands.Command('mhs28.swappreview', command_type=sims4.commands.CommandType.Live)
def mhs28_swappreview(first: str='', second: str='', _connection=None):
    """Plan a full-class-safe exchange using IDs from mhs28.roster."""
    global _PENDING_SWAP
    _PENDING_SWAP = None
    out = sims4.commands.CheatOutput(_connection)
    try:
        a = canonical_sim_id(first)
        b = canonical_sim_id(second)
        slot = current_slot()
        roster = _STORE.load(slot)
        _, result = roster.swap_students(a, b, teenager_checker)
        _PENDING_SWAP = {'slot':slot, 'first':a, 'second':b,
                         'snapshot':roster_fingerprint(roster)}
        out('SCAMBIO PREPARATO (non salvato): {} -> Classe {}; {} -> Classe {}'.format(
            _sim_label(a), result['first_class'],
            _sim_label(b), result['second_class']))
        out('Per confermare SOLO nel registro test: mhs28.swapcommit conferma')
    except Exception as exc:
        out('M28 SCAMBIO NON VALIDO: {}'.format(str(exc)[:140]))


@sims4.commands.Command('mhs28.swapcommit', command_type=sims4.commands.CommandType.Live)
def mhs28_swapcommit(confirmation: str='', _connection=None):
    global _PENDING_SWAP
    out = sims4.commands.CheatOutput(_connection)
    if str(confirmation or '').strip().casefold() != 'conferma':
        out('Nessuna modifica: usa mhs28.swapcommit conferma')
        return
    if _PENDING_SWAP is None:
        out('Nessuno scambio preparato. Nessuna modifica.')
        return
    pending = _PENDING_SWAP
    _PENDING_SWAP = None  # single use even if validation fails
    try:
        slot = current_slot()
        if slot != pending['slot']:
            raise RosterError('Partita cambiata')
        roster = _STORE.load(slot)
        if roster_fingerprint(roster) != pending['snapshot']:
            raise RosterError('Il registro e cambiato. Riprova la selezione')
        updated, stats = roster.swap_students(
            pending['first'], pending['second'], teenager_checker)
        _STORE.save(slot, updated)
        out('M28 SCAMBIO SALVATO nel registro TEST: {} in Classe {}, {} in Classe {}'.format(
            stats['first'], stats['first_class'],
            stats['second'], stats['second_class']))
        out('Nessun Sim cancellato, le lezioni EA non sono modificate.')
    except Exception as exc:
        out('M28 SCAMBIO BLOCCATO: {}'.format(str(exc)[:140]))


@sims4.commands.Command('mhs28.swapcancel', command_type=sims4.commands.CommandType.Live)
def mhs28_swapcancel(_connection=None):
    global _PENDING_SWAP
    _PENDING_SWAP = None
    sims4.commands.CheatOutput(_connection)(
        'M28: scambio annullato, nessuna modifica al registro.')
