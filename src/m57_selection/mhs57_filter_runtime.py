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
from mhs57_filter_policy import apply_constraints, guid_for_filter, SCHOOL_FILTERS

_DIRECTORY=os.path.join(os.path.expanduser('~'),'Documents','Electronic Arts',
                        'The Sims 4','MY_HIGH_SCHOOL_M25_TEST_DATA')
_ROSTERS=RosterStore(_DIRECTORY)
_STAFF=StaffStore(_DIRECTORY)
_SETTINGS=SettingsStore(_DIRECTORY)
_INSTALLED=False
_HOOK_ERRORS=[]
_STATS={'constrain':0,'preserve':0,'bypass':0,'error':0}
_LAST_EVENT='Filtro M57 in attesa della selezione EA'


def _log(status, filter_id=None, detail=''):
    global _LAST_EVENT
    if status in _STATS:
        _STATS[status]+=1
    _LAST_EVENT='{} filtro {}: {}'.format(status,filter_id or '?',str(detail)[:90])


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


def _filtered(original, self, args, kwargs, method):
    # Avoid any file reads for the vast majority of EA filters.
    idx=1 if method=='matching' else 0
    tuning=kwargs.get('sim_filter',args[idx] if len(args)>idx else None)
    guid=guid_for_filter(tuning)
    if guid not in SCHOOL_FILTERS:
        return original(self,*args,**kwargs)
    try:
        plan=_manifest()
        if plan is None:
            _log('preserve',guid,'Gestione scuola inattiva')
            return original(self,*args,**kwargs)
        newargs,newkwargs,report=apply_constraints(args,kwargs,method,plan)
        _log(report[0],guid,report[2])
    except Exception as exc:
        # Never risk a crash in school bouncer filtering, or choose an ID
        # belonging to a different save by using a stale manifest.
        _log('error',guid,type(exc).__name__)
        return original(self,*args,**kwargs)
    return original(self,*newargs,**newkwargs)


def install_filter_hooks():
    global _INSTALLED
    if _INSTALLED:
        return True
    try:
        for method in ('submit_matching_filter','submit_filter'):
            old=getattr(SimFilterService,method,None)
            if not callable(old):
                raise RuntimeError('API EA assente: '+method)
            if getattr(old,'_mhs57_school_filter_hook',False):
                continue

            def wrapper(self,*args,_previous=old,_name=method,**kwargs):
                return _filtered(_previous,self,args,kwargs,_name)
            wrapper._mhs57_school_filter_hook=True
            setattr(SimFilterService,method,wrapper)
        _INSTALLED=True
        return True
    except Exception as exc:
        _log('error',None,'Hook install failed '+type(exc).__name__)
        return False


def installed():
    return _INSTALLED


def status():
    return ('Selezione M57: {}. Filtri limitati: {} | non modificati: {} '
            '| errori: {}. Ultimo: {}'.format(
                'installata' if _INSTALLED else 'non installata',
                _STATS['constrain'],_STATS['preserve']+_STATS['bypass'],
                _STATS['error'],_LAST_EVENT))


install_filter_hooks()
