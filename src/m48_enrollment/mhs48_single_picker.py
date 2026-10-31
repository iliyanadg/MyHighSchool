"""M48: one native Sim Picker, one confirmation (the existing checkmark).

User-approved flow:
MY HIGH SCHOOL -> Class N -> Iscrivi students -> choose up to 8 teens
-> native picker checkmark immediately enrolls / X never writes.

The proven M45 category tree and visibility remain untouched. No separate
UiDialogOkCancel, no console command. Only the external TEST roster JSON
is affected after a verified native picker acceptance, using M46's
same-slot/class/capacity/stale-roster safety checks.

Compatibility of programmatically created UiSimPicker needs Mac test.
This module does NOT alter real EA High School Years attendance.
"""
import inspect
import os

import services
from sims.sim_info_types import Age
from sims4.localization import LocalizationHelperTuning
from interactions.base.immediate_interaction import ImmediateSuperInteraction
from ui.ui_dialog_picker import UiSimPicker, SimPickerRow, UiDialogObjectPicker
from ui.ui_dialog_notification import UiDialogNotification

from mhs_m2_game_bridge import current_slot, teenager_checker
from mhs_m2_roster import canonical_sim_id
from mhs_m2_store import RosterStore
from mhs34_settings import SettingsStore
from mhs46_enrollment_transaction import preview_enrollment, confirm_enrollment
from mhs39_visibility_ui import _MHS39VisibilityMixin

_DIR=os.path.join(os.path.expanduser('~'),'Documents','Electronic Arts',
                  'The Sims 4','MY_HIGH_SCHOOL_M25_TEST_DATA')
_ROSTERS=RosterStore(_DIR)
_SETTINGS=SettingsStore(_DIR)
_EVENTS=[]


def _record(action,details=''):
    _EVENTS.append((action,str(details)[:160]))
    del _EVENTS[:-20]


def _text(value):
    return lambda **_: LocalizationHelperTuning.get_raw_text(str(value))


def _notify(actor,title,message):
    _record('NOTIFY',title+': '+message)
    try:
        dlg=UiDialogNotification.TunableFactory().default(
            actor,title=_text(title),text=_text(message))
        dlg.show_dialog()
        return True
    except Exception as exc:
        _record('NOTIFY_FAILED',type(exc).__name__)
        return False


def _teens():
    manager=services.sim_info_manager()
    if manager is None:
        raise ValueError('Elenco adolescenti non disponibile')
    selected={}
    for sim in manager.get_all():
        if sim is None or getattr(sim,'age',None)!=Age.TEEN:
            continue
        try:
            sid=canonical_sim_id(getattr(sim,'sim_id',None))
        except Exception:
            continue
        selected[sid]=sim
    return sorted(selected.values(),key=lambda x:(
        str(getattr(x,'last_name','')),
        str(getattr(x,'first_name','')),
        int(x.sim_id)))


def _max_selectable(limit):
    """Keep EA's working picker strategy but cap actual checkable rows.

    M49 proved _MaxSelectableUnlimited works on Mac. Subclass this SAME
    EA object to supply the remaining seat count via get_max_selectable;
    unlike the old ImmutableSlots implementation, we preserve the native
    selection API. Rejection in the transaction is still a final guard.
    """
    if type(limit) is not int or not 1<=limit<=8:
        raise ValueError('Numero di posti non valido')

    base=UiDialogObjectPicker._MaxSelectableUnlimited
    if not callable(getattr(base,'get_max_selectable',None)):
        raise TypeError('API di selezione EA non disponibile')

    class _MaxSelectableRemainingSeats(base):
        def get_max_selectable(self,*args,**kwargs):
            return limit

    return _MaxSelectableRemainingSeats()


def _unassigned_candidates(students,roster):
    """Exclude students already in ANY registered class (1, 2 or 3)."""
    occupied=set(roster.assignments)
    return [sim for sim in students
            if canonical_sim_id(sim.sim_id) not in occupied]


