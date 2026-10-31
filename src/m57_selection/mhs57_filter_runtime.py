"""M57: reversible, fail-closed EA school SimFilterService interception.

This module installs two thin method wrappers once. Only exact EP12 tuning
GUIDs from school filters are eligible; all other game filter requests pass
through unchanged. No direct Sim spawn, removal, gameplay state or EA tuning
modification. The incoming method/callback signature is preserved.
"""
import os
import services
from filters.sim_filter_service import SimFilterService
from mhs_m2_game_bridge import current_slot
from mhs_m2_store import RosterStore
from mhs34_settings import SettingsStore
from mhs53_staff_store import StaffStore
from mhs57_school_manifest import make_manifest
from mhs57_filter_policy import (apply_constraints, guid_for_filter, SCHOOL_FILTERS,
                                 CORE_FILTERS, is_competing_high_school_mod)

_DIRECTORY=os.path.join(os.path.expanduser('~'),'Documents','Electronic Arts',
                        'The Sims 4','MY_HIGH_SCHOOL_M25_TEST_DATA')
_ROSTERS=RosterStore(_DIRECTORY)
_STAFF=StaffStore(_DIRECTORY)
_SETTINGS=SettingsStore(_DIRECTORY)
_INSTALLED=False
_HOOK_ERRORS=[]
_STATS={'constrain':0,'preserve':0,'bypass':0,'error':0}
_LAST_EVENT='Filtro M57 in attesa della selezione EA'
_LAST_ERROR='nessuno'
_ERROR_SAMPLES=[]
_CONFLICTS=()
# Bounded counters of EA filter tuning GUIDs, never SimIDs or names.
_FILTER_OBSERVATIONS={}
_FILTER_RECENCY=[]
_FILTER_CALLS=0
_FILTER_LIMIT=64
_EA_GENERIC_FACULTY=280457


def _find_conflicting_school_mods():
    """One-time filename-only scan; never touch or delete another mod.

    Only known EP12 high-school controller filenames are considered. The
    developer's name by itself is NOT a conflict: elementary school and
    unrelated interactions must remain compatible by default.
    """
    mods=os.path.join(os.path.expanduser('~'),'Documents',
                      'Electronic Arts','The Sims 4','Mods')
    found=set()
    try:
        for root, folders, files in os.walk(mods):
            for name in files:
                if is_competing_high_school_mod(name):
                    found.add(name)
    except Exception:
        return ('Ricerca incompatibilita non disponibile',)
    return tuple(sorted(found))


_CONFLICTS=_find_conflicting_school_mods()


def _log(status, filter_id=None, detail=''):
    global _LAST_EVENT, _LAST_ERROR
    if status in _STATS:
        _STATS[status]+=1
    message='{} filtro {}: {}'.format(
        status, filter_id if filter_id is not None else '?',str(detail)[:130])
    _LAST_EVENT=message
    if status=='error':
        _LAST_ERROR=message
        if message not in _ERROR_SAMPLES:
            _ERROR_SAMPLES.append(message)
            del _ERROR_SAMPLES[:-4]


def _record_filter_call(guid, method):
    """Observe EA service use even when filtering is not changed.

    Use bounded counters only. Keep the recently-used GUIDs when more than
    64 different filters run; do not store Sims or private save data.
    """
    global _FILTER_CALLS
    _FILTER_CALLS += 1
    if guid is None:
        return
    if guid in _FILTER_OBSERVATIONS:
        old=_FILTER_OBSERVATIONS[guid]
        _FILTER_OBSERVATIONS[guid]=(old[0]+1, old[1]+(1 if method=='matching' else 0))
        _FILTER_RECENCY.remove(guid)
    else:
        if len(_FILTER_RECENCY)>=_FILTER_LIMIT:
            _FILTER_OBSERVATIONS.pop(_FILTER_RECENCY.pop(0),None)
        _FILTER_OBSERVATIONS[guid]=(1,1 if method=='matching' else 0)
    _FILTER_RECENCY.append(guid)


