"""M98 in-game five school core role appointment menu (Mac Python 3.7).

PERSISTENT DRAFT ROLE SELECTION ONLY: never claims EA Core situation actually
honored an appointment. No automatic NPC placement, no modified EA filters,
no school situation creation, no extra Sim generation.

Reuses the verified M53 native UiSimPicker flow. Max 1 human enrolled teen.
All changes happen only on explicit picker checkmark, on the current save.
"""
import inspect
import os
import services
from interactions.base.immediate_interaction import ImmediateSuperInteraction
from sims.sim_info_types import Age,Species
from sims4.localization import LocalizationHelperTuning
from ui.ui_dialog_picker import UiSimPicker,SimPickerRow,UiDialogObjectPicker
from ui.ui_dialog_notification import UiDialogNotification

from mhs_m2_game_bridge import current_slot
from mhs_m2_store import RosterStore
from mhs34_settings import SettingsStore
from mhs97_core_role_store import (CoreRoleStore,CoreRosterError,plan_change,
                                    ROLE_TO_JOB,ROLES)

_FOLDER=os.path.join(os.path.expanduser('~'),'Documents','Electronic Arts',
                     'The Sims 4','MY_HIGH_SCHOOL_M25_TEST_DATA')
_ROSTERS=RosterStore(_FOLDER)
_SETTINGS=SettingsStore(_FOLDER)
_CORE=CoreRoleStore(_FOLDER)
_LABELS={'cheer':'Cheerleader','chess':'Scacchi','football':'Football',
         'computer':'Informatica','mean':'Sim perfido'}
_ACTIONS=tuple((role,mode) for role in ROLES for mode in ('assign','remove'))
_ACTIONS+=(('all','view'),)
_EVENTS=[]

def _record(kind,detail=''):
    _EVENTS.append((kind,str(detail)[:120]))
    del _EVENTS[:-20]

def _text(raw):
    return lambda **_:LocalizationHelperTuning.get_raw_text(str(raw))

def _actor(interaction):
    sim=getattr(interaction,'sim',None)
    if sim is not None:
        return sim
    try:
        return services.client_manager().get_first_client().active_sim
    except Exception:
        return None

def _notice(actor,title,body):
    _record('NOTICE',title)
    if actor is None:
        return
    try:
        dlg=UiDialogNotification.TunableFactory().default(
            actor,title=_text(title),text=_text(body))
        dlg.show_dialog()
    except Exception as exc:
        _record('NOTICE_ERROR',type(exc).__name__)

def _teen_human(info):
    return (info is not None and
            getattr(info,'age',None)==Age.TEEN and
            getattr(info,'species',None)==Species.HUMAN)

def _is_playable(info):
    try:
        household=services.active_household()
        return household is not None and (
            getattr(info,'household_id',None)==getattr(household,'id',None))
    except Exception:
        return True

def _still_candidate(sid):
    """Preliminary gate; NOT a job-specific EA SimFilter evaluation."""
    try:
        info=services.sim_info_manager().get(int(sid))
        return _teen_human(info) and not _is_playable(info)
    except Exception:
        return False

def _registered(slot):
    settings=_SETTINGS.load(slot)
    if not settings.active or settings.class_count!=2:
        raise CoreRosterError('Attiva prima le due classi MHS')
    roster=_ROSTERS.load(slot)
    groups=tuple(tuple(roster.class_members(k)) for k in (1,2))
    ids=[str(sid) for group in groups for sid in group]
    if any(len(group)>8 for group in groups) or len(set(ids))!=len(ids):
        raise CoreRosterError('Registro studenti duplicato o non valido')
    return groups,ids

def _name(sid):
    try:
        info=services.sim_info_manager().get(int(sid))
        if info is not None:
            return '{} {}'.format(getattr(info,'first_name',''),
                                  getattr(info,'last_name','')).strip()
    except Exception:
        pass
    return 'Sim {}'.format(sid)

def _max_one():
    strategy=UiDialogObjectPicker._MaxSelectableUnlimited
    if not callable(getattr(strategy,'get_max_selectable',None)):
        raise CoreRosterError('Selettore EA non compatibile')
    class _SingleCoreRole(strategy):
        def get_max_selectable(self,*args,**kwargs):
            return 1
    return _SingleCoreRole()

def _summary(record,groups):
    lines=[]
    for role in ROLES:
        sid=record.roles[role]
        klass=next((i for i,group in enumerate(groups,1) if sid in group),None)
        lines.append('{}: {}{}'.format(
            _LABELS[role], _name(sid) if sid else 'Non assegnato',
            (' (Classe {})'.format(klass) if klass is not None else '')))
    lines.append('Totale {}/5, assegnazioni provvisorie.'.format(
        len(record.chosen())))
    lines.append('Nessun ruolo EA viene modificato da questo menu.')
    return '\n'.join(lines)

