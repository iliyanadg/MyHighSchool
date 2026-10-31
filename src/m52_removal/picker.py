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