def filter_observation_status():
    """Read-only counts of real EA calls, distinct from successful overrides."""
    hits=sorted(_FILTER_OBSERVATIONS.items(),
                key=lambda row:(-row[1][0],row[0]))
    shown=', '.join('{}x{}'.format(guid,counts[0])
                    for guid,counts in hits[:8]) or 'nessun GUID'
    school_calls=sum(counts[0] for guid,counts in hits
                     if guid in SCHOOL_FILTERS)
    staff_generic=_FILTER_OBSERVATIONS.get(_EA_GENERIC_FACULTY,(0,0))[0]
    return ('M57d API EA: chiamate {}; filtri scuola riconosciuti {}; '
            'faculty generico 280457: {}; ID frequenti: {}'.format(
                _FILTER_CALLS,school_calls,staff_generic,shown))


def _manifest():
    """Never guess an old slot after travel and never persist any game state."""
    slot=current_slot(allow_travel=True)
    settings=_SETTINGS.load(slot)
    if not settings.active:
        return None
    roster=_ROSTERS.load(slot)
    staff=_STAFF.load(slot)
    count=settings.class_count
    from sims.sim_info_types import Age,Species
    household=services.active_household()
    members=tuple(household.sim_info_gen()) if household is not None else ()
    teen_ids=tuple(getattr(s,'sim_id') for s in members
                   if getattr(s,'age',None)==Age.TEEN
                   and getattr(s,'species',None)==Species.HUMAN)
    return make_manifest(roster,staff,count,teen_ids)


def _m60_present_ids():
    """Aggregate current on-zone Sim IDs; read-only and only for base pupils."""
    manager=services.sim_info_manager()
    if manager is None:
        return ()
    seen=[]
    for info in manager.get_all():
        try:
            if info.get_sim_instance() is not None:
                seen.append(str(info.sim_id))
        except Exception:
            continue
    return tuple(seen)


def _filtered(original, self, args, kwargs, method):
    # Avoid any file reads for the vast majority of EA filters.
    idx=1 if method=='matching' else 0
    tuning=kwargs.get('sim_filter',args[idx] if len(args)>idx else None)
    guid=guid_for_filter(tuning)
    _record_filter_call(guid,method)
    if guid not in SCHOOL_FILTERS:
        return original(self,*args,**kwargs)
    if _CONFLICTS:
        _log('preserve',guid,'Altro controller liceo installato')
        return original(self,*args,**kwargs)
    # The five Core NPC positions (clubs, mean Sim, rivals) are owned by EA.
    # They must NEVER depend on the MHS roster/staff manifest, which may not
    # yet be loaded while EA is choosing morning school jobs.
    if guid in CORE_FILTERS:
        _log('preserve',guid,'Ruolo speciale EA, nessuna restrizione')
        return original(self,*args,**kwargs)
    try:
        plan=_manifest()
        if plan is None:
            _log('preserve',guid,'Gestione scuola inattiva')
            return original(self,*args,**kwargs)
        # M60: for the six Base Student filter requests, prefer enrolled teens
        # not physically on-zone yet. All other filters remain unchanged.
        # When offline tests execute the isolated EA adapter, this optional
        # observation is absent and the original registry constraints apply.
        present=(_m60_present_ids() if guid==280516 else ())
        newargs,newkwargs,report=apply_constraints(
            args,kwargs,method,plan,exclude_student_ids=present)
        _log(report[0],guid,report[2])
    except Exception as exc:
        # Never risk a crash in school bouncer filtering, or choose an ID
        # belonging to a different save by using a stale manifest.
        _log('error',guid,'{}: {}'.format(
            type(exc).__name__,str(exc)[:105]))
        return original(self,*args,**kwargs)
    return original(self,*newargs,**newkwargs)


