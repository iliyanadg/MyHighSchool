"""M52: class-scoped multi-student removal using one native picker.

Checkmark removes selected Sims from the isolated registry JSON immediately;
X cancels. No Sim is deleted from the EA save. Legacy M27 console debug
commands are kept but not used in the native picker.
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
from mhs34_settings import SettingsStore

_DATA_DIR = os.path.join(os.path.expanduser('~'), 'Documents',
                         'Electronic Arts', 'The Sims 4',
                         'MY_HIGH_SCHOOL_M25_TEST_DATA')
_SERVICE = RemovalService(RosterStore(_DATA_DIR))
_SETTINGS = SettingsStore(_DATA_DIR)
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


def _remove_limit(count):
    """EA native picker policy: allow 1..8 current students in ONE window."""
    from ui.ui_dialog_picker import UiDialogObjectPicker
    if type(count) is not int or not 1<=count<=8:
        raise RosterError('Numero candidati rimozione non valido')
    base=UiDialogObjectPicker._MaxSelectableUnlimited
    if not callable(getattr(base,'get_max_selectable',None)):
        raise TypeError('Selettore EA non compatibile')

    class _RemovalSeats(base):
        def get_max_selectable(self,*args,**kwargs):
            return count

    return _RemovalSeats()


def _remove_text(value):
    from sims4.localization import LocalizationHelperTuning
    return lambda **_:LocalizationHelperTuning.get_raw_text(str(value))


def _remove_notice(actor,title,body):
    _event('NOTICE',title+': '+body)
    if actor is None:
        return False
    try:
        from ui.ui_dialog_notification import UiDialogNotification
        dlg=UiDialogNotification.TunableFactory().default(
            actor,title=_remove_text(title),text=_remove_text(body))
        dlg.show_dialog()
        return True
    except Exception as exc:
        _event('NOTICE_FAILED',type(exc).__name__)
        return False


def _dialog_factory(klass, sim_infos, actor, title_text=None, description_text=None):
    """Native multi-select; only students enrolled in this class appear."""
    from ui.ui_dialog_picker import SimPickerRow, UiSimPicker
    dialog=UiSimPicker.TunableFactory().default(
        actor,
        title=_remove_text(title_text or
            'Rimuovi studenti - Classe {}'.format(klass)),
        text=_remove_text(description_text or
            'Seleziona gli iscritti da rimuovere. Spunta = rimuovi dal registro. '
            'X = chiudi senza modifiche. I Sim resteranno nel gioco.'),
        max_selectable=_remove_limit(len(sim_infos)),
        min_selectable=1,should_show_names=True,hide_row_description=False)
    for sim_info in sim_infos:
        dialog.add_row(SimPickerRow(sim_info.sim_id,False,tag=sim_info.sim_id))
    return dialog


def open_remove_picker(klass, interaction):
    """M52: one checkmark removes ALL selected registered Sims, never deletes Sims.

    The legacy M27 console staging commands remain only for compatibility;
    this interaction directly validates and commits a single atomic JSON
    change. Clicking X is always a no-op.
    """
    global _PENDING
    _PENDING=None
    actor=getattr(interaction,'sim',None)
    if actor is None:
        try:
            actor=services.client_manager().get_first_client().active_sim
        except Exception:
            actor=None
    try:
        slot=current_slot()
        _SETTINGS.require_management(slot,klass)
        roster=_SERVICE.store.load(slot)
        ids=tuple(roster.class_members(klass))
        if not ids:
            _event('EMPTY','Classe {} senza studenti'.format(klass))
            _remove_notice(actor,'MY HIGH SCHOOL',
                'Classe {}: nessuno studente da rimuovere.'.format(klass))
            return False
        choices=candidate_rows(roster,klass,_lookup_sim_info)
        if not choices:
            _event('BLOCKED','Sim iscritti non disponibili')
            _remove_notice(actor,'MY HIGH SCHOOL',
                'Studenti iscritti non disponibili nel salvataggio.')
            return False
        if actor is None:
            _event('BLOCKED','Sim attivo non disponibile')
            return False
        available={str(info.sim_id) for info in choices}
        snapshot=roster_fingerprint(roster)
        dialog=_dialog_factory(klass,choices,actor)
        processed=[False]

        def _selection_callback(result_dialog):
            if processed[0]:
                return
            processed[0]=True
            if not getattr(result_dialog,'accepted',False):
                _event('CANCELLED','Classe {}'.format(klass))
                return
            try:
                from mhs_m2_roster import canonical_sim_id
                chosen=tuple(canonical_sim_id(sid)
                             for sid in result_dialog.get_result_tags())
                if (not 1<=len(chosen)<=len(choices) or
                        len(set(chosen))!=len(chosen) or
                        not set(chosen).issubset(available)):
                    raise RosterError('Selezione non valida: scegli soltanto gli iscritti')
                if current_slot()!=slot:
                    raise RosterError('Il salvataggio e cambiato')
                _SETTINGS.require_management(slot,klass)
                current=_SERVICE.store.load(slot)
                if roster_fingerprint(current)!=snapshot:
                    raise RosterError('Registro cambiato: riapri Rimuovi studenti')
                preview=_SERVICE.preview(slot,klass,chosen)
                result=_SERVICE.commit(preview,current_slot())
                _event('REMOVED','Classe {} | {} rimossi'.format(
                    klass,result['removed']))
                _remove_notice(actor,'MY HIGH SCHOOL - Rimozione completata',
                    '{} studenti rimossi dal registro della Classe {}. '
                    'Rimangono {}/8 iscritti. Nessun Sim e stato eliminato.'.format(
                        result['removed'],klass,result['remaining']))
            except Exception as exc:
                _event('BLOCKED',type(exc).__name__)
                _remove_notice(actor,'MY HIGH SCHOOL - Nessuna modifica',
                    'Rimozione non eseguita: {}'.format(str(exc)[:120]))

        dialog.add_listener(_selection_callback)
        dialog.show_dialog()
        _event('OPEN','Classe {} | {} studenti'.format(klass,len(choices)))
        return True
    except Exception as exc:
        _event('ERROR','{}: {}'.format(type(exc).__name__,str(exc)[:100]))
        _remove_notice(actor,'MY HIGH SCHOOL - Impossibile aprire',
            '{}'.format(str(exc)[:125]))
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
    out('Le azioni native M52 ora rimuovono con la spunta; X annulla.')
