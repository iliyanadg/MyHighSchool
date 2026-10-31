"""M53 staff personnel UI: ONLY choose existing young adult/adult/elder Sims.

All school staffing changes affect a per-save external TEST JSON, not real
EA principal/teacher/cafeteria/custodian roles. None of the EA school lot
NPC service assignments or live attendance are changed yet.

One native picker checkmark is the only confirmation; X cancels.
The action types are validated against M34 activation & 2/3 class setting.
"""
import inspect
import os

import services
from interactions.base.immediate_interaction import ImmediateSuperInteraction
from sims.sim_info_types import Age, Species
from sims4.localization import LocalizationHelperTuning
from ui.ui_dialog_picker import UiSimPicker,SimPickerRow,UiDialogObjectPicker
from ui.ui_dialog_notification import UiDialogNotification

from mhs_m2_game_bridge import current_slot
from mhs_m2_roster import canonical_sim_id
from mhs34_settings import SettingsStore
from mhs53_staff_store import StaffStore,StaffError,CAP,KEYS,SINGLE

_FOLDER=os.path.join(os.path.expanduser('~'),'Documents','Electronic Arts',
                     'The Sims 4','MY_HIGH_SCHOOL_M25_TEST_DATA')
_STAFF=StaffStore(_FOLDER)
_SETTINGS=SettingsStore(_FOLDER)
_EVENTS=[]
_ADULT_AGES=(Age.YOUNGADULT,Age.ADULT,Age.ELDER)

# Affordance name / staff role / operation / class-visibility gate.
# No create CAS, random generation or second confirmation.
STAFF_ACTIONS=(
    ('PrincipalChoose','principal','assign',1),
    ('PrincipalRemove','principal','remove',1),
    ('PrincipalView','principal','view',1),
    ('Teacher1Choose','teacher1','assign',1),
    ('Teacher1Remove','teacher1','remove',1),
    ('Teacher2Choose','teacher2','assign',2),
    ('Teacher2Remove','teacher2','remove',2),
    ('Teacher3Choose','teacher3','assign',3),
    ('Teacher3Remove','teacher3','remove',3),
    ('TeachersView','teacher1','teachers_view',1),
    ('CafeteriaChoose','cafeteria','assign',1),
    ('CafeteriaRemove','cafeteria','remove',1),
    ('CafeteriaView','cafeteria','view',1),
    ('CustodiansChoose','custodians','assign',1),
    ('CustodiansRemove','custodians','remove',1),
    ('CustodiansView','custodians','view',1),
    ('StaffViewAll','principal','all',1),
)


def _record(event,message=''):
    _EVENTS.append((str(event),str(message)[:160]))
    del _EVENTS[:-30]


def _text(value):
    return lambda **_:LocalizationHelperTuning.get_raw_text(str(value))


def _notice(actor,title,message):
    _record('NOTICE',title+' | '+message)
    if actor is None:
        return
    try:
        dlg=UiDialogNotification.TunableFactory().default(
            actor,title=_text(title),text=_text(message))
        dlg.show_dialog()
    except Exception as exc:
        _record('NOTICE_ERROR',type(exc).__name__)


def _actor(interaction):
    actor=getattr(interaction,'sim',None)
    if actor is not None:
        return actor
    try:
        return services.client_manager().get_first_client().active_sim
    except Exception:
        return None


def _eligible_human_adult(sim):
    """Require BOTH human species and adult age (pets may have Age.ADULT).

    A missing species is NOT presumed human: fail closed on unknown
    species, dogs, cats, horses and any other animal.
    """
    return (sim is not None
            and getattr(sim,'species',None)==Species.HUMAN
            and getattr(sim,'age',None) in _ADULT_AGES)


def _adult_infos():
    mgr=services.sim_info_manager()
    if mgr is None:
        raise StaffError('Archivio Sims non disponibile')
    result={}
    for sim in mgr.get_all():
        if not _eligible_human_adult(sim):
            continue
        try:
            sid=canonical_sim_id(getattr(sim,'sim_id',None))
        except Exception:
            continue
        result[sid]=sim
    return sorted(result.values(),key=lambda info:(
        str(getattr(info,'last_name','')),
        str(getattr(info,'first_name','')),int(info.sim_id)))


def _still_adult(sid):
    try:
        sim=services.sim_info_manager().get(int(canonical_sim_id(sid)))
        return _eligible_human_adult(sim)
    except Exception:
        return False


def _name(sim_id):
    try:
        sim=services.sim_info_manager().get(int(sim_id))
        if sim is not None:
            return '{} {}'.format(getattr(sim,'first_name',''),
                                  getattr(sim,'last_name','')).strip()
    except Exception:
        pass
    return 'Sim {}'.format(sim_id)


def _role_label(role):
    return {'principal':'Preside','teacher1':'Professore Classe 1',
            'teacher2':'Professore Classe 2',
            'teacher3':'Professore Classe 3',
            'cafeteria':'Addetti mensa','custodians':'Bidelli'}[role]


def _selection_strategy(count):
    if type(count) is not int or not 1<=count<=3:
        raise StaffError('Numero di persone non valido')
    base=UiDialogObjectPicker._MaxSelectableUnlimited
    if not callable(getattr(base,'get_max_selectable',None)):
        raise StaffError('Selettore Sims non compatibile')

    class _LimitedStaffPicker(base):
        def get_max_selectable(self,*args,**kwargs):
            return count

    return _LimitedStaffPicker()


def _summary(roster,mode,role):
    if mode=='all':
        roles=KEYS
    elif mode=='teachers_view':
        roles=('teacher1','teacher2','teacher3')
    else:
        roles=(role,)
    result=[]
    for key in roles:
        ids=roster.members(key)
        label=_role_label(key)
        if key not in SINGLE:
            label+=' ({}/{})'.format(len(ids),CAP[key])
        names=', '.join(_name(sid) for sid in ids) if ids else 'Nessuno assegnato'
        result.append('{}: {}'.format(label,names))
    return '\n'.join(result)


