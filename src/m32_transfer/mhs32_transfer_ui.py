"""M51 updates M32 class transfers: native multi-selection and ✓ commit.

Legacy mhs32.* console commands are retained only for debugging; picking
students and confirming now writes the TEST JSON directly. Requires game
High School Years for ultimate attendance integration.
"""
import inspect
import os

import sims4.commands
from interactions.base.immediate_interaction import ImmediateSuperInteraction

from mhs_m2_game_bridge import current_slot, teenager_checker
from mhs_m2_roster import SchoolRoster, RosterError
from mhs_m2_store import RosterStore
from mhs26_remove import candidate_rows, roster_fingerprint
from mhs27_remove_ui import _dialog_factory, _lookup_sim_info
from mhs29_controls import _get_actor
from mhs28_controls import _sim_label
from mhs34_settings import SettingsStore
from sims4.localization import LocalizationHelperTuning
from ui.ui_dialog_picker import UiSimPicker, SimPickerRow, UiDialogObjectPicker
from ui.ui_dialog_notification import UiDialogNotification

_DATA_DIR = os.path.join(os.path.expanduser('~'), 'Documents',
                         'Electronic Arts', 'The Sims 4',
                         'MY_HIGH_SCHOOL_M25_TEST_DATA')
_STORE = RosterStore(_DATA_DIR)
_SETTINGS = SettingsStore(_DATA_DIR)
_PENDING = None
_EVENTS = []


def _record(code, message):
    _EVENTS.append((str(code),str(message)[:140]))
    if len(_EVENTS)>20:
        del _EVENTS[:-20]


def plan_transfer(roster, source, destination, chosen_ids, is_teen):
    """Atomic plan for moving only students of source to destination.

    Fails closed on stale, empty or mixed-class selection, full destination
    and non-teen Sim. Never writes anything.
    """
    if not isinstance(roster, SchoolRoster):
        raise RosterError('Registro non valido')
    roster._class(source)
    roster._class(destination)
    if source==destination:
        raise RosterError('Scegli due classi differenti')
    if not isinstance(chosen_ids,(list,tuple)) or not 1<=len(chosen_ids)<=8:
        raise RosterError('Scegli da uno a otto iscritti')
    from mhs_m2_roster import canonical_sim_id
    selected=[canonical_sim_id(x) for x in chosen_ids]
    if len(selected)!=len(set(selected)):
        raise RosterError('Studente duplicato')
    for sid in selected:
        if roster.assignments.get(sid)!=source:
            raise RosterError('Sim {} non iscritto in Classe {}'.format(sid,source))
    updated, stats = roster.assign_many(destination,selected,is_teen)
    if stats['moved']!=len(selected):
        raise RosterError('Trasferimento incompleto')
    return updated, {'slot':roster.slot,'source':source,
                     'destination':destination,'selected':tuple(selected),
                     'moved':len(selected),'from_size':len(updated.class_members(source)),
                     'to_size':len(updated.class_members(destination))}


def _transfer_selection_strategy(max_students):
    """Use the native EA picker object, with actual remaining seat cap."""
    if type(max_students) is not int or not 1<=max_students<=8:
        raise ValueError('Limite trasferimenti non valido')
    base=UiDialogObjectPicker._MaxSelectableUnlimited
    if not callable(getattr(base,'get_max_selectable',None)):
        raise TypeError('Selettore EA non compatibile')

    class _TransferSeatCap(base):
        def get_max_selectable(self,*args,**kwargs):
            return max_students

    return _TransferSeatCap()


def _transfer_text(message):
    return lambda **_: LocalizationHelperTuning.get_raw_text(message)


def _transfer_notice(actor,title,body):
    _record('NOTIFY',title+': '+body)
    if actor is None:
        return False
    try:
        dialog=UiDialogNotification.TunableFactory().default(
            actor,title=_transfer_text(title),text=_transfer_text(body))
        dialog.show_dialog()
        return True
    except Exception as exc:
        _record('NOTICE_ERROR',type(exc).__name__)
        return False


