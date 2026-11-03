"""M120 experimental Mac: 8 exactly enrolled Base NPCs, original EA hooks.

Extends M119's actual live result: one EA Base assigned NPC observed at
08:13 and 10:32. No manual Core promotion, no extra student generation.
Native original EA Base count (3,3) may be raised to (8,8) only in
school context, using the EA calendar classmethod owner.
One test save only; not a complete 16-student classroom controller.
"""
import os
import services
import sims4.commands
from sims.sim_info_types import Age, Species
from filters.tunable import TunableSimFilter
from mhs_m2_game_bridge import current_slot
from mhs_m2_store import RosterStore
from mhs34_settings import SettingsStore
from mhs97_core_role_store import CoreRoleStore

FOLDER=os.path.join(os.path.expanduser('~'),'Documents',
    'Electronic Arts','The Sims 4','MY_HIGH_SCHOOL_M25_TEST_DATA')
SCHOOL_SCHEDULES=frozenset((277657,279958))
BASE_SITUATION=277733
BASE_JOB=277894
CORE_JOBS=frozenset((278965,278966,278967,278968,303765))
_RUNTIME=None


def zone_schedule():
    zone=services.current_zone()
    venue=services.venue_service()
    director=venue.get_zone_director() if venue else None
    return (getattr(zone,'id',None),
            getattr(getattr(director,'_schedule',None),'guid64',None))


def registered_eight():
    slot=str(current_slot(allow_travel=False))
    setting=SettingsStore(FOLDER).load(slot)
    if not setting.active or setting.class_count!=2:
        raise ValueError('Attiva due classi MHS')
    roster=RosterStore(FOLDER).load(slot)
    enrolled=tuple(str(i) for klass in (1,2)
                   for i in roster.class_members(klass))
    if len(enrolled)!=16 or len(set(enrolled))!=16:
        raise ValueError('Registro deve contenere due classi da 8')
    household=services.active_household()
    if household is None:
        raise ValueError('Nessuna famiglia attiva')
    played=tuple(str(info.sim_id) for info in household.sim_info_gen()
                 if getattr(info,'age',None)==Age.TEEN
                 and getattr(info,'species',None)==Species.HUMAN)
    if len(played)!=3 or not set(played)<=set(enrolled):
        raise ValueError('Tre teen giocabili devono essere iscritti')
    core=CoreRoleStore(FOLDER).load(slot)
    pinned=core.chosen() if core.complete else {}
    if (set(pinned)!=CORE_JOBS or len(set(pinned.values()))!=5
            or not set(pinned.values())<=set(enrolled)-set(played)):
        raise ValueError('Servono 5 ruoli Core manuali, NPC iscritti')
    base=tuple(sid for sid in enrolled
               if sid not in played and sid not in pinned.values())
    if len(base)!=8 or len(set(base))!=8:
        raise ValueError('Base deve contenere 8 NPC esatti')
    mgr=services.sim_info_manager()
    if mgr is None:
        raise ValueError('SimInfoManager assente')
    for sid in enrolled:
        info=mgr.get(int(sid))
        if (info is None or getattr(info,'age',None)!=Age.TEEN
                or getattr(info,'species',None)!=Species.HUMAN):
            raise ValueError('Sim iscritto non umano teen')
        if sid in base and getattr(info,'is_selectable',True) is not False:
            raise ValueError('Base scelto non NPC')
    return slot,base


