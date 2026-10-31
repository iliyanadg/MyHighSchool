"""M29 cumulative test-register tools: photos, audit, cleanup and undo.

Does not touch .save files, school situations, EA roles or Sim existence.
The only writes are explicit commands to the external M25 test JSON.
"""
import inspect
import os

import sims4.commands
from interactions.base.immediate_interaction import ImmediateSuperInteraction
from mhs_m2_game_bridge import current_slot, teenager_checker
from mhs_m2_roster import SchoolRoster, RosterError, canonical_sim_id
from mhs_m2_store import RosterStore
from mhs26_remove import candidate_rows, roster_fingerprint
from mhs27_remove_ui import _lookup_sim_info, _dialog_factory
from mhs28_controls import _sim_label

_DATA_DIR = os.path.join(os.path.expanduser('~'), 'Documents',
                         'Electronic Arts', 'The Sims 4',
                         'MY_HIGH_SCHOOL_M25_TEST_DATA')
_STORE = RosterStore(_DATA_DIR)
_PENDING_CLEANUP = None
_UI_EVENTS = []


def inspect_roster(roster, lookup, teenager):
    """Return exact class rosters and members invalid for continued enrollment.

    Missing SimInfo and no-longer-teen SimInfo are distinguished. Read only.
    """
    if not isinstance(roster, SchoolRoster):
        raise RosterError('Registro non valido')
    if not callable(lookup) or not callable(teenager):
        raise RosterError('Verifica Sim non disponibile')
    rows = {}
    invalid = []
    for klass in (1, 2, 3):
        members = roster.class_members(klass)
        rows[klass] = tuple(members)
        for sid in members:
            sim = lookup(sid)
            if sim is None:
                invalid.append((sid, klass, 'Sim non trovato'))
                continue
            try:
                is_teen = teenager(sid) is True
            except Exception:
                # Unknown lookup status is not evidence of graduating.
                raise RosterError('Verifica adolescenza fallita per {}'.format(sid))
            if not is_teen:
                invalid.append((sid, klass, 'Non piu adolescente'))
    return {'classes':rows, 'invalid':tuple(invalid),
            'enrolled':sum(len(x) for x in rows.values())}


def _describe(roster, out):
    survey = inspect_roster(roster, _lookup_sim_info, teenager_checker)
    out('MY HIGH SCHOOL - controllo registro TEST (slot {})'.format(roster.slot))
    for klass in (1, 2, 3):
        out('Classe {}: {}/8 iscritti'.format(klass,len(survey['classes'][klass])))
    for sid, klass, reason in survey['invalid']:
        out('ATTENZIONE | {} | Classe {} | ID {} | {}'.format(
            _sim_label(sid), klass, sid, reason))
    if not survey['invalid']:
        out('Nessun iscritto mancante o non adolescente rilevato.')
    return survey


def _get_actor(interaction):
    actor = getattr(interaction,'sim',None)
    if actor is not None:
        return actor
    import services
    client = services.client_manager().get_first_client()
    return getattr(client,'active_sim',None)


def open_view_picker(klass, interaction):
    """Photo-based, class-filtered read-only overview; no callback writes."""
    try:
        roster = _STORE.load(current_slot(allow_travel=True))
        choices = candidate_rows(roster,klass,_lookup_sim_info)
        if not choices:
            _UI_EVENTS.append('EMPTY | Classe {}'.format(klass))
            return False
        actor = _get_actor(interaction)
        if actor is None:
            _UI_EVENTS.append('NO ACTOR | Classe {}'.format(klass))
            return False
        # Reuse the M27 native picker factory, with distinct read-only copy.
        dialog = _dialog_factory(
            klass, choices, actor,
            title_text='Consulta iscritti - Classe {}'.format(klass),
            description_text='SOLO CONSULTAZIONE: scegliere un Sim non modifica il registro.')
        dialog.show_dialog()
        _UI_EVENTS.append('OPEN | Classe {} | {} iscritti'.format(klass,len(choices)))
        return True
    except Exception as exc:
        _UI_EVENTS.append('ERROR | {} | {}'.format(type(exc).__name__,str(exc)[:90]))
        return False


class MHS29ViewClass1(ImmediateSuperInteraction):
    def _run_interaction_gen(self, timeline):
        open_view_picker(1,self)
        base = super()._run_interaction_gen(timeline)
        if inspect.isgenerator(base):
            return (yield from base)
        return base


class MHS29ViewClass2(ImmediateSuperInteraction):
    def _run_interaction_gen(self, timeline):
        open_view_picker(2,self)
        base = super()._run_interaction_gen(timeline)
        if inspect.isgenerator(base):
            return (yield from base)
        return base


class MHS29ViewClass3(ImmediateSuperInteraction):
    def _run_interaction_gen(self, timeline):
        open_view_picker(3,self)
        base = super()._run_interaction_gen(timeline)
        if inspect.isgenerator(base):
            return (yield from base)
        return base


@sims4.commands.Command('mhs29.report', command_type=sims4.commands.CommandType.Live)
def mhs29_report(_connection=None):
    out=sims4.commands.CheatOutput(_connection)
    out('M29 - eventi consultazione registro:')
    for event in _UI_EVENTS[-8:]:
        out(event)
    out('Un click sulla foto in CONSULTA non modifica il registro.')


