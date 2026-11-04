"""M34 settings actions, deliberately on the verified flat M33 mailbox menu.

These settings only control the experimental external JSON registry.
They do not affect EA high-school time tables or students' attendance.
"""
import inspect
import os
import sims4.commands
from interactions.base.immediate_interaction import ImmediateSuperInteraction
from mhs_m2_game_bridge import current_slot
from mhs_m2_store import RosterStore
from mhs34_settings import SettingsStore, SettingsError

_FOLDER=os.path.join(os.path.expanduser('~'),'Documents',
                     'Electronic Arts','The Sims 4','MY_HIGH_SCHOOL_M25_TEST_DATA')
_CONFIG=SettingsStore(_FOLDER)
_ROSTERS=RosterStore(_FOLDER)
_EVENTS=[]


def _event(text):
    _EVENTS.append(str(text)[:160])
    if len(_EVENTS)>12:
        del _EVENTS[:-12]


def _settings_notice(title,message):
    """Make rejected class-3 deactivation visible instead of silently failing."""
    try:
        import services
        from sims4.localization import LocalizationHelperTuning
        from ui.ui_dialog_notification import UiDialogNotification
        client=services.client_manager().get_first_client()
        actor=getattr(client,'active_sim',None)
        if actor is None:
            return False
        text=lambda value:(lambda **_:LocalizationHelperTuning.get_raw_text(value))
        dialog=UiDialogNotification.TunableFactory().default(
            actor,title=text(title),text=text(message))
        dialog.show_dialog()
        return True
    except Exception:
        return False


def _warning(actor,reason):
    if actor is None:
        return
    try:
        from sims4.localization import LocalizationHelperTuning
        from ui.ui_dialog_notification import UiDialogNotification
        txt=lambda text:lambda **_:LocalizationHelperTuning.get_raw_text(text)
        dlg=UiDialogNotification.TunableFactory().default(
            actor,title=txt('MY HIGH SCHOOL - Classe 3 non disattivata'),
            text=txt(reason))
        dlg.show_dialog()
    except Exception:
        pass


def _apply(operation, actor=None):
    try:
        slot=current_slot()
        if operation=='enable':
            state=_CONFIG.set_active(slot,True)
        elif operation=='disable':
            state=_CONFIG.set_active(slot,False)
        elif operation=='two':
            state=_CONFIG.set_class_count(slot,2,_ROSTERS.load(slot))
        elif operation=='three':
            state=_CONFIG.set_class_count(slot,3,_ROSTERS.load(slot))
        else:
            raise SettingsError('Operazione non valida')
        _event('SAVED slot {} | {} | {} classi'.format(
            slot,'Attiva' if state.active else 'Disattiva',state.class_count))
        try:
            import mhs_classroom_bootstrap
        except ImportError:
            pass
        else:
            status=mhs_classroom_bootstrap.refresh()
            # Preserve the established silent success path, especially Disable.
            # Only a failed activation or hook restoration needs a notice.
            if (str(status).startswith('RESTORE_BLOCKED') or
                    (operation=='enable' and any(word in str(status) for word in (
                        'BLOCKED','NON ATTIVA','BLOCCATA','REQUIRES_HOME')))):
                _settings_notice('MY HIGH SCHOOL',
                    mhs_classroom_bootstrap.settings_message(status))
        return True
    except Exception as exc:
        _event('BLOCKED | {}: {}'.format(type(exc).__name__,str(exc)[:120]))
        if operation=='two':
            _settings_notice('MY HIGH SCHOOL - Classe 3 ancora attiva',
                str(exc)[:180])
        else:
            _settings_notice('MY HIGH SCHOOL - Impostazioni non modificate',
                str(exc)[:180])
        return False


class MHS34Enable(ImmediateSuperInteraction):
    def _run_interaction_gen(self,timeline):
        _apply('enable')
        result=super()._run_interaction_gen(timeline)
        if inspect.isgenerator(result):
            return (yield from result)
        return result


class MHS34Disable(ImmediateSuperInteraction):
    def _run_interaction_gen(self,timeline):
        _apply('disable')
        result=super()._run_interaction_gen(timeline)
        if inspect.isgenerator(result):
            return (yield from result)
        return result


class MHS34TwoClasses(ImmediateSuperInteraction):
    def _run_interaction_gen(self,timeline):
        _apply('two',getattr(self,'sim',None))
        result=super()._run_interaction_gen(timeline)
        if inspect.isgenerator(result):
            return (yield from result)
        return result


class MHS34ThreeClasses(ImmediateSuperInteraction):
    def _run_interaction_gen(self,timeline):
        _apply('three')
        result=super()._run_interaction_gen(timeline)
        if inspect.isgenerator(result):
            return (yield from result)
        return result


@sims4.commands.Command('mhs34.settings',command_type=sims4.commands.CommandType.Live)
def mhs34_settings(_connection=None):
    out=sims4.commands.CheatOutput(_connection)
    try:
        slot=current_slot()
        state=_CONFIG.load(slot)
        out('MY HIGH SCHOOL M34 - IMPOSTAZIONI REGISTRO TEST | Slot {}'.format(slot))
        out('Gestione iscrizioni: {}'.format('ATTIVA' if state.active else 'DISATTIVA'))
        out('Classi disponibili: {}'.format(state.class_count))
        roster=_ROSTERS.load(slot)
        out('Classe 3 iscritti: {}'.format(len(roster.class_members(3))))
        out('Solo registro esterno, NON controlla ancora il liceo EA.')
        for event in _EVENTS[-4:]:
            out(event)
    except Exception as exc:
        out('IMPOSTAZIONI NON LETTE: {}'.format(str(exc)[:130]))


@sims4.commands.Command('mhs34.report',command_type=sims4.commands.CommandType.Live)
def mhs34_report(_connection=None):
    out=sims4.commands.CheatOutput(_connection)
    if not _EVENTS:
        out('Nessuna modifica di impostazioni eseguita in questa sessione.')
    for event in _EVENTS[-8:]:
        out(event)
    out('Le modifiche al JSON impostazioni sono immediate, anche senza salvare il gioco.')
