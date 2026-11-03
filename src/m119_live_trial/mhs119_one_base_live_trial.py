"""M119 one-original-Base-place EA INTERVENTION beta, for a duplicate save.

This actually patches SituationManager.create_situation and the scoped
BouncerRequest methods ONLY while manually armed at home. It replaces
the original EA random Base student with ONE existing enrolled NPC,
NEVER a generated Sim. Does not alter MHS stores, Core, lessons or rooms.
It DOES NOT promise that the 13 NPCs or 16 students attend.

The stop command restores original descriptors and any still-live request
filter values. No clock-driven automatic activation and no save writes.
On broken or unrecognized original EA values, returns the vanilla call
untouched. One Base attempt per session; other Base situations are vanilla.
"""
import os
import services
import sims4.commands
from sims.sim_info_types import Age, Species
from filters.tunable import TunableSimFilter
from mhs_m2_game_bridge import current_slot
from mhs_m2_store import RosterStore
from mhs34_settings import SettingsStore

BASE_GUID = 277733
BASE_JOB = 277894
SCHOOL_SCHEDULES = frozenset((277657,279958))
DATA = os.path.join(os.path.expanduser('~'),'Documents',
                    'Electronic Arts','The Sims 4',
                    'MY_HIGH_SCHOOL_M25_TEST_DATA')
_STATE = None


def _zone_schedule():
    z = services.current_zone()
    zone = getattr(z,'id',None)
    venue = services.venue_service()
    director = venue.get_zone_director() if venue else None
    return zone, getattr(getattr(director,'_schedule',None),'guid64',None)


def _read_roster():
    slot = str(current_slot(allow_travel=False))
    settings=SettingsStore(DATA).load(slot)
    if not settings.active or settings.class_count != 2:
        raise ValueError('MHS classi 1 e 2 non attive')
    roster=RosterStore(DATA).load(slot)
    selected=tuple(str(i) for c in (1,2)
                   for i in roster.class_members(c))
    if len(selected)!=16 or len(set(selected))!=16:
        raise ValueError('Registro non contiene 16 iscritti unici')
    house=services.active_household()
    if house is None:
        raise ValueError('Famiglia attiva assente')
    playable=set(str(s.sim_id) for s in house.sim_info_gen()
                 if getattr(s,'age',None)==Age.TEEN
                 and getattr(s,'species',None)==Species.HUMAN)
    if len(playable)!=3 or not playable<=set(selected):
        raise ValueError('Occorrono 3 adolescenti giocabili iscritti')
    mgr=services.sim_info_manager()
    for sid in selected:
        info=mgr.get(int(sid)) if mgr else None
        if (info is None or getattr(info,'age',None)!=Age.TEEN
                or getattr(info,'species',None)!=Species.HUMAN):
            raise ValueError('Iscritto non adolescente umano')
    # One deterministic, user-chosen enrolled NPC: first school class
    # member not in active playable family. NO random replacement.
    target=next((sid for sid in selected[:8] if sid not in playable),None)
    if target is None:
        raise ValueError('Nessun NPC disponibile in Classe 1')
    info=mgr.get(int(target))
    if getattr(info,'is_selectable',True) is not False:
        raise ValueError('Il target non e NPC non giocabile')
    return slot,target