@sims4.commands.Command('mhs29.audit', command_type=sims4.commands.CommandType.Live)
def mhs29_audit(_connection=None):
    out=sims4.commands.CheatOutput(_connection)
    try:
        _describe(_STORE.load(current_slot()),out)
        out('Sola lettura. Non e stato rimosso nessuno studente.')
    except Exception as exc:
        out('M29 AUDIT BLOCCATO: {}'.format(str(exc)[:130]))


@sims4.commands.Command('mhs29.find', command_type=sims4.commands.CommandType.Live)
def mhs29_find(query: str='', _connection=None):
    out=sims4.commands.CheatOutput(_connection)
    name=str(query or '').strip().casefold()
    if not name:
        out('Scrivi: mhs29.find Nome')
        return
    try:
        roster=_STORE.load(current_slot())
        found=0
        for klass in (1,2,3):
            for sid in roster.class_members(klass):
                label=_sim_label(sid)
                if name in label.casefold() or name==sid:
                    out('{} | Classe {} | Sim ID {}'.format(label,klass,sid))
                    found+=1
        if not found:
            out('Nessun iscritto corrisponde alla ricerca "{}".'.format(name))
    except Exception as exc:
        out('M29 RICERCA BLOCCATA: {}'.format(type(exc).__name__))


@sims4.commands.Command('mhs29.cleanpreview', command_type=sims4.commands.CommandType.Live)
def mhs29_cleanpreview(_connection=None):
    global _PENDING_CLEANUP
    _PENDING_CLEANUP=None
    out=sims4.commands.CheatOutput(_connection)
    try:
        slot=current_slot()
        roster=_STORE.load(slot)
        audit=_describe(roster,out)
        ids=tuple(sid for sid,klass,reason in audit['invalid'])
        if not ids:
            out('Nessuna rimozione necessaria.')
            return
        _PENDING_CLEANUP={'slot':slot,'ids':ids,
                          'snapshot':roster_fingerprint(roster)}
        out('RIMOZIONE SOLO PREPARATA: {} iscritti non idonei.'.format(len(ids)))
        out('Nessun Sim cancellato. Per aggiornare il JSON TEST: mhs29.cleancommit conferma')
    except Exception as exc:
        out('M29 PULIZIA BLOCCATA: {}'.format(str(exc)[:130]))


@sims4.commands.Command('mhs29.cleancommit', command_type=sims4.commands.CommandType.Live)
def mhs29_cleancommit(confirmation: str='', _connection=None):
    global _PENDING_CLEANUP
    out=sims4.commands.CheatOutput(_connection)
    if str(confirmation or '').strip().casefold()!='conferma':
        out('Nessuna modifica. Usa mhs29.cleancommit conferma nella partita TEST.')
        return
    if not _PENDING_CLEANUP:
        out('Nessuna pulizia preparata.')
        return
    pending=_PENDING_CLEANUP
    _PENDING_CLEANUP=None
    try:
        slot=current_slot()
        if slot!=pending['slot']:
            raise RosterError('Salvataggio cambiato')
        roster=_STORE.load(slot)
        if roster_fingerprint(roster)!=pending['snapshot']:
            raise RosterError('Registro modificato: ripetere la verifica')
        audit=inspect_roster(roster,_lookup_sim_info,teenager_checker)
        current_ids=tuple(sid for sid,klass,reason in audit['invalid'])
        if current_ids!=pending['ids']:
            raise RosterError('Stato degli studenti cambiato: ripetere la verifica')
        updated=SchoolRoster(slot,{sid:klass
            for sid,klass in roster.assignments.items() if sid not in current_ids})
        _STORE.save(slot,updated)
        out('M29 REGISTRO TEST: {} iscrizioni non idonee rimosse.'.format(len(current_ids)))
        out('Sim non eliminati. Usa mhs29.undo conferma per annullare la modifica.')
    except Exception as exc:
        out('M29 PULIZIA NON ESEGUITA: {}'.format(str(exc)[:130]))


@sims4.commands.Command('mhs29.cleancancel', command_type=sims4.commands.CommandType.Live)
def mhs29_cleancancel(_connection=None):
    global _PENDING_CLEANUP
    _PENDING_CLEANUP=None
    sims4.commands.CheatOutput(_connection)('Pulizia annullata senza scrittura.')


@sims4.commands.Command('mhs29.undo', command_type=sims4.commands.CommandType.Live)
def mhs29_undo(confirmation: str='', _connection=None):
    out=sims4.commands.CheatOutput(_connection)
    if str(confirmation or '').strip().casefold()!='conferma':
        out('Per annullare solo L ULTIMA modifica al JSON TEST: mhs29.undo conferma')
        return
    try:
        slot=current_slot()
        before=_STORE.undo_last(slot)
        out('ULTIMA MODIFICA ANNULLATA nel registro esterno slot {}.'.format(slot))
        out('Iscritti ripristinati: {}. Salvataggio EA invariato.'.format(len(before.assignments)))
    except Exception as exc:
        out('ANNULLAMENTO BLOCCATO: {}'.format(str(exc)[:130]))