def open_role(role,mode,interaction):
    actor=_actor(interaction)
    try:
        slot=current_slot(allow_travel=True)
        _SETTINGS.require_management(slot,1)
        groups,enrolled=_registered(slot)
        before=_CORE.load(slot)
        if mode=='view':
            _notice(actor,'MY HIGH SCHOOL - Ruoli speciali',
                    _summary(before,groups))
            return True
        if role not in ROLE_TO_JOB or mode not in ('assign','remove'):
            raise CoreRosterError('Operazione ruolo non valida')
        if mode=='remove':
            sid=before.roles[role]
            if sid is None:
                _notice(actor,'MY HIGH SCHOOL',
                        '{}: nessuno assegnato.'.format(_LABELS[role]))
                return False
            info=services.sim_info_manager().get(int(sid))
            if info is None:
                # If a Sim was deleted/aged-out, we must still let the player
                # remove a stale appointment. Do not silently mutate a role.
                raise CoreRosterError(
                    'Sim non presente: impossibile aprire il selettore. '
                    'Nessuna modifica effettuata.')
            candidates=(info,)
        else:
            reserved=set(before.chosen().values())
            candidate_ids=[sid for sid in enrolled
                           if sid not in reserved or sid==before.roles[role]]
            mgr=services.sim_info_manager()
            candidates=tuple(info for sid in candidate_ids
                             for info in (mgr.get(int(sid)),)
                             if _teen_human(info) and not _is_playable(info))
        if not candidates:
            _notice(actor,'MY HIGH SCHOOL',
                    'Nessuno studente umano adolescente iscritto disponibile.')
            return False
        offered=set(str(info.sim_id) for info in candidates)
        dialog=UiSimPicker.TunableFactory().default(
            actor,
            title=_text('{} - {}'.format(
                'Assegna' if mode=='assign' else 'Rimuovi',_LABELS[role])),
            text=_text(
                'Scegli un iscritto e premi la spunta per confermare. '
                'La X annulla. Ruolo provvisorio: filtro EA da verificare.'),
            max_selectable=_max_one(),min_selectable=1,
            should_show_names=True,hide_row_description=False)
        for info in candidates:
            dialog.add_row(SimPickerRow(info.sim_id,False,tag=info.sim_id))
        fingerprint=before.fingerprint()
        handled=[False]
        def on_answer(result):
            if handled[0]:
                return
            handled[0]=True
            if not getattr(result,'accepted',False):
                _record('CANCEL',role)
                return
            try:
                tags=tuple(str(x) for x in result.get_result_tags())
                if len(tags)!=1 or tags[0] not in offered:
                    raise CoreRosterError('Seleziona un solo Sim dalla lista')
                if current_slot(allow_travel=True)!=slot:
                    raise CoreRosterError('Hai cambiato salvataggio')
                _SETTINGS.require_management(slot,1)
                now_groups,now_enrolled=_registered(slot)
                if now_groups!=groups:
                    raise CoreRosterError('Il registro e cambiato: riapri il menu')
                if mode=='assign':
                    if not _still_candidate(tags[0]):
                        raise CoreRosterError('Il Sim non e piu un adolescente umano NPC')
                    updated=plan_change(
                        before,role,tags[0],now_enrolled,
                        lambda job,sid:_still_candidate(sid))
                else:
                    if tags[0]!=before.roles[role]:
                        raise CoreRosterError('Studente assegnato cambiato')
                    updated=plan_change(
                        before,role,None,now_enrolled,
                        lambda job,sid:False)
                _CORE.save(slot,updated,fingerprint)
                _record('SAVED',role+' '+mode)
                _notice(actor,'MY HIGH SCHOOL - Ruoli speciali',
                        '{}: {}. Scelta salvata nel registro MHS; '
                        'il ruolo EA non viene ancora cambiato.'.format(
                            _LABELS[role],
                            _name(tags[0]) if mode=='assign' else 'rimosso'))
            except Exception as exc:
                _record('BLOCKED',type(exc).__name__)
                _notice(actor,'MY HIGH SCHOOL - Nessuna modifica',
                        str(exc)[:140])
        dialog.add_listener(on_answer)
        dialog.show_dialog()
        _record('OPEN',role+' '+mode)
        return True
    except Exception as exc:
        _record('ERROR',type(exc).__name__)
        _notice(actor,'MY HIGH SCHOOL - Ruoli speciali',
                str(exc)[:150])
        return False

class _RoleAction(ImmediateSuperInteraction):
    _role=None
    _mode=None
    def _run_interaction_gen(self,timeline):
        open_role(self._role,self._mode,self)
        result=super()._run_interaction_gen(timeline)
        if inspect.isgenerator(result):
            return (yield from result)
        return result

for _role,_mode in _ACTIONS:
    _classname='MHS98Role'+_mode.capitalize()+_role.capitalize()
    globals()[_classname]=type(
        _classname,(_RoleAction,),
        {'__module__':__name__,'_role':_role,'_mode':_mode})