class OneBaseTrial(object):
    def __init__(self,slot,target,home_zone,owner,request,blank,job,guest_cls,
                 guest_list_cls,invited):
        self.slot=slot
        self.target=target
        self.home_zone=home_zone
        self.owner=owner
        self.request=request
        self.blank=blank
        self.job=job
        self.guest_cls=guest_cls
        self.guest_list_cls=guest_list_cls
        self.invited=invited
        self.saved={}
        self.tracked={}
        self.attempts=0
        self.created_id=None
        self.filter_applied=0
        self.replacements_blocked=0
        self.error=''
        self.active=False
        self.call_zone=None
        self.request_refusal_count=0

    def _school(self):
        try:
            zone,schedule=_zone_schedule()
            return (zone is not None and str(zone)!=str(self.home_zone)
                    and schedule in SCHOOL_SCHEDULES
                    and str(current_slot(allow_travel=True))==self.slot)
        except Exception:
            return False

    def _new_guest_list(self,original):
        if original is None:
            return None
        try:
            old=tuple(original.guest_info_gen())
            retained=[]
            count=0
            for guest in old:
                guid=getattr(getattr(guest,'job_type',None),'guid64',None)
                if guid==BASE_JOB:
                    count+=1
                    if count>1:
                        return None
                elif guid in (277895,278963):
                    retained.append(guest)
                else:
                    return None
            replacement=type(original)(
                invite_only=True,
                host_sim_id=original.host_sim_id,
                filter_requesting_sim_id=original.filter_requesting_sim_id)
            for other in retained:
                replacement.add_guest_info(other.clone_for_guest_list())
            guest=self.guest_cls.construct_from_purpose(
                int(self.target),self.job,self.invited)
            if (str(getattr(guest,'sim_id',None))!=self.target
                    or getattr(guest,'accept_alternate_sim',None) is not False):
                return None
            replacement.add_guest_info(guest)
            actual=tuple(replacement.guest_info_gen())
            if (len(actual)!=len(retained)+1
                    or actual[-1].sim_id!=int(self.target)):
                return None
            return replacement
        except Exception:
            return None

    def _eligible(self,req):
        if not self.active or not self._school():
            return False
        if (getattr(getattr(req,'_situation',None),'guid64',None)
                !=BASE_GUID
                or getattr(getattr(req,'_job_type',None),'guid64',None)
                !=BASE_JOB
                or str(getattr(req,'_requested_sim_id',None))!=self.target
                or self.attempts!=1
                or self.call_zone is None):
            return False
        zone,_=_zone_schedule()
        if zone!=self.call_zone:
            return False
        constraints=getattr(req,'_constrained_sim_ids',None)
        if (type(constraints) not in (list,tuple,set,frozenset)
                or set(constraints)!={int(self.target)}):
            return False
        if (getattr(req,'_continue_if_constraints_fail',None) is not False
                or getattr(req,'_for_persisted_sim',None) is not False):
            return False
        if getattr(req,'_sim_filter',None) is not getattr(
                getattr(req,'_job_type',None),'filter',None):
            return False
        info=services.sim_info_manager().get(int(self.target))
        return (info is not None and getattr(info,'age',None)==Age.TEEN
                and getattr(info,'species',None)==Species.HUMAN
                and getattr(info,'is_selectable',True) is False)

    def arm(self):
        cls=self.owner
        req=self.request
        descriptor_names=((cls,'create_situation'),
                          (req,'__init__'),
                          (req,'get_additional_filter_terms'),
                          (req,'clone_for_replace'))
        if any(name not in owner.__dict__
               or getattr(owner.__dict__[name],'_mhs119_hook',False)
               for owner,name in descriptor_names):
            return False
        self.saved={(owner,name):owner.__dict__[name]
                    for owner,name in descriptor_names}
        original_create=self.saved[(cls,'create_situation')]
        original_init=self.saved[(req,'__init__')]
        original_terms=self.saved[(req,'get_additional_filter_terms')]
        original_clone=self.saved[(req,'clone_for_replace')]

        def create(manager, situation_type, *args, **kwargs):
            if (not self.active or self.attempts
                    or not self._school()
                    or getattr(situation_type,'guid64',None)!=BASE_GUID):
                return original_create(manager,situation_type,*args,**kwargs)
            if 'guest_list' in kwargs and args:
                return original_create(manager,situation_type,*args,**kwargs)
            old=kwargs.get('guest_list',args[0] if args else None)
            prepared=self._new_guest_list(old)
            if prepared is None:
                self.request_refusal_count+=1
                return original_create(manager,situation_type,*args,**kwargs)
            self.attempts=1
            self.call_zone=_zone_schedule()[0]
            try:
                if 'guest_list' in kwargs:
                    replaced=dict(kwargs,guest_list=prepared)
                    result=original_create(manager,situation_type,
                                           *args,**replaced)
                elif args:
                    result=original_create(manager,situation_type,prepared,
                                           *args[1:],**kwargs)
                else:
                    self.request_refusal_count+=1
                    self.error='EA_GUEST_LIST_CALL_SHAPE_NOT_VERIFIED'
                    return original_create(manager,situation_type,*args,**kwargs)
                if type(result) is int and result>0:
                    self.created_id=result
                else:
                    self.error='EA_CREATE_RETURNED_NO_SITUATION_ID'
                return result
            except Exception as exc:
                self.error='EA_CREATE_EXCEPTION_'+type(exc).__name__
                raise

        def request_init(obj,*args,**kwargs):
            original_init(obj,*args,**kwargs)
            if self._eligible(obj):
                try:
                    self.tracked[obj]=obj._sim_filter
                    obj._sim_filter=self.blank
                    self.filter_applied+=1
                except Exception:
                    self.tracked.pop(obj,None)

        def request_terms(obj):
            if obj in self.tracked:
                if self._school() and obj._sim_filter is self.blank:
                    return ()
                before=self.tracked.pop(obj)
                if obj._sim_filter is self.blank:
                    obj._sim_filter=before
            return original_terms(obj)

        def request_clone(obj,*args,**kwargs):
            if obj in self.tracked and self._school():
                self.replacements_blocked+=1
                return None
            return original_clone(obj,*args,**kwargs)

        for fn in (create,request_init,request_terms,request_clone):
            fn._mhs119_hook=True
        changed=[]
        try:
            for owner,name,method in (
                (cls,'create_situation',create),
                (req,'__init__',request_init),
                (req,'get_additional_filter_terms',request_terms),
                (req,'clone_for_replace',request_clone)):
                setattr(owner,name,method)
                changed.append((owner,name))
        except Exception:
            for owner,name in reversed(changed):
                setattr(owner,name,self.saved[(owner,name)])
            return False
        self.active=True
        return True

    def stop(self):
        if not self.active:
            return False
        # Refuse to clobber third-party alterations made after arming.
        if any(getattr(owner.__dict__.get(name),'_mhs119_hook',False)
               is not True for owner,name in self.saved):
            self.error='RESTORE_CONFLICT_THIRD_PARTY'
            return False
        for obj,previous in tuple(self.tracked.items()):
            if getattr(obj,'_sim_filter',None) is self.blank:
                obj._sim_filter=previous
        self.tracked.clear()
        for (owner,name),prior in self.saved.items():
            setattr(owner,name,prior)
        self.active=False
        return True

    def report(self):
        return ('M119 active={} target={} attempts={} EA_situation={} '
                'filter={} blocked_random={} refused={} error={}'.format(
                    self.active,self.target,self.attempts,
                    self.created_id or 0,self.filter_applied,
                    self.replacements_blocked,self.request_refusal_count,
                    self.error or 'none'))


