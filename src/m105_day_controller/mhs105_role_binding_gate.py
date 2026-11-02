"""M105 — verify *actual EA situation job membership* before claiming Core.

A successful original EA SimFilter query or matching filter override
does not prove that the selected Sim is assigned to a SituationJob.
Only caller-supplied, independently observed membership from an active EA
core situation can authorize this post-spawn verification.

This pure module does NOT import Sims APIs, spawn Sims or change game data.
UNKNOWN is not a negative match and is not evidence of successful binding.
"""
from mhs105_atomic_school_roster import CORE_JOBS

def _id(value):
    if type(value) not in (str,int):
        return None
    s=str(value)
    if not s.isdigit() or int(s)<=0 or str(int(s))!=s:
        return None
    return s

def _blocked(reason,**extra):
    result={'status':'NOT_VERIFIED','reason':reason,
            'actual_ea_core_binding_verified':False,
            'before_school_spawn_reservation_proved':False,
            'mutated_ea':False}
    result.update(extra)
    return result

def verify_core_membership(plan,observed_job_members,
                           observed_school_context=False,
                           observed_same_save=False,
                           observed_same_day=False,
                           observed_situation_is_ea_core=False,
                           observed_on_lot_ids=None):
    """Verify 5 exact EA Core SituationJob-to-Sim bindings from live evidence.

    observed_job_members: job_id -> iterable of *actual SituationJob
    members*; not filtered candidates, not guest IDs, not registration.
    A job may have exactly one member in this single-role plan.
    This is a POST-SPAWN check. It MUST NOT authorize retroactive
    pre-spawn permission for the Base situation count.
    """
    if (not isinstance(plan,dict)
            or plan.get('status')!='PREPARED_NOT_EA_BOUND'
            or plan.get('all_core_appointments_confirmed') is not True):
        return _blocked('no confirmed whole-day enrollment plan')
    if not (observed_school_context is True and
            observed_same_save is True and
            observed_same_day is True and
            observed_situation_is_ea_core is True):
        return _blocked('school/core situation context not verified')
    if not isinstance(observed_job_members,dict):
        return _blocked('no live EA job-to-Sim membership data')
    if set(observed_job_members)!=set(CORE_JOBS):
        return _blocked('one or more core job memberships unavailable')
    expected=dict(plan.get('core_role_assignments',()))
    if set(expected)!=set(CORE_JOBS) or len(set(expected.values()))!=5:
        return _blocked('invalid core reservation plan')
    seen={}
    for job in CORE_JOBS:
        members=observed_job_members[job]
        if not isinstance(members,(tuple,list,set,frozenset)):
            return _blocked('unreadable EA membership for job {}'.format(job))
        ids=tuple(_id(sim) for sim in members)
        if (len(ids)!=1 or ids[0] is None
                or ids[0]!=expected[job]):
            return _blocked('real EA membership differs for job {}'.format(job),
                            failing_job=job,
                            observed_ids=tuple(x for x in ids if x is not None))
        seen[job]=ids[0]
    if len(set(seen.values()))!=5:
        return _blocked('a Sim holds multiple EA school core jobs')
    if not isinstance(observed_on_lot_ids,(tuple,list,set,frozenset)):
        return _blocked('on-lot evidence not available')
    on_lot=tuple(_id(x) for x in observed_on_lot_ids)
    if None in on_lot:
        return _blocked('invalid physical Sim IDs')
    if not set(seen.values())<=set(on_lot):
        return _blocked('a bound EA core Sim is not physically on lot')
    return {'status':'FIVE_ACTUAL_EA_CORE_MEMBERS_VERIFIED',
            'actual_ea_core_binding_verified':True,
            'before_school_spawn_reservation_proved':False,
            'observed_job_members':tuple((job,seen[job]) for job in CORE_JOBS),
            'actual_ea_on_lot_count':5,
            'full_16_present_verified':False,
            'eight_per_class_verified':False,
            'mutated_ea':False}