class EightBaseController(object):
    def __init__(self,slot,targets,home_zone,manager_owner,bouncer_owner,
                 schedule_owner,job,blank,guest_cls,invited):
        self.slot=slot
        self.targets=tuple(targets)
        self.home_zone=home_zone
        self.manager_owner=manager_owner
        self.bouncer_owner=bouncer_owner
        self.schedule_owner=schedule_owner
        self.job=job
        self.blank=blank
        self.guest_cls=guest_cls
        self.invited=invited
        self.previous={}
        self.wrappers={}
        self.current=None
        self.created={}
        self.pending=None
        self._tracked={}
        self.base_count_calls=0
        self.base_count_overrides=0
        self.base_count_last=None
        self.filter_hits=0
        self.random_blocked=0
        self.refused=0
        self.error=''
        self.active=False
        self.bound_zone=None

    def in_school(self):
        try:
            zone,schedule=zone_schedule()
            return (zone is not None and zone!=self.home_zone
                    and schedule in SCHOOL_SCHEDULES
                    and str(current_slot(allow_travel=True))==self.slot)
        except Exception:
            return False

    def guest_clone(self,old,sim_id):
        if old is None:
            return None
        try:
            existing=tuple(old.guest_info_gen())
            others=[]
            base_count=0
            for guest in existing:
                guid=getattr(getattr(guest,'job_type',None),'guid64',None)
                if guid==BASE_JOB:
                    base_count+=1
                    if base_count>1:
                        return None
                elif guid in (277895,278963):
                    others.append(guest)
                else:
                    return None
            replacement=type(old)(
                invite_only=True,host_sim_id=old.host_sim_id,
                filter_requesting_sim_id=old.filter_requesting_sim_id)
            for guest in others:
                replacement.add_guest_info(guest.clone_for_guest_list())
            guest=self.guest_cls.construct_from_purpose(
                int(sim_id),self.job,self.invited)
            if (str(getattr(guest,'sim_id',None))!=sim_id
                    or getattr(guest,'accept_alternate_sim',None) is not False):
                return None
            replacement.add_guest_info(guest)
            actual=tuple(replacement.guest_info_gen())
            if (len(actual)!=len(others)+1
                    or str(actual[-1].sim_id)!=sim_id):
                return None
            return replacement
        except Exception:
            return None

    def eligible(self,request):
        if not self.active or not self.in_school():
            return False
        sid=str(getattr(request,'_requested_sim_id',None))
        if (sid not in self.targets or (sid!=self.pending and
              sid not in self.created)
                or getattr(getattr(request,'_situation',None),'guid64',None)
                   !=BASE_SITUATION
                or getattr(getattr(request,'_job_type',None),'guid64',None)
                   !=BASE_JOB):
            return False
        zone,_=zone_schedule()
        if zone!=self.bound_zone:
            return False
        constrained=getattr(request,'_constrained_sim_ids',None)
        if (type(constrained) not in (set,frozenset,list,tuple)
                or set(constrained)!={int(sid)}
                or getattr(request,'_for_persisted_sim',None) is not False
                or getattr(request,'_continue_if_constraints_fail',None)
                   is not False
                or getattr(request,'_sim_filter',None) is not
                   getattr(getattr(request,'_job_type',None),'filter',None)):
            return False
        info=services.sim_info_manager().get(int(sid))
        return (info is not None and getattr(info,'age',None)==Age.TEEN
                and getattr(info,'species',None)==Species.HUMAN
                and getattr(info,'is_selectable',True) is False)

    def install(self):
        manager=self.manager_owner
        request=self.bouncer_owner
        day=self.schedule_owner
        methods=((manager,'create_situation'),
                 (request,'__init__'),
                 (request,'get_additional_filter_terms'),
                 (request,'clone_for_replace'),
                 (day,'get_long_term_situation_count'))
        if (len(self.targets)!=8 or len(set(self.targets))!=8
                or any(name not in owner.__dict__
                       for owner,name in methods)):
            return False
        originals={(owner,name):owner.__dict__[name]
                   for owner,name in methods}
        descriptor=originals[(day,'get_long_term_situation_count')]
        if not isinstance(descriptor,classmethod):
            return False
        for original in originals.values():
            func=original.__func__ if isinstance(original,classmethod) else original
            if (not callable(func)
                    or getattr(func,'_mhs120_hook',False)
                    or getattr(func,'_mhs119_hook',False)):
                return False
        original_create=originals[(manager,'create_situation')]
        original_init=originals[(request,'__init__')]
        original_terms=originals[(request,'get_additional_filter_terms')]
        original_clone=originals[(request,'clone_for_replace')]
        original_count=descriptor.__func__

        def count(cls,data,resolver):
            result=original_count(cls,data,resolver)
            if (not self.active or not self.in_school()
                    or getattr(cls,'guid64',None) not in SCHOOL_SCHEDULES
                    or getattr(getattr(data,'situation',None),'guid64',None)
                       !=BASE_SITUATION):
                return result
            self.base_count_calls+=1
            self.base_count_last=result
            if (result==(3,3) and not self.created
                    and self.pending is None):
                self.base_count_overrides+=1
                return (8,8)
            return result

        def create(obj,kind,*args,**kwargs):
            if (not self.active or not self.in_school()
                    or getattr(kind,'guid64',None)!=BASE_SITUATION
                    or len(self.created)>=8
                    or self.pending is not None):
                return original_create(obj,kind,*args,**kwargs)
            if 'guest_list' in kwargs and args:
                return original_create(obj,kind,*args,**kwargs)
            old=kwargs.get('guest_list',args[0] if args else None)
            target=next((sid for sid in self.targets
                         if sid not in self.created),None)
            if target is None:
                return original_create(obj,kind,*args,**kwargs)
            prepared=self.guest_clone(old,target)
            if prepared is None:
                self.refused+=1
                return original_create(obj,kind,*args,**kwargs)
            self.pending=target
            self.bound_zone=zone_schedule()[0]
            try:
                if 'guest_list' in kwargs:
                    call=dict(kwargs,guest_list=prepared)
                    native=original_create(obj,kind,*args,**call)
                elif args:
                    native=original_create(obj,kind,prepared,*args[1:],
                                           **kwargs)
                else:
                    self.refused+=1
                    return original_create(obj,kind,*args,**kwargs)
                if type(native) is int and native>0:
                    self.created[target]=native
                else:
                    self.error='EA_NO_SITUATION_ID'
                    # Do not advance to a different Sim on the next call
                    # until the original create returned an ID.
                return native
            except Exception as exc:
                self.error='EA_CREATE_'+type(exc).__name__
                raise
            finally:
                self.pending=None

        def request_init(obj,*args,**kwargs):
            original_init(obj,*args,**kwargs)
            if self.eligible(obj):
                try:
                    prior=obj._sim_filter
                    self._tracked[obj]=prior
                    obj._sim_filter=self.blank
                    self.filter_hits+=1
                except Exception:
                    self._tracked.pop(obj,None)

        def terms(obj):
            if obj in self._tracked:
                if self.in_school() and obj._sim_filter is self.blank:
                    return ()
                prior=self._tracked.pop(obj)
                if obj._sim_filter is self.blank:
                    obj._sim_filter=prior
            return original_terms(obj)

        def clone(obj,*args,**kwargs):
            if obj in self._tracked and self.in_school():
                self.random_blocked+=1
                return None
            return original_clone(obj,*args,**kwargs)

        functions=((manager,'create_situation',create),
                   (request,'__init__',request_init),
                   (request,'get_additional_filter_terms',terms),
                   (request,'clone_for_replace',clone),
                   (day,'get_long_term_situation_count',classmethod(count)))
        for _,_,fn in functions:
            f=fn.__func__ if isinstance(fn,classmethod) else fn
            f._mhs120_hook=True
        changed=[]
        try:
            for owner,name,fn in functions:
                setattr(owner,name,fn)
                changed.append((owner,name))
        except Exception:
            for owner,name in reversed(changed):
                setattr(owner,name,originals[(owner,name)])
            return False
        self.previous=originals
        self.wrappers={(owner,name):fn for owner,name,fn in functions}
        self.active=True
        return True

    def stop(self):
        if not self.active:
            return False
        if any(owner.__dict__.get(name) is not fn
               for (owner,name),fn in self.wrappers.items()):
            self.error='THIRD_PARTY_RESTORE_CONFLICT'
            return False
        for req,prior in tuple(self._tracked.items()):
            if getattr(req,'_sim_filter',None) is self.blank:
                req._sim_filter=prior
        self._tracked.clear()
        for (owner,name),prior in self.previous.items():
            setattr(owner,name,prior)
        self.active=False
        return True

    def native_job_status(self,sid,situation_id):
        if not self.in_school():
            return 'FUORI_LICEO'
        try:
            manager=services.get_zone_situation_manager()
            situation=manager.get(situation_id) if manager else None
            if situation is None:
                return 'SITUAZIONE_SCOMPARSA'
            if getattr(situation,'guid64',None)!=BASE_SITUATION:
                return 'SITUAZIONE_ERRATA'
            jobs=tuple(situation.all_jobs_gen())
            selected=[job for job in jobs
                      if getattr(job,'guid64',None)==BASE_JOB]
            if len(selected)!=1:
                return 'RUOLO_BASE_NON_UNICO'
            sims=tuple(situation.all_sims_in_job_gen(selected[0]))
            ids=set()
            for sim in sims:
                a=getattr(sim,'sim_id',None)
                b=getattr(sim,'id',None)
                if a is not None and b is not None and a!=b:
                    return 'ID_AMBIGUO'
                ident=a if a is not None else b
                if type(ident) is not int:
                    return 'ID_NON_VALIDO'
                ids.add(str(ident))
            if ids=={sid}:
                return 'PRESENTE'
            return 'ALTRO_SIM' if ids else 'VUOTO'
        except Exception as exc:
            return 'LETTURA_'+type(exc).__name__

    def report(self):
        checked=[(sid,self.native_job_status(sid,sit))
                 for sid,sit in self.created.items()]
        present=sum(status=='PRESENTE' for _,status in checked)
        missing=tuple(sid for sid,status in checked if status!='PRESENTE')
        return ('M120 active={} EA_base_created={}/8 EA_base_present={}/8 '
                'count_override={} native_count={} filter={} '
                'blocked_random={} refused={} missing={} error={}'.format(
                    self.active,len(self.created),present,
                    self.base_count_overrides,self.base_count_last,
                    self.filter_hits,self.random_blocked,self.refused,
                    ','.join(missing) or 'none',self.error or 'none'))