def open_picker(klass,interaction):
    actor=getattr(interaction,'sim',None)
    if actor is None:
        try:
            actor=services.client_manager().get_first_client().active_sim
        except Exception:
            actor=None
    if actor is None:
        _record('BLOCKED','Nessun attore disponibile')
        return False

    try:
        slot=current_slot()
        _SETTINGS.require_management(slot,klass)
        roster=_ROSTERS.load(slot)
        seats=8-len(roster.class_members(klass))
        if seats<=0:
            _notify(actor,'MY HIGH SCHOOL - Classe completa',
                    'Classe {}: tutti gli 8 posti sono occupati.'.format(klass))
            return False
        students=_unassigned_candidates(_teens(),roster)
        if not students:
            _notify(actor,'MY HIGH SCHOOL',
                    'Non ci sono adolescenti non ancora iscritti.')
            return False
        offered={canonical_sim_id(info.sim_id) for info in students}
        max_count=min(seats,len(students))
        dialog=UiSimPicker.TunableFactory().default(
            actor,
            title=_text('Iscrivi studenti - Classe {}'.format(klass)),
            text=_text('Posti liberi: {}/8. Seleziona al massimo {} '
                       'adolescenti non iscritti. '
                       'Premi la spunta per iscriverli, X per uscire.'.format(
                           seats,max_count)),
            max_selectable=_max_selectable(max_count),
            min_selectable=1,should_show_names=True,
            hide_row_description=False)
        for info in students:
            dialog.add_row(SimPickerRow(info.sim_id,False,tag=info.sim_id))
        handled=[False]
        def _on_answer(answer):
            """The SINGLE native confirmation event. No secondary dialog."""
            if handled[0]:
                return
            handled[0]=True
            if getattr(answer,'accepted',False) is not True:
                _record('CANCEL','Classe {}'.format(klass))
                return
            try:
                values=tuple(answer.get_result_tags())
                selected=tuple(canonical_sim_id(x) for x in values)
                if (not 1<=len(selected)<=max_count or
                        len(set(selected))!=len(selected)):
                    raise ValueError('Selezione non valida per i posti disponibili')
                if not set(selected).issubset(offered):
                    raise ValueError('Sim non incluso nel selettore')
                if current_slot()!=slot:
                    raise ValueError('Partita cambiata: nessuna iscrizione')
                # Preview only validates; the SAME accepted checkmark then
                # commits immediately. Cancel never reaches either operation.
                plan=preview_enrollment(
                    _ROSTERS,_SETTINGS,slot,klass,selected,teenager_checker,
                    only_new=True)
                result=confirm_enrollment(
                    _ROSTERS,_SETTINGS,current_slot(),plan,teenager_checker)
                _record('SAVED','Classe {} | {} iscritti'.format(
                    klass,result['changed']))
                _notify(actor,'MY HIGH SCHOOL',
                    'Classe {}: {} iscrizioni aggiornate. Totale {}/8. '
                    'Il liceo EA non e ancora controllato.'.format(
                        klass,result['changed'],result['class_size']))
            except Exception as exc:
                _record('REJECTED',type(exc).__name__)
                _notify(actor,'MY HIGH SCHOOL - Nessuna modifica',
                    'Iscrizione non salvata: {}'.format(str(exc)[:130]))
        dialog.add_listener(_on_answer)
        dialog.show_dialog()
        _record('OPEN','Classe {}'.format(klass))
        return True
    except Exception as exc:
        _record('ERROR',type(exc).__name__)
        _notify(actor,'MY HIGH SCHOOL - Impossibile aprire',
                str(exc)[:130])
        return False


class _EnrollmentAction(ImmediateSuperInteraction):
    _mhs39_action='class'
    _mhs39_class=0

    def _run_interaction_gen(self,timeline):
        open_picker(self._mhs39_class,self)
        result=super()._run_interaction_gen(timeline)
        if inspect.isgenerator(result):
            return (yield from result)
        return result


for _class_number in (1,2,3):
    _name='MHS48EnrollClass{}'.format(_class_number)
    globals()[_name]=type(_name,(_MHS39VisibilityMixin,_EnrollmentAction),{
        '__module__':__name__,
        '_mhs39_class':_class_number,
    })