def open_transfer_picker(source, destination, interaction):
    """M51: one native multiple-choice picker, ✓ commits; X never writes.

    It can transfer the entire source class in ONE click if the target has
    the seats, or any selected subset. Uses the same save-local JSON as M49.
    Does not alter the official High School Years attendance.
    """
    actor=_get_actor(interaction)
    try:
        slot=current_slot()
        _SETTINGS.require_management(slot,source)
        _SETTINGS.require_management(slot,destination)
        roster=_STORE.load(slot)
        source_ids=tuple(roster.class_members(source))
        if not source_ids:
            _transfer_notice(actor,'MY HIGH SCHOOL',
                'Classe {} non ha studenti da trasferire.'.format(source))
            return False
        free=8-len(roster.class_members(destination))
        if free<=0:
            _transfer_notice(actor,'MY HIGH SCHOOL - Classe completa',
                'Classe {}: nessun posto libero. Nessun trasferimento.'.format(destination))
            return False
        choices=candidate_rows(roster,source,_lookup_sim_info)
        if not choices:
            _transfer_notice(actor,'MY HIGH SCHOOL',
                'Studenti della Classe {} non disponibili nel gioco.'.format(source))
            return False
        if actor is None:
            _record('BLOCKED','Sim attivo non trovato')
            return False

        maximum=min(free,len(choices))
        original=roster_fingerprint(roster)
        allowed_ids={str(info.sim_id) for info in choices}
        dialog=UiSimPicker.TunableFactory().default(
            actor,
            title=_transfer_text('Trasferisci dalla Classe {} alla Classe {}'.format(
                source,destination)),
            text=_transfer_text(
                'Scegli fino a {} studenti della Classe {}. '
                'Posti liberi nella Classe {}: {}. '
                'Premi la spunta per trasferirli tutti insieme; '
                'X per annullare.'.format(maximum,source,destination,free)),
            max_selectable=_transfer_selection_strategy(maximum),
            min_selectable=1,should_show_names=True,
            hide_row_description=False)
        for info in choices:
            dialog.add_row(SimPickerRow(info.sim_id,False,tag=info.sim_id))
        handled=[False]

        def _selected(result):
            if handled[0]:
                return
            handled[0]=True
            if not getattr(result,'accepted',False):
                _record('CANCEL','Trasferimento annullato')
                return
            try:
                from mhs_m2_roster import canonical_sim_id
                chosen=tuple(canonical_sim_id(x)
                             for x in result.get_result_tags())
                if not 1<=len(chosen)<=maximum or len(set(chosen))!=len(chosen):
                    raise RosterError('Selezione non valida per i posti disponibili')
                if not set(chosen).issubset(allowed_ids):
                    raise RosterError('Selettore contiene studenti fuori dalla Classe {}'.format(source))
                if current_slot()!=slot:
                    raise RosterError('Partita cambiata dopo apertura menu')
                _SETTINGS.require_management(slot,source)
                _SETTINGS.require_management(slot,destination)
                latest=_STORE.load(slot)
                if roster_fingerprint(latest)!=original:
                    raise RosterError('Registro aggiornato: riapri il trasferimento')
                updated,plan=plan_transfer(
                    latest,source,destination,chosen,teenager_checker)
                # One atomic transaction, same policy as current registry.
                _STORE.save(slot,updated)
                _record('SAVED','{} studenti Classe {} -> {}'.format(
                    plan['moved'],source,destination))
                _transfer_notice(actor,'MY HIGH SCHOOL - Trasferimento completato',
                    '{} studenti trasferiti da Classe {} a Classe {}. '
                    'Ora: Classe {} {}/8, Classe {} {}/8.'.format(
                        plan['moved'],source,destination,
                        source,plan['from_size'],destination,plan['to_size']))
            except Exception as exc:
                _record('REJECTED',type(exc).__name__)
                _transfer_notice(actor,'MY HIGH SCHOOL - Nessuna modifica',
                    'Trasferimento non eseguito: {}'.format(str(exc)[:110]))

        dialog.add_listener(_selected)
        dialog.show_dialog()
        _record('OPEN','Classe {} -> {} | max {}'.format(
            source,destination,maximum))
        return True
    except Exception as exc:
        _record('ERROR','{}: {}'.format(type(exc).__name__,str(exc)[:105]))
        _transfer_notice(actor,'MY HIGH SCHOOL - Impossibile aprire',
            '{}'.format(str(exc)[:125]))
        return False


class MHS32Transfer1To2(ImmediateSuperInteraction):
    def _run_interaction_gen(self,timeline):
        open_transfer_picker(1,2,self)
        result=super()._run_interaction_gen(timeline)
        if inspect.isgenerator(result):
            return (yield from result)
        return result


class MHS32Transfer1To3(ImmediateSuperInteraction):
    def _run_interaction_gen(self,timeline):
        open_transfer_picker(1,3,self)
        result=super()._run_interaction_gen(timeline)
        if inspect.isgenerator(result):
            return (yield from result)
        return result