def open_staff(role,mode,klass,interaction):
    """Save only inside the genuine accepted result callback of the picker."""
    actor=_actor(interaction)
    try:
        slot=current_slot(allow_travel=(mode in ('view','teachers_view','all')))
        _SETTINGS.require_management(slot,klass)
        before=_STAFF.load(slot)
        if mode in ('view','teachers_view','all'):
            if mode=='teachers_view' and _SETTINGS.load(slot).class_count==2:
                text=_summary(before,'view','teacher1')+'\n'+_summary(before,'view','teacher2')
            else:
                text=_summary(before,mode,role)
            _notice(actor,'MY HIGH SCHOOL - Personale scolastico',text)
            return True
        if mode not in ('assign','remove'):
            raise StaffError('Operazione personale non supportata')
        members=before.members(role)
        if mode=='remove':
            if not members:
                _notice(actor,'MY HIGH SCHOOL',
                        '{}: non ci sono persone assegnate.'.format(_role_label(role)))
                return False
            wanted=set(members)
            # Removing an already-assigned animal must remain possible,
            # to clean up bad entries created with the older M53 build.
            # A pet can NEVER be newly assigned by the human-only picker.
            mgr=services.sim_info_manager()
            candidates=[]
            if mgr is not None:
                for sid in members:
                    info=mgr.get(int(sid))
                    if info is not None and canonical_sim_id(
                            info.sim_id) in wanted:
                        candidates.append(info)
            max_allowed=min(len(candidates),CAP[role])
        else:
            occupied=before.all_ids()
            # A staff appointment must be an eligible HUMAN adult and
            # must not duplicate an already-occupied staff role.
            candidates=[info for info in _adult_infos()
                        if canonical_sim_id(info.sim_id) not in occupied]
            max_allowed=(1 if role in SINGLE else
                        min(CAP[role]-len(members),len(candidates)))
        if not candidates or max_allowed<=0:
            msg=('Posti completi. Usa Rimuovi per liberare un posto.'
                 if mode=='assign' and role not in SINGLE
                 and len(members)>=CAP[role]
                 else 'Non ci sono Sim idonei disponibili per questo incarico.')
            _notice(actor,'MY HIGH SCHOOL',msg)
            return False
        offered={canonical_sim_id(info.sim_id) for info in candidates}
        action='Scegli / sostituisci' if mode=='assign' else 'Rimuovi'
        dialog=UiSimPicker.TunableFactory().default(
            actor,
            title=_text('{} - {}'.format(action,_role_label(role))),
            text=_text('Scegli fino a {} adulto/i. '
                       'La spunta conferma, la X annulla. '
                       'Nessun Sim viene eliminato dal gioco.'.format(max_allowed)),
            max_selectable=_selection_strategy(max_allowed),
            min_selectable=1,should_show_names=True,
            hide_row_description=False)
        for sim in candidates:
            dialog.add_row(SimPickerRow(sim.sim_id,False,tag=sim.sim_id))
        snapshot=before.fingerprint()
        called=[False]

        def _answer(result):
            if called[0]:
                return
            called[0]=True
            if not getattr(result,'accepted',False):
                _record('CANCEL',role)
                return
            try:
                selected=tuple(canonical_sim_id(x) for x in result.get_result_tags())
                if (not 1<=len(selected)<=max_allowed
                        or len(set(selected))!=len(selected)
                        or not set(selected).issubset(offered)):
                    raise StaffError('Selezione non valida per i posti disponibili')
                # Re-check species BEFORE the save, so stale selections,
                # dog/cat/horse IDs and modified live Sims cannot be
                # appointed even if an old picker handed back their IDs.
                if mode=='assign' and not all(_still_adult(sid)
                                              for sid in selected):
                    raise StaffError('Il personale deve essere un Sim umano adulto')
                if current_slot()!=slot:
                    raise StaffError('Salvataggio cambiato')
                _SETTINGS.require_management(slot,klass)
                stats=_STAFF.apply(slot,role,mode,selected,_still_adult,snapshot)
                _record('SAVED',role+' '+mode+' '+str(stats['changed']))
                _notice(actor,'MY HIGH SCHOOL - Personale aggiornato',
                        '{}: {} persone aggiornate; totale {}/{}.'.format(
                            _role_label(role),stats['changed'],
                            stats['count'],stats['limit']))
            except Exception as exc:
                _record('BLOCKED',type(exc).__name__)
                _notice(actor,'MY HIGH SCHOOL - Nessuna modifica',
                        'Personale non aggiornato: {}'.format(str(exc)[:120]))
        dialog.add_listener(_answer)
        dialog.show_dialog()
        _record('OPEN',role+' '+mode)
        return True
    except Exception as exc:
        _record('ERROR',type(exc).__name__)
        _notice(actor,'MY HIGH SCHOOL - Errore personale',
                str(exc)[:130])
        return False


class _StaffAction(ImmediateSuperInteraction):
    _role=None
    _mode=None
    _klass=1

    def _run_interaction_gen(self,timeline):
        open_staff(self._role,self._mode,self._klass,self)
        result=super()._run_interaction_gen(timeline)
        if inspect.isgenerator(result):
            return (yield from result)
        return result


for _token,_role,_mode,_klass in STAFF_ACTIONS:
    _class_name='MHS53'+_token
    globals()[_class_name]=type(
        _class_name,(_StaffAction,),{
            '__module__':__name__,
            '_role':_role,'_mode':_mode,'_klass':_klass})