def _arm():
    global _STATE
    if _STATE is not None and _STATE.active:
        return 'M119 gia attivo. ' + _STATE.report()
    try:
        zone,schedule=_zone_schedule()
        if zone is None or schedule in SCHOOL_SCHEDULES:
            return 'M119 BLOCCATA: devi partire dal lotto di casa.'
        slot,sid=_read_roster()
        from situations.situation_manager import SituationManager
        from situations.bouncer.bouncer_request import BouncerRequest
        from situations.situation_guest_list import (
            SituationGuestInfo, SituationGuestList,
            SituationInvitationPurpose)
        from sims4.resources import Types
        job=services.get_instance_manager(Types.SITUATION_JOB).get(BASE_JOB)
        blank=TunableSimFilter.BLANK_FILTER
        purpose=SituationInvitationPurpose.INVITED
        if (job is None or getattr(job,'guid64',None)!=BASE_JOB
                or blank is None
                or not callable(getattr(blank,'get_filter_terms',None))):
            return 'M119 BLOCCATA: job Base o filtro EA non trovato.'
        trial=OneBaseTrial(slot,sid,zone,SituationManager,BouncerRequest,
                           blank,job,SituationGuestInfo,SituationGuestList,
                           purpose)
        if not trial.arm():
            return 'M119 BLOCCATA: metodo EA modificato o incompatibile.'
        _STATE=trial
        return 'M119 PRONTA (1 solo NPC Base): target SimID {}.'.format(sid)
    except Exception as exc:
        return 'M119 NON ATTIVA: '+type(exc).__name__+': '+str(exc)[:90]


def _stop():
    global _STATE
    if _STATE is None:
        return 'M119 non attiva.'
    return ('M119 RIPRISTINATA' if _STATE.stop() else
            'M119 RIPRISTINO BLOCCATO: '+_STATE.error)


@sims4.commands.Command('mhs119.arm',
                        command_type=sims4.commands.CommandType.Live)
def mhs119_arm(_connection=None):
    sims4.commands.output(_arm(),_connection)


@sims4.commands.Command('mhs119.status',
                        command_type=sims4.commands.CommandType.Live)
def mhs119_status(_connection=None):
    sims4.commands.output(
        _STATE.report() if _STATE else 'M119 non attiva.',_connection)


@sims4.commands.Command('mhs119.stop',
                        command_type=sims4.commands.CommandType.Live)
def mhs119_stop(_connection=None):
    sims4.commands.output(_stop(),_connection)
