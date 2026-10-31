"""M55 automatic full-roster school invitations.

Loaded from the M55 native interaction tuning. A conservative Zone-ready
hook starts ONE in-game repeating alarm. When a genuine EA school student
situation is active, it freezes the current class roster and sends invited
students to the EA Base Student job in small batches. No menu clicks required.

Test-save prototype: EA may reject a request or autonomously spawn its own
NPC pupils; neither actual arrival nor 3rd-room routing is guaranteed.
"""
import os
import alarms
import services
from date_and_time import create_time_span, sim_ticks_per_day
from sims.sim_info_types import Age, Species
from ui.ui_dialog_notification import UiDialogNotification
from sims4.localization import LocalizationHelperTuning

from mhs_m2_game_bridge import current_slot
from mhs_m2_store import RosterStore
from mhs34_settings import SettingsStore
from mhs55_attendance_core import (
    DailyAttendance, AttendanceError, roster_plan, valid_student,
    school_running, already_in_base_student, create_student_request,
    BASE_STUDENT_SITUATION, BASE_STUDENT_JOB)

_ROOT = os.path.join(os.path.expanduser('~'), 'Documents', 'Electronic Arts',
                     'The Sims 4', 'MY_HIGH_SCHOOL_M25_TEST_DATA')
_ROSTERS = RosterStore(_ROOT)
_SETTINGS = SettingsStore(_ROOT)
_HANDLE = None
_ZONE = None
_SESSION = None
_HOOK_STATE = 'non ancora installato'
_LAST_EVENT = 'In attesa di una giornata scolastica EA'
_EVENTS = []
_BATCH = 3
_POLL_MINUTES = 5


def _event(kind, message=''):
    global _LAST_EVENT
    _LAST_EVENT = '{}: {}'.format(kind, str(message)[:170])
    _EVENTS.append(_LAST_EVENT)
    del _EVENTS[:-25]


def _notice(title, message):
    try:
        client = services.client_manager().get_first_client()
        actor = getattr(client, 'active_sim', None)
        if actor is None:
            return
        txt = lambda text:lambda **_:LocalizationHelperTuning.get_raw_text(str(text))
        dialog = UiDialogNotification.TunableFactory().default(
            actor, title=txt(title), text=txt(message))
        dialog.show_dialog()
    except Exception as exc:
        _event('AVVISO_NON_MOSTRATO', type(exc).__name__)


def _game_day():
    service = services.time_service()
    now = getattr(service, 'sim_now', None)
    ticks = None
    if now is not None:
        for name in ('absolute_ticks', 'in_ticks'):
            method = getattr(now, name, None)
            if callable(method):
                try:
                    ticks = int(method())
                    break
                except (ValueError, TypeError, AttributeError):
                    pass
    total = sim_ticks_per_day()
    if ticks is None or not total:
        raise AttendanceError('Orologio EA non verificabile')
    return ticks // int(total)


def _zone_id(zone):
    value = getattr(zone, 'id', None)
    if value is None:
        value = getattr(zone, 'zone_id', None)
    if value is None:
        raise AttendanceError('Identificativo lotto non disponibile')
    return str(value)


def _ea_resources():
    from sims4.resources import Types
    from situations.situation_guest_list import (
        SituationGuestList, SituationGuestInfo, SituationInvitationPurpose)
    sit_mgr = services.get_instance_manager(Types.SITUATION)
    job_type = getattr(Types, 'SITUATION_JOB', None)
    job_mgr = services.get_instance_manager(job_type) if job_type is not None else None
    situation = sit_mgr.get(BASE_STUDENT_SITUATION) if sit_mgr else None
    job = job_mgr.get(BASE_STUDENT_JOB) if job_mgr else None
    if (situation is None or job is None or
            int(getattr(situation, 'guid64', -1)) != BASE_STUDENT_SITUATION or
            int(getattr(job, 'guid64', -1)) != BASE_STUDENT_JOB):
        raise AttendanceError('Espansione Vita da Liceali: risorse studente EA assenti')
    return situation, job, SituationGuestList, SituationGuestInfo, SituationInvitationPurpose.INVITED


def _is_playable_household(info):
    """Never coerce the active household's teens into a background NPC job."""
    try:
        household = services.active_household()
        return (household is not None
                and getattr(info, 'household_id', None) == getattr(household, 'id', None))
    except Exception:
        return False


def _process(session, situation_mgr, sim_mgr):
    """One small batch per Sim alarm: at most three EA situation calls."""
    try:
        tuning, job, guestlist, guestinfo, purpose = _ea_resources()
    except Exception as exc:
        _event('EP12_BLOCCO', str(exc))
        # No invitation if EP12 or an API is unavailable.
        for klass, sid in session.next_batch(_BATCH):
            session.record(sid, 'failed')
        return

    for klass, sid in session.next_batch(_BATCH):
        try:
            info = sim_mgr.get(int(sid))
            if not valid_student(info, Age.TEEN, Species.HUMAN):
                session.record(sid, 'missing')
                continue
            if _is_playable_household(info):
                session.record(sid, 'playable')
                continue
            if already_in_base_student(situation_mgr, info):
                session.record(sid, 'present')
                continue
            create_student_request(situation_mgr, info, tuning, job,
                                   guestlist, guestinfo, purpose)
            session.record(sid, 'requested')
        except Exception as exc:
            session.record(sid, 'failed')
            _event('INVITO_FALLITO', 'Classe {} / Sim {}: {}'.format(
                klass, sid, type(exc).__name__))