def install_filter_hooks():
    global _INSTALLED
    if _INSTALLED:
        return True
    try:
        # EA public methods are named submit_*; the constraint policy uses
        # the logical modes 'matching'/'filter'. Passing the API method name
        # directly raised ManifestError("Unsupported EA filter method") for
        # every attempted school filter in the user's M57b Mac test.
        for method, mode in (('submit_matching_filter','matching'),
                             ('submit_filter','filter')):
            old=getattr(SimFilterService,method,None)
            if not callable(old):
                raise RuntimeError('API EA assente: '+method)
            if getattr(old,'_mhs57_school_filter_hook',False):
                continue

            def wrapper(self,*args,_previous=old,_mode=mode,**kwargs):
                return _filtered(_previous,self,args,kwargs,_mode)
            wrapper._mhs57_school_filter_hook=True
            setattr(SimFilterService,method,wrapper)
        _INSTALLED=True
        return True
    except Exception as exc:
        _log('error',None,'Hook install failed '+type(exc).__name__)
        return False


def installed():
    return _INSTALLED


def physical_status():
    """Read-only comparison of loaded on-zone SimIDs, not attendance roles."""
    try:
        plan=_manifest()
        if plan is None:
            return 'M57 confronto lotto: gestione non attiva'
        manager=services.sim_info_manager()
        if manager is None:
            return 'M57 confronto lotto: archivio Sim non pronto'
        loaded=set()
        for info in manager.get_all():
            try:
                sim=getattr(info,'get_sim_instance',lambda:None)()
                if sim is not None:
                    loaded.add(str(info.sim_id))
            except Exception:
                continue
        school_seen=len(loaded & plan.all_student_ids)
        # The distinction between teens and non-teen visitors is crucial:
        # this does not call every unregistered person an "extra student".
        from sims.sim_info_types import Age,Species
        stray=0
        for info in manager.get_all():
            try:
                sid=str(info.sim_id)
                if sid in loaded and sid not in plan.all_student_ids and (
                        info.age==Age.TEEN and info.species==Species.HUMAN):
                    stray+=1
            except Exception:
                continue
        planned_staff=set()
        for members in plan.staff_ids.values():
            planned_staff.update(members)
        staff_seen=len(loaded.intersection(planned_staff))
        return ('M57 Sim visibili sul lotto: iscritti {}/{}; altri adolescenti '
                '{} (anche giocabili non iscritti); personale scelto {}/{} '
                '(presenza, NON ruolo EA)'.format(
                    school_seen,len(plan.all_student_ids),stray,
                    staff_seen,len(planned_staff)))
    except Exception as exc:
        return 'M57 confronto lotto non disponibile: {}'.format(
            type(exc).__name__)


def m59_snapshot():
    """Read-only aggregate matching of enrolled teens and actual on-zone Sims."""
    result={'filter_calls':_FILTER_CALLS,
            'school_filter_counts':{
                str(k):v[0] for k,v in _FILTER_OBSERVATIONS.items()
                if k in SCHOOL_FILTERS},
            'constraint_success':_STATS['constrain'],
            'constraint_preserved':_STATS['preserve'],
            'errors':_STATS['error'],
            'manifest_available':False}
    try:
        plan=_manifest()
        if plan is None:
            return result
        result['manifest_available']=True
        result['registered_students']=len(plan.all_student_ids)
        manager=services.sim_info_manager()
        if manager is None:
            return result
        actual=set()
        for info in manager.get_all():
            try:
                if info.get_sim_instance() is not None:
                    actual.add(str(info.sim_id))
            except Exception:
                continue
        result['registered_present_on_zone']=len(actual.intersection(plan.all_student_ids))
        result['registered_missing_on_zone']=len(plan.all_student_ids-actual)
    except Exception as exc:
        result['snapshot_error']=type(exc).__name__
    return result


def status():
    return ('Selezione M57d: {}. Filtri limitati: {} | non modificati: {} '
            '| errori: {}. Ultimo: {}. Ultimo errore: {}'.format(
                'bloccata (altre mod liceo: {})'.format(
                    ', '.join(_CONFLICTS[:2])) if _CONFLICTS
                else ('installata' if _INSTALLED else 'non installata'),
                _STATS['constrain'],_STATS['preserve']+_STATS['bypass'],
                _STATS['error'],_LAST_EVENT,_LAST_ERROR))


install_filter_hooks()