class MHS32Transfer2To1(ImmediateSuperInteraction):
    def _run_interaction_gen(self,timeline):
        open_transfer_picker(2,1,self)
        result=super()._run_interaction_gen(timeline)
        if inspect.isgenerator(result):
            return (yield from result)
        return result


class MHS32Transfer2To3(ImmediateSuperInteraction):
    def _run_interaction_gen(self,timeline):
        open_transfer_picker(2,3,self)
        result=super()._run_interaction_gen(timeline)
        if inspect.isgenerator(result):
            return (yield from result)
        return result


class MHS32Transfer3To1(ImmediateSuperInteraction):
    def _run_interaction_gen(self,timeline):
        open_transfer_picker(3,1,self)
        result=super()._run_interaction_gen(timeline)
        if inspect.isgenerator(result):
            return (yield from result)
        return result


class MHS32Transfer3To2(ImmediateSuperInteraction):
    def _run_interaction_gen(self,timeline):
        open_transfer_picker(3,2,self)
        result=super()._run_interaction_gen(timeline)
        if inspect.isgenerator(result):
            return (yield from result)
        return result


@sims4.commands.Command('mhs32.transferpreview',command_type=sims4.commands.CommandType.Live)
def mhs32_transferpreview(_connection=None):
    out=sims4.commands.CheatOutput(_connection)
    if not _PENDING:
        out('M32: nessun trasferimento preparato. {}'.format(_EVENTS[-1] if _EVENTS else ''))
        return
    try:
        slot=current_slot()
        if slot!=_PENDING['slot'] or roster_fingerprint(_STORE.load(slot))!=_PENDING['snapshot']:
            out('M32: partita o registro cambiati. Nessun dato scritto.')
            return
        out('M32 SOLO ANTEPRIMA: {} studenti da Classe {} verso Classe {}.'.format(
            _PENDING['moved'],_PENDING['source'],_PENDING['destination']))
        out('Rimarrebbero {}/8 in Classe {} e {}/8 in Classe {}.'.format(
            _PENDING['from_size'],_PENDING['source'],
            _PENDING['to_size'],_PENDING['destination']))
        for sid in _PENDING['selected']:
            out(' - {} | Sim ID {}'.format(_sim_label(sid),sid))
        out('Per confermare SOLO sul JSON TEST: mhs32.transfercommit conferma')
    except Exception as exc:
        out('M32 BLOCCATO: {}'.format(type(exc).__name__))


@sims4.commands.Command('mhs32.transfercommit',command_type=sims4.commands.CommandType.Live)
def mhs32_transfercommit(confirmation: str='',_connection=None):
    global _PENDING
    out=sims4.commands.CheatOutput(_connection)
    if str(confirmation or '').strip().casefold()!='conferma':
        out('Nessun dato scritto. Prima mhs32.transferpreview, poi mhs32.transfercommit conferma')
        return
    if _PENDING is None:
        out('Nessun trasferimento in sospeso.')
        return
    pending=_PENDING
    _PENDING=None
    try:
        slot=current_slot()
        if slot!=pending['slot']:
            raise RosterError('Salvataggio cambiato')
        old=_STORE.load(slot)
        if roster_fingerprint(old)!=pending['snapshot']:
            raise RosterError('Registro cambiato')
        updated,plan=plan_transfer(
            old,pending['source'],pending['destination'],
            pending['selected'],teenager_checker)
        _STORE.save(slot,updated)
        out('M32 REGISTRO TEST: {} studenti trasferiti da Classe {} a Classe {}.'.format(
            plan['moved'],plan['source'],plan['destination']))
        out('I Sim esistono ancora nel gioco. Frequenza scolastica EA non modificata.')
        _record('SAVED','{} -> {} | {}'.format(plan['source'],plan['destination'],plan['moved']))
    except Exception as exc:
        out('M32 TRASFERIMENTO BLOCCATO: {}'.format(str(exc)[:130]))
        _record('BLOCKED',type(exc).__name__)


@sims4.commands.Command('mhs32.transfercancel',command_type=sims4.commands.CommandType.Live)
def mhs32_transfercancel(_connection=None):
    global _PENDING
    _PENDING=None
    sims4.commands.CheatOutput(_connection)('Trasferimento annullato. Nessun dato scritto.')


@sims4.commands.Command('mhs32.report',command_type=sims4.commands.CommandType.Live)
def mhs32_report(_connection=None):
    out=sims4.commands.CheatOutput(_connection)
    out('M32 - ultime operazioni trasferimento:')
    for code,msg in _EVENTS[-8:]:
        out('{} | {}'.format(code,msg))
    out('Click e selezioni non scrivono il registro. Solo mhs32.transfercommit conferma.')
