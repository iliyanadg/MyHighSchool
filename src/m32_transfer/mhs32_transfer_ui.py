"""M32 transfers: six class-scoped native picker options, no automatic writes.

An explicit console confirmation changes only the external M25 TEST JSON.
The active EA high-school attendance and .save remain untouched.
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

_DATA_DIR = os.path.join(os.path.expanduser('~'), 'Documents',
                         'Electronic Arts', 'The Sims 4',
                         'MY_HIGH_SCHOOL_M25_TEST_DATA')
_STORE = RosterStore(_DATA_DIR)
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


def open_transfer_picker(source, destination, interaction):
    """Photo picker always shows only the members of the source class."""
    global _PENDING
    _PENDING=None
    try:
        slot=current_slot()
        roster=_STORE.load(slot)
        if not roster.class_members(source):
            _record('EMPTY','Classe {}: nessun iscritto'.format(source))
            return False
        free=8-len(roster.class_members(destination))
        if free<=0:
            _record('FULL','Classe {} piena. Usa il comando scambio coppia.'.format(destination))
            return False
        choices=candidate_rows(roster,source,_lookup_sim_info)
        if not choices:
            _record('BLOCKED','Iscritti non disponibili nel SimInfoManager')
            return False
        actor=_get_actor(interaction)
        if actor is None:
            _record('BLOCKED','Sim attivo non trovato')
            return False
        original=roster_fingerprint(roster)
        allowed_ids={str(info.sim_id) for info in choices}
        dialog=_dialog_factory(
            source, choices, actor,
            title_text='Trasferisci Classe {} verso Classe {}'.format(source,destination),
            description_text='Scegli iscritti di Classe {} ({} posti liberi in Classe {}). Nessun cambiamento finche non confermi dal registro TEST.'.format(source,free,destination))

        def _selected(result):
            global _PENDING
            _PENDING=None
            if not getattr(result,'accepted',False):
                _record('CANCEL','Trasferimento annullato')
                return
            try:
                chosen=tuple(result.get_result_tags())
                if not chosen:
                    raise RosterError('Nessuno studente selezionato')
                if not {str(x) for x in chosen}.issubset(allowed_ids):
                    raise RosterError('Selettore ha restituito un Sim fuori classe')
                if current_slot()!=slot:
                    raise RosterError('Salvataggio cambiato')
                latest=_STORE.load(slot)
                if roster_fingerprint(latest)!=original:
                    raise RosterError('Registro cambiato dopo apertura picker')
                _updated,plan=plan_transfer(latest,source,destination,
                                            chosen,teenager_checker)
                plan['snapshot']=original
                _PENDING=plan
                _record('READY','{} studenti da Classe {} a Classe {}. Usa mhs32.transferpreview'.format(
                    plan['moved'],source,destination))
            except Exception as exc:
                _record('BLOCKED','{}: {}'.format(type(exc).__name__,str(exc)[:95]))

        dialog.add_listener(_selected)
        dialog.show_dialog()
        _record('OPEN','Classe {} -> {} | {} candidati'.format(source,destination,len(choices)))
        return True
    except Exception as exc:
        _record('ERROR','{}: {}'.format(type(exc).__name__,str(exc)[:105]))
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