def arm_m120():
    global _RUNTIME
    if _RUNTIME is not None and _RUNTIME.active:
        return 'M120 gia attiva: '+_RUNTIME.report()
    try:
        zone,schedule=zone_schedule()
        if zone is None or schedule in SCHOOL_SCHEDULES:
            return 'M120 BLOCCATA: armare da casa prima della scuola'
        slot,targets=registered_eight()
        from situations.situation_manager import SituationManager
        from situations.bouncer.bouncer_request import BouncerRequest
        from situations.situation_guest_list import (
            SituationGuestInfo,SituationInvitationPurpose)
        from venues.weekly_schedule_zone_director import WeeklyScheduleDay
        from sims4.resources import Types
        day=next((c for c in WeeklyScheduleDay.__mro__
                  if isinstance(c.__dict__.get(
                      'get_long_term_situation_count'),classmethod)),None)
        job=services.get_instance_manager(Types.SITUATION_JOB).get(BASE_JOB)
        blank=TunableSimFilter.BLANK_FILTER
        if (day is None or job is None
                or getattr(job,'guid64',None)!=BASE_JOB
                or blank is None
                or not callable(getattr(blank,'get_filter_terms',None))):
            return 'M120 BLOCCATA: tuning EA non compatibile'
        trial=EightBaseController(slot,targets,zone,SituationManager,
            BouncerRequest,day,job,blank,SituationGuestInfo,
            SituationInvitationPurpose.INVITED)
        if not trial.install():
            return 'M120 BLOCCATA: owner EA modificato o non disponibile'
        _RUNTIME=trial
        return 'M120 PRONTA: 8 NPC Base fissi (5 Core esclusi)'
    except Exception as exc:
        return 'M120 NON ATTIVA: '+type(exc).__name__+': '+str(exc)[:100]


@sims4.commands.Command('mhs120.arm',
    command_type=sims4.commands.CommandType.Live)
def m120arm(_connection=None):
    sims4.commands.output(arm_m120(),_connection)


@sims4.commands.Command('mhs120.status',
    command_type=sims4.commands.CommandType.Live)
def m120status(_connection=None):
    sims4.commands.output(
        _RUNTIME.report() if _RUNTIME is not None
        else 'M120 non attiva',_connection)


@sims4.commands.Command('mhs120.stop',
    command_type=sims4.commands.CommandType.Live)
def m120stop(_connection=None):
    sims4.commands.output(
        ('M120 RIPRISTINATA' if _RUNTIME.stop()
         else 'M120 RIPRISTINO BLOCCATO: '+_RUNTIME.error)
        if _RUNTIME is not None else 'M120 non attiva',_connection)
