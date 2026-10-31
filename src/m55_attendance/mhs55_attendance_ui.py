"""M55 Mac TEST: native-prompt, ONE explicitly selected enrolled teen.

This is NOT an automatic attendance controller. The choice is offered under
Class 1 in the verified mailbox/PC menu. M54's existing interactions, staff
registry, 10 categories and Lot51 SimData remain unmodified.
"""
import inspect
import os

import services
from interactions.base.immediate_interaction import ImmediateSuperInteraction
from sims.sim_info_types import Age, Species
from sims4.localization import LocalizationHelperTuning
from ui.ui_dialog_picker import UiSimPicker, SimPickerRow, UiDialogObjectPicker
from ui.ui_dialog_notification import UiDialogNotification

from mhs_m2_game_bridge import current_slot
from mhs_m2_store import RosterStore
from mhs34_settings import SettingsStore
from mhs55_attendance_core import (
    AttendanceError, BASE_STUDENT_JOB, BASE_STUDENT_SITUATION,
    valid_student, select_one, school_running, already_in_base_student,
    create_single_student_situation)

_FOLDER = os.path.join(os.path.expanduser('~'), 'Documents', 'Electronic Arts',
                       'The Sims 4', 'MY_HIGH_SCHOOL_M25_TEST_DATA')
_ROSTERS = RosterStore(_FOLDER)
_SETTINGS = SettingsStore(_FOLDER)
_ATTEMPTED = set()
_EVENTS = []


def _record(kind, detail=''):
    _EVENTS.append((kind, str(detail)[:130]))
    del _EVENTS[:-25]


def _text(value):
    return lambda **_: LocalizationHelperTuning.get_raw_text(str(value))


def _actor(interaction):
    actor = getattr(interaction, 'sim', None)
    if actor is not None:
        return actor
    try:
        return services.client_manager().get_first_client().active_sim
    except Exception:
        return None


def _notice(actor, title, detail):
    _record('NOTICE', title + ' | ' + detail)
    if actor is None:
        return
    try:
        dialog = UiDialogNotification.TunableFactory().default(
            actor, title=_text(title), text=_text(detail))
        dialog.show_dialog()
    except Exception as exc:
        _record('NOTIFY_FAIL', type(exc).__name__)


def _one_selection():
    base = UiDialogObjectPicker._MaxSelectableUnlimited
    if not callable(getattr(base, 'get_max_selectable', None)):
        raise AttendanceError('Selettore EA non compatibile')

    class _One(base):
        def get_max_selectable(self, *args, **kwargs):
            return 1
    return _One()


def _eligible_infos(roster):
    manager = services.sim_info_manager()
    if manager is None:
        raise AttendanceError('Archivio Sim indisponibile')
    infos = []
    for sid in roster.class_members(1):
        info = manager.get(int(sid))
        if valid_student(info, Age.TEEN, Species.HUMAN):
            infos.append(info)
    return infos


