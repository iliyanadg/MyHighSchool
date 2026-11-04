"""M105 runtime observation of EA's ORIGINAL high school Base count.

Safe: only calls NativeScheduleAudit.install and never changes the count.
Arm from home, BEFORE accompanied school travel. A missing EA classmethod
leaves the Bouncer selector unchanged and reports the inability to observe.
"""
import importlib
from mhs105_schedule_audit import NativeScheduleAudit

_AUDIT=None
_INSTALLED=False
_LAST_ERROR='NOT_ARMED'


def _candidate_weekly_day():
    """Use actual EA loaded class, fail closed on differing game APIs."""
    for path in ('venues.weekly_schedule_zone_director',
                 'venues.scheduling_zone_director'):
        try:
            module=importlib.import_module(path)
        except ImportError:
            continue
        obj=getattr(module,'WeeklyScheduleDay',None)
        if isinstance(obj,type):
            return obj
    return None


def arm_schedule_observation(plan,slot,day,home_zone,
                             context_provider,weekly_class=None):
    """Install observation only; never enable M96 nor change a guest list.

    context_provider must supply the CURRENT save/day/zone, independent of
    this saved plan, so an unrelated school or different save is ignored.
    """
    global _AUDIT,_INSTALLED,_LAST_ERROR
    _AUDIT=None
    _INSTALLED=False
    _LAST_ERROR='UNKNOWN'
    try:
        cls=weekly_class if weekly_class is not None else _candidate_weekly_day()
        if cls is None:
            _LAST_ERROR='EA_WEEKLY_DAY_CLASS_UNAVAILABLE'
            return False
        audit=NativeScheduleAudit(plan,slot,day)
        if not callable(context_provider) or not audit.install(cls,context_provider):
            _LAST_ERROR='EA_ORIGINAL_COUNT_CLASSMETHOD_UNAVAILABLE'
            return False
        _AUDIT=audit
        _INSTALLED=True
        _LAST_ERROR='NONE'
        return True
    except Exception as exc:
        _LAST_ERROR=type(exc).__name__
        return False


def observation_status():
    if _AUDIT is None:
        return {'kind':'M105_EA_SCHOOL_COUNT_AUDIT_ONLY',
                'status':'NOT_INSTALLED','reason':_LAST_ERROR,
                'game_count_changed':False,
                'm96_override_authorized':False}
    result=_AUDIT.snapshot()
    result['hook_installed']=_INSTALLED
    return result
