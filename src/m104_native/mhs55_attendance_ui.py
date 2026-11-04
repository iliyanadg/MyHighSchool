"""M55: diagnostic UI for automatic whole-roster school arrival.

No individual student selection is necessary. Clicking this only displays
the coordinator's in-memory status; the coordinator runs on its own on the
school lot after EA initializes school situations.
"""
import inspect
import os

from interactions.base.immediate_interaction import ImmediateSuperInteraction
from sims4.localization import LocalizationHelperTuning
from ui.ui_dialog_notification import UiDialogNotification
from mhs55_attendance_auto import status_lines
import mhs58_situation_probe
import mhs57_filter_runtime
import mhs61_pilot_command
from mhs85_ui_bridge import capture_status, short_line
from mhs94_school_job_probe import capture_report as mhs94_capture, summary_line as mhs94_summary


def _text(value):
    return lambda **_: LocalizationHelperTuning.get_raw_text(str(value))


def _actor(interaction):
    sim = getattr(interaction, 'sim', None)
    if sim is not None:
        return sim
    try:
        import services
        return services.client_manager().get_first_client().active_sim
    except Exception:
        return None


def compact_diagnostic():
    """Short EA-safe notification; original multi-line report was oversized.

    Empty counters mean no matching creation OBSERVED, never no students.
    """
    state=mhs58_situation_probe.status()
    counts=state.get('counts',{})
    parts=[]
    for guid,label in ((277733,'Studenti'),(298052,'Core'),
                       (298096,'Personale'),(278011,'Mensa')):
        row=counts.get(guid,{})
        parts.append('{}:{}'.format(label,row.get('calls',0)))
    return ('M58 attiva: {}. {}. Errore: {}. '
            'Contatori di creazione, NON presenze.'.format(
                'SI' if state.get('installed') else 'NO',
                ' | '.join(parts),str(state.get('error','none'))[:35]))


def show_attendance_status(interaction):
    actor = _actor(interaction)
    if actor is None:
        return False
    try:
        folder=os.path.join(os.path.expanduser('~'),'Documents','Electronic Arts',
                            'The Sims 4','MY_HIGH_SCHOOL_M25_TEST_DATA')
        try:
            mhs58_situation_probe.save_report(folder, mhs57_filter_runtime.m59_snapshot())
        except Exception:
            pass  # File diagnostic is optional; never block native UI.
        result85=capture_status(folder)
        try:
            report94=mhs94_capture(folder)
            extra=' '+mhs94_summary(report94)
        except Exception as exc:
            extra=' M94 lettura non disponibile: '+type(exc).__name__
        dialog = UiDialogNotification.TunableFactory().default(
            actor, title=_text('MY HIGH SCHOOL - Presenze automatiche'),
            text=_text(compact_diagnostic()+' '+short_line(result85)+extra))
        dialog.show_dialog()
        return True
    except Exception:
        return False


class MHS55TryOne(ImmediateSuperInteraction):
    """Class kept for tuning compatibility; now shows full daily status."""
    def _run_interaction_gen(self, timeline):
        show_attendance_status(self)
        result = super()._run_interaction_gen(timeline)
        if inspect.isgenerator(result):
            return (yield from result)
        return result

# M104 native-filter experiment: independent opt-in console commands.
# M57 has already been imported above. This does NOT arm automatically.
try:
    import mhs104_native_school_filter
except Exception:
    pass
