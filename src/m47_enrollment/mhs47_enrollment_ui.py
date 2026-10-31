"""M47 native in-game enrollment picker + explicit second confirmation.

This module does not change EA High School Years attendance or any .save.
It writes only the existing per-save M25 TEST JSON after a genuine positive
confirmation callback, with an atomic, revalidated 8-seat transaction.

The established M45 menu/visibility and Lot51 SimData are preserved.
UiSimPicker / UiDialogOkCancel factory compatibility still needs Mac test.
"""
import inspect
import os

import services
from sims.sim_info_types import Age
from sims4.localization import LocalizationHelperTuning
from interactions.base.immediate_interaction import ImmediateSuperInteraction
from ui.ui_dialog import UiDialogOkCancel
from ui.ui_dialog_notification import UiDialogNotification

from mhs_m2_game_bridge import current_slot, teenager_checker
from mhs_m2_roster import canonical_sim_id
from mhs_m2_store import RosterStore
from mhs34_settings import SettingsStore
from mhs46_enrollment_transaction import (
    preview_enrollment, confirm_enrollment)

_DATA_DIR=os.path.join(os.path.expanduser('~'),'Documents',
    'Electronic Arts','The Sims 4','MY_HIGH_SCHOOL_M25_TEST_DATA')
_ROSTERS=RosterStore(_DATA_DIR)
_SETTINGS=SettingsStore(_DATA_DIR)
_EVENTS=[]


def _event(kind,details=''):
    _EVENTS.append((kind,str(details)[:160]))
    if len(_EVENTS)>20:
        del _EVENTS[:-20]


def _localized(text):
    return lambda **_: LocalizationHelperTuning.get_raw_text(str(text))


def _notice(actor,title,message):
    """Use native notification; logging remains available if UI cannot show it."""
    _event('NOTIFY',title+': '+message)
    try:
        dialog=UiDialogNotification.TunableFactory().default(
            actor,title=_localized(title),text=_localized(message))
        dialog.show_dialog()
        return True
    except Exception as exc:
        _event('NOTICE_FAILED',type(exc).__name__)
        return False


def _teen_candidates():
    manager=services.sim_info_manager()
    if manager is None:
        raise ValueError('Elenco degli adolescenti non disponibile')
    result=[]
    used=set()
    for info in manager.get_all():
        if info is None or getattr(info,'age',None)!=Age.TEEN:
            continue
        try:
            sid=canonical_sim_id(getattr(info,'sim_id',None))
        except Exception:
            continue
        if sid not in used:
            used.add(sid)
            result.append(info)
    return sorted(result,key=lambda i:(str(getattr(i,'last_name','')),
                                       str(getattr(i,'first_name','')),
                                       int(i.sim_id)))


def _confirmation_dialog(actor,klass,plan):
    text=('Selezionati: {selected_count}. Nuovi o spostati: {changed}. '
          'Gia in classe: {already_in_class}. '
          'Totale Classe {klass} dopo la conferma: {class_size}/8. '
          'Posti liberi: {remaining}. '
          'Confermi le iscrizioni nel registro di prova?').format(
              klass=klass,**plan)
    dialog=UiDialogOkCancel.TunableFactory().default(
        actor,
        title=_localized('Conferma iscrizioni - Classe {}'.format(klass)),
        text=_localized(text))

    finished=[False]

    def _on_answer(answer):
        if finished[0]:
            return
        finished[0]=True
        if not getattr(answer,'accepted',False):
            _event('CANCEL','Classe {}'.format(klass))
            return
        try:
            result=confirm_enrollment(
                _ROSTERS,_SETTINGS,current_slot(),plan,teenager_checker)
            _notice(actor,'MY HIGH SCHOOL - Registro aggiornato',
                'Classe {}: {} iscritti registrati. Totale {}/8. '
                'Frequenza al liceo EA non ancora modificata.'.format(
                    klass,result['changed'],result['class_size']))
            _event('COMMITTED','Classe {} | {}'.format(
                klass,result['changed']))
        except Exception as exc:
            _notice(actor,'MY HIGH SCHOOL - Iscrizione non salvata',
                'Controllo non superato: {}. Ripeti la scelta.'.format(str(exc)[:110]))
            _event('REJECTED',type(exc).__name__)

    dialog.add_listener(_on_answer)
    dialog.show_dialog()
    return True


