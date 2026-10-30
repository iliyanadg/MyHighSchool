"""M27 prototype — class-scoped student removal from MY HIGH SCHOOL menu.

Native Sim portraits are built only from current classroom enrollment.
The picker NEVER writes. Only mhs27.removecommit conferma can write to the
same isolated M25 test JSON, after save-slot and roster-snapshot checks.
Compatibility of UiSimPicker factory must be validated in-game.
"""
import inspect
import os

import services
import sims4.commands
from interactions.base.immediate_interaction import ImmediateSuperInteraction

from mhs_m2_game_bridge import current_slot
from mhs_m2_roster import RosterError
from mhs_m2_store import RosterStore, StoreError
from mhs26_remove import (RemovalService, RemovalError, candidate_rows,
                          roster_fingerprint)

_DATA_DIR = os.path.join(os.path.expanduser('~'), 'Documents',
                         'Electronic Arts', 'The Sims 4',
                         'MY_HIGH_SCHOOL_M25_TEST_DATA')
_SERVICE = RemovalService(RosterStore(_DATA_DIR))
_PENDING = None
_EVENTS = []


def _event(code, info):
    _EVENTS.append((str(code), str(info)[:120]))
    if len(_EVENTS) > 15:
        del _EVENTS[:-15]


def _lookup_sim_info(sid):
    manager = services.sim_info_manager()
    if manager is None:
        return None
    try:
        info = manager.get(int(sid))
    except (TypeError, ValueError, AttributeError):
        info = None
    if info is not None:
        return info
    for candidate in manager.get_all():
        value = getattr(candidate, 'sim_id', None)
        if value is None:
            value = getattr(candidate, 'id', None)
        if value is not None and str(value) == str(sid):
            return candidate
    return None


def _dialog_factory(klass, sim_infos, actor, title_text=None, description_text=None):
    """Direct native picker; no Sim not present in sim_infos is added."""
    from sims4.localization import LocalizationHelperTuning
    from ui.ui_dialog_picker import SimPickerRow, UiSimPicker

    title = lambda **_: LocalizationHelperTuning.get_raw_text(
        title_text or 'Rimuovi studenti - Classe {}'.format(klass))
    description = lambda **_: LocalizationHelperTuning.get_raw_text(
        description_text or 'Seleziona gli iscritti da rimuovere dal registro. I Sim non verranno eliminati.')
    # The old M27 implementation supplied a hand-built ImmutableSlots as
    # max_selectable. The October 2026 game calls get_max_selectable() on
    # this object while building the picker, causing a silent UI failure:
    # AttributeError: 'ImmutableSlots' object has no attribute ...
    # Let the game's TunableFactory supply its own valid selectable policy.
    # Only enrolled students are offered (hard limit of eight per class).
    # RemovalService independently rejects invalid or oversized selections.
    dialog = UiSimPicker.TunableFactory().default(
        actor, text=description, title=title,
        min_selectable=1, should_show_names=True, hide_row_description=False)
    for sim_info in sim_infos:
        dialog.add_row(SimPickerRow(sim_info.sim_id, False, tag=sim_info.sim_id))
    return dialog


def open_remove_picker(klass, interaction):
    """Read-only opening and staging. Failure does not mutate school state."""
    global _PENDING
    _PENDING = None
    try:
        slot = current_slot()
        roster = _SERVICE.store.load(slot)
        allowed_ids = tuple(roster.class_members(klass))
        if not allowed_ids:
            _event('EMPTY', 'Classe {} non ha iscritti'.format(klass))
            return False

        choices = candidate_rows(roster, klass, _lookup_sim_info)
        if not choices:
            _event('BLOCKED', 'Iscritti non presenti nel SimInfoManager')
            return False
        actor = getattr(interaction, 'sim', None)
        if actor is None:
            client = services.client_manager().get_first_client()
            actor = getattr(client, 'active_sim', None)
        if actor is None:
            _event('BLOCKED', 'Actor Sim non disponibile')
            return False
        snapshot = roster_fingerprint(roster)
        dialog = _dialog_factory(klass, choices, actor)

        def _selection_callback(result_dialog):
            global _PENDING
            _PENDING = None
            if not getattr(result_dialog, 'accepted', False):
                _event('CANCELLED', 'Classe {}'.format(klass))
                return
            try:
                tags = tuple(result_dialog.get_result_tags())
                if not tags:
                    _event('BLOCKED', 'Nessuno studente selezionato')
                    return
                # Refuse a stale save slot even before staging.
                if current_slot() != slot:
                    _event('BLOCKED', 'Partita cambiata')
                    return
                preview = _SERVICE.preview(slot, klass, tags)
                if preview['snapshot'] != snapshot:
                    _event('BLOCKED', 'Registro aggiornato durante la scelta')
                    return
                # A real filtered UI candidate list MUST cover all chosen IDs.
                if not set(preview['selected']).issubset(set(allowed_ids)):
                    _event('BLOCKED', 'Picker ha restituito un ID non iscritto')
                    return
                _PENDING = preview
                _event('READY', 'Classe {} | {} da rimuovere. mhs27.removepreview'.format(
                    klass, preview['removed']))
            except Exception as exc:
                _event('BLOCKED', type(exc).__name__)
        dialog.add_listener(_selection_callback)
        # Do not override the dialog header icon with a (None, SimInfo)
        # tuple. The live game expects an icon data object with
        # icon_resource; passing a tuple crashes the picker on open.
        # The SimPickerRow entries still provide native Sim portraits.
        dialog.show_dialog()
        _event('OPEN', 'Classe {} | candidati {}'.format(klass, len(choices)))
        return True
    except Exception as exc:
        _event('ERROR', '{}: {}'.format(type(exc).__name__, str(exc)[:60]))
        return False


