"""M55: diagnostic UI for automatic whole-roster school arrival.

No individual student selection is necessary. Clicking this only displays
the coordinator's in-memory status; the coordinator runs on its own on the
school lot after EA initializes school situations.
"""
import inspect

from interactions.base.immediate_interaction import ImmediateSuperInteraction
from sims4.localization import LocalizationHelperTuning
from ui.ui_dialog_notification import UiDialogNotification
from mhs55_attendance_auto import status_lines


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


def show_attendance_status(interaction):
    actor = _actor(interaction)
    if actor is None:
        return False
    try:
        dialog = UiDialogNotification.TunableFactory().default(
            actor, title=_text('MY HIGH SCHOOL - Presenze automatiche'),
            text=_text(status_lines()))
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