def open_enrollment_picker(klass,interaction):
    """Open ALL teens, then preview and ask a separate yes/no confirmation.

    Clicking a Sim in the picker never writes. Closing either dialog never
    writes. Stale slot, wrong age, disabled class, roster change fail closed.
    """
    actor=getattr(interaction,'sim',None)
    if actor is None:
        try:
            client=services.client_manager().get_first_client()
            actor=getattr(client,'active_sim',None)
        except Exception:
            actor=None
    if actor is None:
        _event('BLOCKED','Actor non disponibile')
        return False

    try:
        slot=current_slot()
        _SETTINGS.require_management(slot,klass)
        roster=_ROSTERS.load(slot)
        candidates=_teen_candidates()
        if not candidates:
            _notice(actor,'MY HIGH SCHOOL','Nessun adolescente disponibile nel salvataggio.')
            return False
        from ui.ui_dialog_picker import UiSimPicker, SimPickerRow
        dialog=UiSimPicker.TunableFactory().default(
            actor,
            title=_localized('Iscrivi studenti - Classe {}'.format(klass)),
            text=_localized('Scegli da 1 a 8 adolescenti. '
                'Attualmente iscritti: {}/8. '
                'Dopo la selezione vedrai una seconda conferma.'.format(
                    len(roster.class_members(klass)))),
            min_selectable=1,should_show_names=True,hide_row_description=False)
        offered={canonical_sim_id(i.sim_id) for i in candidates}
        for info in candidates:
            dialog.add_row(SimPickerRow(info.sim_id,False,tag=info.sim_id))
        processed=[False]

        def _on_select(answer):
            if processed[0]:
                return
            processed[0]=True
            if not getattr(answer,'accepted',False):
                _event('CANCEL_PICKER','Classe {}'.format(klass))
                return
            try:
                raw=tuple(answer.get_result_tags())
                selected=tuple(canonical_sim_id(x) for x in raw)
                if not selected or len(selected)>8 or len(set(selected))!=len(selected):
                    raise ValueError('Seleziona da 1 a 8 studenti senza duplicati')
                if not set(selected).issubset(offered):
                    raise ValueError('La scelta contiene un Sim non autorizzato')
                if current_slot()!=slot:
                    raise ValueError('Salvataggio cambiato durante la scelta')
                plan=preview_enrollment(
                    _ROSTERS,_SETTINGS,slot,klass,selected,teenager_checker)
                _confirmation_dialog(actor,klass,plan)
                _event('PREVIEW','Classe {} | {}'.format(klass,len(selected)))
            except Exception as exc:
                _notice(actor,'MY HIGH SCHOOL - Selezione non valida',
                    str(exc)[:135])
                _event('BLOCKED',type(exc).__name__)

        dialog.add_listener(_on_select)
        dialog.show_dialog()
        _event('OPEN','Classe {} | {} adolescenti'.format(klass,len(candidates)))
        return True
    except Exception as exc:
        _notice(actor,'MY HIGH SCHOOL - Impossibile aprire',
            '{}'.format(str(exc)[:135]))
        _event('ERROR',type(exc).__name__)
        return False


class MHS47EnrollmentImmediateBase(ImmediateSuperInteraction):
    _mhs47_class=0

    def _run_interaction_gen(self,timeline):
        open_enrollment_picker(self._mhs47_class,self)
        original=super()._run_interaction_gen(timeline)
        if inspect.isgenerator(original):
            return (yield from original)
        return original
