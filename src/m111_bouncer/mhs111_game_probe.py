"""M111 Mac: opt-in read-only native EA school job snapshot.

Unlike M110, this diagnostic installs NO runtime method wrappers,
does not change situations, request filters, tuning, Sims or the save.
The M54/M57 save-scoped registry JSON is read from disk but never edited.
Arm at home; check once at school. It does NOT prove Bouncer completion,
full-day attendance or classroom seating.
"""
import json
import os
import services
import sims4.commands
from date_and_time import sim_ticks_per_day
from mhs_m2_game_bridge import current_slot
from mhs111_live_school_bridge import inspect_current_school_ea_jobs

DIR = os.path.join(os.path.expanduser('~'), 'Documents',
                   'Electronic Arts', 'The Sims 4',
                   'MY_HIGH_SCHOOL_M25_TEST_DATA')
FILE = 'MHS_M111_NATIVE_SCHOOL_JOB_READBACK.json'
_ARMED = None
_LAST = None


def _day():
    service = services.time_service()
    now = service.sim_now
    return int(now.absolute_ticks()) // int(sim_ticks_per_day())


def _zone():
    zone = services.current_zone()
    zone_id = getattr(zone, 'id', None)
    return zone_id if type(zone_id) is int and zone_id > 0 else None


def _write(report):
    # Writes a diagnostic report only; no game tuning, registry or save.
    os.makedirs(DIR, exist_ok=True)
    target = os.path.join(DIR, FILE)
    temporary = target + '.tmp'
    with open(temporary, 'w', encoding='utf-8') as stream:
        json.dump(report, stream, indent=2, sort_keys=True)
    os.replace(temporary, target)


def _unknown(status, **fields):
    return dict(kind='M111_OPT_IN_EA_JOB_READ_ONLY',
                status=status,
                game_modified=False,
                original_ea_methods_wrapped=False,
                exact_16_native_membership_verified=False,
                post_bouncer_barrier_verified=False,
                full_school_day_verified=False,
                two_classroom_seating_verified=False, **fields)


def arm():
    """Anchor exact save/day/home zone; do not touch any EA method."""
    global _ARMED
    if _ARMED is not None:
        return 'M111 gia preparata. Usa mhs111.check al liceo.'
    try:
        from mhs111_live_school_bridge import SCHOOL_SCHEDULES
        zone = _zone()
        if zone is None:
            return 'M111 BLOCCATA: lotto attuale non disponibile.'
        # Explicit home precondition, original EA school schedule only.
        venue = services.venue_service()
        director = venue.get_zone_director() if venue else None
        schedule = getattr(director, '_schedule', None)
        if getattr(schedule, 'guid64', None) in SCHOOL_SCHEDULES:
            return 'M111 BLOCCATA: prepara il test da casa, non dal liceo.'
        slot = str(current_slot(allow_travel=False))
        day = _day()
        if not slot.isdigit() or day < 0:
            return 'M111 BLOCCATA: salvataggio/giorno non verificato.'
        _ARMED = (slot, day, zone)
        return ('M111 PRONTA: nessun metodo EA modificato. '
                'Al liceo, durante la lezione, usa mhs111.check.')
    except Exception as exc:
        return 'M111 NON PREPARATA: ' + type(exc).__name__


def check():
    """One read-only snapshot; never pretend callback has been verified."""
    global _LAST
    if _ARMED is None:
        return 'M111 NON PREPARATA. Da casa usa mhs111.arm.'
    try:
        slot, day, home_zone = _ARMED
        now_slot = str(current_slot(allow_travel=True))
        current_day = _day()
        current_zone = _zone()
        if now_slot != slot or current_day != day:
            _LAST = _unknown('WRONG_SAVE_OR_GAME_DAY')
        elif current_zone is None or current_zone == home_zone:
            _LAST = _unknown('NOT_TRAVELLED_TO_SCHOOL')
        else:
            # The caller asks for the lesson-stage snapshot. Its *actual*
            # in-game time and Bouncer barrier are NOT proven by this API.
            _LAST = inspect_current_school_ea_jobs('lesson')
            _LAST['kind'] = 'M111_OPT_IN_EA_JOB_READ_ONLY'
            _LAST['phase_selected_by_user_not_game_verified'] = True
        _LAST['capture_same_save_day'] = (
            now_slot == slot and current_day == day)
        _LAST['captured_game_day'] = current_day
        _LAST['no_ea_hooks_installed_by_m111'] = True
        _write(_LAST)
        return ('M111 REPORT: {}. '
                'Ruoli letti senza modificare Sim o lezioni. '
                'Invia {}'.format(_LAST['status'], FILE))
    except Exception as exc:
        _LAST = _unknown('EA_JOB_SNAPSHOT_ERROR',
                         error_type=type(exc).__name__)
        try:
            _write(_LAST)
        except Exception:
            pass
        return 'M111 ERRORE LETTURA: ' + type(exc).__name__


def status():
    if _ARMED is None:
        return 'M111 NON PREPARATA: avvia da casa.'
    if _LAST is None:
        return 'M111 PRONTA: in attesa di un controllo al liceo.'
    return 'M111: ' + _LAST['status'] + ' | ' + FILE


@sims4.commands.Command('mhs111.arm',
                        command_type=sims4.commands.CommandType.Live)
def _command_arm(_connection=None):
    sims4.commands.output(arm(), _connection)


@sims4.commands.Command('mhs111.check',
                        command_type=sims4.commands.CommandType.Live)
def _command_check(_connection=None):
    sims4.commands.output(check(), _connection)


@sims4.commands.Command('mhs111.status',
                        command_type=sims4.commands.CommandType.Live)
def _command_status(_connection=None):
    sims4.commands.output(status(), _connection)