def _attempt_one(slot, sid, expected_roster):
    """Recheck all invariants AFTER picker checkmark, BEFORE EA mutation."""
    if current_slot() != slot:
        raise AttendanceError('Partita non verificabile al liceo; nessuna convocazione')
    _SETTINGS.require_management(slot, 1)
    roster = _ROSTERS.load(slot)
    if roster.to_json() != expected_roster or sid not in roster.class_members(1):
        raise AttendanceError('Registro modificato: riapri il selettore')

    manager = services.sim_info_manager()
    if manager is None:
        raise AttendanceError('Archivio Sim non disponibile')
    info = manager.get(int(sid))
    if not valid_student(info, Age.TEEN, Species.HUMAN):
        raise AttendanceError('Studente non piu idoneo')
    situations = services.get_zone_situation_manager()
    if situations is None:
        raise AttendanceError('Gestore situazioni EA non disponibile')
    # Real-life school-lot / active-school-day proxy, not a lot-ID guess.
    if not school_running(situations, manager.get_all(), Age.TEEN):
        raise AttendanceError('Giornata liceo EA non rilevata: prova a scuola')
    if already_in_base_student(situations, info):
        return 'GIA_PRESENTE', None
    key = (slot, sid)
    if key in _ATTEMPTED:
        raise AttendanceError('Un tentativo gia effettuato in questa sessione')

    from sims4.resources import Types
    from situations.situation_guest_list import (
        SituationGuestList, SituationGuestInfo, SituationInvitationPurpose)
    situ_mgr = services.get_instance_manager(Types.SITUATION)
    job_type = getattr(Types, 'SITUATION_JOB', None)
    if job_type is None:
        raise AttendanceError('Tipo lavoro situazione EA non disponibile')
    job_mgr = services.get_instance_manager(job_type)
    situ_tuning = situ_mgr.get(BASE_STUDENT_SITUATION) if situ_mgr else None
    job_tuning = job_mgr.get(BASE_STUDENT_JOB) if job_mgr else None

    # A failed attempt is not automatically repeated. User checks what happened.
    # Mark immediately before the only create_situation call.
    if (situ_tuning is None or job_tuning is None or
            int(getattr(situ_tuning, 'guid64', -1)) != BASE_STUDENT_SITUATION or
            int(getattr(job_tuning, 'guid64', -1)) != BASE_STUDENT_JOB or
            not callable(getattr(situations, 'create_situation', None))):
        raise AttendanceError('Tuning EP12 non rilevati; nessuna convocazione')
    _ATTEMPTED.add(key)
    result = create_single_student_situation(
        situations, info, situ_tuning, job_tuning,
        SituationGuestList, SituationGuestInfo, SituationInvitationPurpose.INVITED)
    return 'RICHIESTA_INVIATA', result


def open_m55_picker(interaction):
    actor = _actor(interaction)
    try:
        slot = current_slot()
        _SETTINGS.require_management(slot, 1)
        roster = _ROSTERS.load(slot)
        candidates = _eligible_infos(roster)
        if not candidates:
            _notice(actor, 'M55 - Presenze liceo',
                    'Nessun adolescente umano iscritto in Classe 1. '
                    'Iscrivilo prima nel registro.')
            return False
        offered = {str(i.sim_id) for i in candidates}
        frozen = roster.to_json()
        dlg = UiSimPicker.TunableFactory().default(
            actor, title=_text('M55 TEST - Convoca 1 studente Classe 1'),
            text=_text('SOLO SALVATAGGIO DI PROVA. Scegli UN iscritto, '
                       'poi premi la spunta. La X annulla. '
                       'La presenza reale non e ancora garantita.'),
            max_selectable=_one_selection(), min_selectable=1,
            should_show_names=True, hide_row_description=False)
        for info in candidates:
            dlg.add_row(SimPickerRow(info.sim_id, False, tag=info.sim_id))
        called = [False]

        def on_answer(answer):
            if called[0]:
                return
            called[0] = True
            if not getattr(answer, 'accepted', False):
                _record('CANCEL')
                return
            try:
                sid = select_one(roster.class_members(1), offered,
                                 tuple(answer.get_result_tags()))
                outcome, eid = _attempt_one(slot, sid, frozen)
                if outcome == 'GIA_PRESENTE':
                    message = 'Lo studente e gia nella situazione studente EA. Nessun doppione.'
                else:
                    message = ('Richiesta inviata (ID {}). Verifica se compare davvero '
                               'a scuola. NON equivale a presenza confermata.').format(eid)
                _notice(actor, 'M55 - Risultato prova studente', message)
                _record(outcome, sid)
            except Exception as exc:
                _notice(actor, 'M55 - Nessuna convocazione confermata',
                        '{}: {}'.format(type(exc).__name__, str(exc)[:115]))
                _record('BLOCK', type(exc).__name__)
        dlg.add_listener(on_answer)
        dlg.show_dialog()
        _record('OPEN', str(slot))
        return True
    except Exception as exc:
        _record('ERROR', type(exc).__name__)
        _notice(actor, 'M55 - Test non disponibile', str(exc)[:155])
        return False


class MHS55TryOne(ImmediateSuperInteraction):
    def _run_interaction_gen(self, timeline):
        open_m55_picker(self)
        response = super()._run_interaction_gen(timeline)
        if inspect.isgenerator(response):
            return (yield from response)
        return response