def _tick(_handle=None):
    global _SESSION
    try:
        zone = services.current_zone()
        if zone is None or zone is not _ZONE:
            return
        slot = current_slot()  # Fail closed on 0 (unknown travel slot).
        settings = _SETTINGS.load(slot)
        if not settings.active:
            return
        day = _game_day()
        current = _SESSION
        if current is not None and current.same_session(slot, _zone_id(zone), day):
            if current.done:
                return
        situation_mgr = services.get_zone_situation_manager()
        sim_mgr = services.sim_info_manager()
        if situation_mgr is None or sim_mgr is None:
            return
        if not school_running(situation_mgr, sim_mgr.get_all(), Age.TEEN):
            return
        if current is None or not current.same_session(slot, _zone_id(zone), day):
            roster = _ROSTERS.load(slot)
            planned, invalid = roster_plan(
                roster, settings.class_count, sim_mgr.get, Age.TEEN, Species.HUMAN)
            _SESSION = DailyAttendance(slot, _zone_id(zone), day, planned, invalid)
            _event('GIORNATA_INIZIATA', 'Iscritti idonei {} / non idonei {}'.format(
                len(planned), len(invalid)))
        current = _SESSION
        if not current.done:
            _process(current, situation_mgr, sim_mgr)
            if current.done:
                counts = current.summary()
                _event('GIORNATA_ELABORATA', str(counts))
                _notice('MY HIGH SCHOOL - Presenze automatiche',
                        'Elaborati {} studenti. Richieste EA: {}. '
                        'Gia presenti: {}. Giocabili: {}. '
                        'Errori: {}. Verifica arrivo in gioco.'.format(
                            counts['total'], counts['requested'],
                            counts['present'], counts['playable'],
                            counts['failed'] + counts['missing'] + counts['ineligible']))
    except Exception as exc:
        # Retain the school session; do not loop unsafe retries.
        _event('ATTESA_O_BLOCCO', '{}: {}'.format(type(exc).__name__, str(exc)[:95]))


def _start_zone(zone):
    global _HANDLE, _ZONE, _SESSION
    if _HANDLE is not None:
        try:
            alarms.cancel_alarm(_HANDLE)
        except Exception:
            pass
    _HANDLE = None
    _ZONE = zone
    _SESSION = None
    interval = create_time_span(minutes=_POLL_MINUTES)
    _HANDLE = alarms.add_alarm(
        zone, interval, _tick, repeating=True, repeat_interval=interval)
    _event('CONTROLLO_AVVIATO', 'Verifica scuola automatica ogni {} minuti Sim'.format(
        _POLL_MINUTES))


def _install_zone_hook():
    global _HOOK_STATE
    try:
        from zone import Zone
        original = getattr(Zone, 'on_loading_screen_animation_finished', None)
        if not callable(original):
            raise AttendanceError('Hook fine caricamento zona non trovato')
        if getattr(original, '_mhs55_attendance_hook', False):
            _HOOK_STATE = 'gia installato'
            return

        def _mhs55_after_loading(zone, *args, **kwargs):
            result = original(zone, *args, **kwargs)
            try:
                _start_zone(zone)
            except Exception as exc:
                _event('HOOK_ERRORE', type(exc).__name__)
            return result

        _mhs55_after_loading._mhs55_attendance_hook = True
        Zone.on_loading_screen_animation_finished = _mhs55_after_loading
        _HOOK_STATE = 'installato'
    except Exception as exc:
        _HOOK_STATE = 'non installato: {}'.format(type(exc).__name__)
        _event('HOOK_ASSENTE', _HOOK_STATE)


def status_lines():
    result = ['Automazione M55: {}'.format(_HOOK_STATE), _LAST_EVENT]
    if _SESSION is None:
        result.append('Giornata liceale: non ancora rilevata')
    else:
        c = _SESSION.summary()
        result.extend([
            'Slot {} / Giorno Sim {}'.format(_SESSION.slot, _SESSION.day),
            'Iscritti previsti: {} / convocazioni richieste: {}'.format(
                c['total'], c['requested']),
            'Gia in situazione EA: {} / giocabili: {}'.format(
                c['present'], c['playable']),
            'Non idonei: {} / non trovati: {} / falliti: {} / da elaborare: {}'.format(
                c['ineligible'], c['missing'], c['failed'], c['pending']),
            'Il gioco EA puo comunque aggiungere NPC suoi. '
            'Una richiesta non garantisce che lo studente sia fisicamente presente.'
        ])
    return '\n'.join(result)


_install_zone_hook()