class MHS27RemoveClass1(ImmediateSuperInteraction):
    def _run_interaction_gen(self, timeline):
        open_remove_picker(1, self)
        result = super()._run_interaction_gen(timeline)
        if inspect.isgenerator(result):
            return (yield from result)
        return result


class MHS27RemoveClass2(ImmediateSuperInteraction):
    def _run_interaction_gen(self, timeline):
        open_remove_picker(2, self)
        result = super()._run_interaction_gen(timeline)
        if inspect.isgenerator(result):
            return (yield from result)
        return result


@sims4.commands.Command('mhs27.removepreview', command_type=sims4.commands.CommandType.Live)
def mhs27_removepreview(_connection=None):
    out = sims4.commands.CheatOutput(_connection)
    if not _PENDING:
        out('M27: nessuna rimozione pronta. {}'.format(_EVENTS[-1] if _EVENTS else ''))
        return
    try:
        slot = current_slot()
        if slot != _PENDING['slot']:
            out('M27 BLOCCATO: partita cambiata.')
            return
        before = _SERVICE.store.load(slot)
        if roster_fingerprint(before) != _PENDING['snapshot']:
            out('M27 BLOCCATO: il registro e cambiato.')
            return
        out('M27 PREVIEW: Classe {} | {} studenti da rimuovere | slot {}'.format(
            _PENDING['class'], _PENDING['removed'], slot))
        out('Rimarrebbero {} studenti nella Classe {}.'.format(
            _PENDING['remaining'], _PENDING['class']))
        out('Non e stato cancellato nessun Sim e nessun dato e stato scritto.')
        out('SOLO nella partita di prova: mhs27.removecommit conferma')
    except Exception as exc:
        out('M27 BLOCCATO: {}'.format(type(exc).__name__))


@sims4.commands.Command('mhs27.removecommit', command_type=sims4.commands.CommandType.Live)
def mhs27_removecommit(confirmation: str='', _connection=None):
    global _PENDING
    out = sims4.commands.CheatOutput(_connection)
    if str(confirmation or '').strip().casefold() != 'conferma':
        out('Nessuna rimozione scritta: mhs27.removecommit conferma')
        return
    if _PENDING is None:
        out('M27: nessuna rimozione preparata. Nessuna modifica.')
        return
    try:
        result = _SERVICE.commit(_PENDING, current_slot())
        out('M27 REGISTRO TEST: Classe {} | {} rimossi | restano {}/8'.format(
            result['class'], result['removed'], result['remaining']))
        out('I Sim rimangono nel gioco e possono essere reiscritti.')
        _event('REMOVED', 'Classe {} | {}'.format(result['class'], result['removed']))
        _PENDING = None
    except Exception as exc:
        out('M27 RIMOZIONE BLOCCATA: {}'.format(type(exc).__name__))
        _event('BLOCKED', type(exc).__name__)


@sims4.commands.Command('mhs27.removecancel', command_type=sims4.commands.CommandType.Live)
def mhs27_removecancel(_connection=None):
    global _PENDING
    _PENDING = None
    sims4.commands.CheatOutput(_connection)('M27: rimozione annullata senza scrittura.')


@sims4.commands.Command('mhs27.report', command_type=sims4.commands.CommandType.Live)
def mhs27_report(_connection=None):
    out = sims4.commands.CheatOutput(_connection)
    out('M27 - ultimi eventi diagnostici:')
    for code,info in _EVENTS[-8:]:
        out('{} | {}'.format(code,info))
    out('Nessuna scrittura da apertura picker o click sulla spunta.')
