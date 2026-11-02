"""M105: read-only real EA SituationJob-to-Sim membership, post-spawn.

Uses M85's proven SituationManager.get_situations_sim_is_in(sim). But the
job getter itself is not yet proven in the user's current Sims build, so
it is probed conservatively. If an EA job API is unavailable or a role
cannot be read, return UNKNOWN; NEVER infer jobs from guest lists,
MHS user settings, SimFilter results, or Situation type alone.

This is for the M105 acceptance gate; no spawning or EA state changes.
"""
from mhs105_atomic_school_roster import CORE_JOBS
from mhs105_role_binding_gate import verify_core_membership

CORE_SITUATION_GUID=298052

def _guid(tuned):
    if tuned is None:
        return None
    for entry in (tuned,getattr(tuned,'tuned_class',None),type(tuned)):
        if entry is None:
            continue
        guid=getattr(entry,'guid64',None)
        if type(guid) is int and guid>0:
            return guid
    return None

def _job_for_sim(situation,sim):
    # These are potential EA read methods; no call is made if unavailable.
    # One name may differ across EA game versions. Only accept an actual
    # SituationJob object whose guid64 matches one of the five known jobs.
    # BaseSituation exposes get_current_job_for_sim in the user's
    # decompiled EA version. Use the verified native API first, then
    # retain harmless legacy fallbacks for other game revisions.
    for name in ('get_current_job_for_sim','get_job_for_sim',
                 'get_situation_job_for_sim','get_job_type_for_sim'):
        method=getattr(situation,name,None)
        if not callable(method):
            continue
        try:
            job=method(sim)
        except Exception:
            continue
        guid=_guid(job)
        if guid is not None:
            return guid
    return None

def inspect_core_jobs(plan,sim_infos,situation_manager,teen_age,
                      human_species,school_verified=False,
                      save_verified=False,day_verified=False):
    """Return live role-binding proof only when 5 real EA roles are visible.

    A known CoreSituation type without the job getter is insufficient.
    Situations are discovered through an existing live Sim's membership
    API; nothing is created, destroyed or reassigned.
    """
    blocked={'status':'UNKNOWN',
             'reason':'EA job-level membership is not verified',
             'actual_ea_core_binding_verified':False,
             'game_changed':False}
    if not (school_verified and save_verified and day_verified):
        return dict(blocked,reason='school/save/day not verified')
    getter=getattr(situation_manager,'get_situations_sim_is_in',None)
    if not callable(getter):
        return dict(blocked,reason='EA situation membership getter unavailable')
    found={job:set() for job in CORE_JOBS}
    on_lot=set()
    core_seen=False
    unknown_jobs=0
    try:
        for info in sim_infos:
            if (getattr(info,'age',None)!=teen_age
                    or getattr(info,'species',None)!=human_species):
                continue
            sim=info.get_sim_instance()
            if sim is None:
                continue
            sid=getattr(info,'sim_id',None)
            if type(sid) is not int or sid<=0:
                continue
            on_lot.add(sid)
            for situation in tuple(getter(sim) or ()):
                if _guid(situation)!=CORE_SITUATION_GUID:
                    continue
                core_seen=True
                job=_job_for_sim(situation,sim)
                if job in found:
                    found[job].add(sid)
                else:
                    unknown_jobs+=1
    except Exception as exc:
        return dict(blocked,reason='EA core membership reading error',
                    error_type=type(exc).__name__)
    if not core_seen:
        return dict(blocked,reason='no live CoreClassNPC situation observed')
    if unknown_jobs:
        return dict(blocked,reason='some CoreClassNPC members lack verified job APIs',
                    unreadable_core_members=unknown_jobs)
    return verify_core_membership(
        plan,{job:tuple(sorted(sids)) for job,sids in found.items()},
        observed_school_context=True,
        observed_same_save=True,
        observed_same_day=True,
        observed_situation_is_ea_core=True,
        observed_on_lot_ids=tuple(sorted(on_lot)))
