# Multi-student native picker for school enrollment records
import inspect
import services
from interactions.base.immediate_interaction import ImmediateSuperInteraction
from sims4.localization import LocalizationHelperTuning
from ui.ui_dialog_picker import UiSimPicker,SimPickerRow,UiDialogObjectPicker
from ui.ui_dialog_notification import UiDialogNotification
from mhs_m2_game_bridge import current_slot
from mhs_m2_roster import canonical_sim_id,RosterError
from mhs_m2_store import RosterStore
from mhs34_settings import SettingsStore
from mhs26_remove import candidate_rows,plan_removal,roster_fingerprint
from mhs27_remove_ui import _lookup_sim_info
import os

_DIR=os.path.join(os.path.expanduser('~'),'Documents','Electronic Arts',
                  'The Sims 4','MY_HIGH_SCHOOL_M25_TEST_DATA')
_STORE=RosterStore(_DIR)
_SETTINGS=SettingsStore(_DIR)

def _str(s):
    return lambda **_:LocalizationHelperTuning.get_raw_text(str(s))

def _notice(actor,heading,message):
    if actor is None:
        return
    try:
        dialog=UiDialogNotification.TunableFactory().default(
            actor,title=_str(heading),text=_str(message))
        dialog.show_dialog()
    except Exception:
        pass

def _max(count):
    base=UiDialogObjectPicker._MaxSelectableUnlimited
    class Limit(base):
        def get_max_selectable(self,*args,**kwargs):
            return count
    return Limit()

def open_picker(klass,interaction):
    actor=getattr(interaction,'sim',None)
    if actor is None:
        try:
            actor=services.client_manager().get_first_client().active_sim
        except Exception:
            actor=None
    try:
        slot=current_slot()
        _SETTINGS.require_management(slot,klass)
        roster=_STORE.load(slot)
        choices=candidate_rows(roster,klass,_lookup_sim_info)
        if not choices or actor is None:
            return False
        before=roster_fingerprint(roster)
        allowed=set(roster.class_members(klass))
        limit=min(8,len(choices))
        picker=UiSimPicker.TunableFactory().default(
            actor,title=_str('Rimuovi studenti - Classe {}'.format(klass)),
            text=_str('Seleziona gli iscritti. Spunta per rimuovere, X per annullare.'),
            min_selectable=1,max_selectable=_max(limit),
            should_show_names=True,hide_row_description=False)
        for sim in choices:
            picker.add_row(SimPickerRow(sim.sim_id,False,tag=sim.sim_id))
        done=[False]
        def on_answer(result):
            if done[0]:
                return
            done[0]=True
            if not getattr(result,'accepted',False):
                return
            try:
                ids=tuple(canonical_sim_id(t) for t in result.get_result_tags())
                if not 1<=len(ids)<=limit or len(set(ids))!=len(ids):
                    raise RosterError('Selezione non valida')
                if not set(ids).issubset(allowed) or current_slot()!=slot:
                    raise RosterError('Selezione o partita cambiata')
                _SETTINGS.require_management(slot,klass)
                current=_STORE.load(slot)
                if roster_fingerprint(current)!=before:
                    raise RosterError('Registro cambiato: riapri il menu')
                updated,stats=plan_removal(current,klass,ids)
                _STORE.save(slot,updated)
                _notice(actor,'MY HIGH SCHOOL - Studenti rimossi',
                    'Classe {}: {} rimossi, restano {}/8.'.format(
                        klass,stats['removed'],stats['remaining']))
            except Exception as exc:
                _notice(actor,'MY HIGH SCHOOL - Nessuna modifica',
                    str(exc)[:130])
        picker.add_listener(on_answer)
        picker.show_dialog()
        return True
    except Exception as exc:
        _notice(actor,'MY HIGH SCHOOL - Impossibile aprire',str(exc)[:130])
        return False

class _Action(ImmediateSuperInteraction):
    klass=0
    def _run_interaction_gen(self,timeline):
        open_picker(self.klass,self)
        result=super()._run_interaction_gen(timeline)
        if inspect.isgenerator(result):
            return (yield from result)
        return result

class MHS27RemoveClass1(_Action):
    klass=1
class MHS27RemoveClass2(_Action):
    klass=2
class MHS28RemoveClass3(_Action):
    klass=3
