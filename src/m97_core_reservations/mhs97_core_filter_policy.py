"""M97 pre-selection filter policy for the five EA school core jobs.

Pure adapter only. Caller is responsible for EARLY installation *before*
EA creates CoreClassNPCs, verifying exact school+save+day, and committing
an atomic 16-seat plan. This module makes no game API calls.
"""
from mhs93_verified_jobs import VERIFIED_SPECS,CORE_STUDENT_JOBS

# Inverse is established from the user's actual Mac M94 JSON.
FILTER_TO_JOB={VERIFIED_SPECS[job][0]:job for job in CORE_STUDENT_JOBS}

def prepare_core_filter(role_plan,filter_guid,sim_constraints=None,
                        zone_verified=False,save_verified=False,
                        session_verified=False):
    """Policy decision, never silently preserve EA random picks.

    Returns (action, exact_ids, reason) with actions:
    - bypass: unrelated filter/non-school; caller may use vanilla;
    - constrain: pass a single reserved Sim ID to EA, disable all
      fallback; a separate runtime binding verifier is still required;
    - block: after verified M97 selection, caller MUST fail closed,
      never delegate this school core request back to a random EA pool.
    """
    if type(filter_guid) is not int or filter_guid not in FILTER_TO_JOB:
        return ('bypass',None,'not a verified core school filter')
    if not(zone_verified and save_verified and session_verified):
        return ('bypass',None,'core selection inactive outside verified school session')
    if (not isinstance(role_plan,dict) or
            role_plan.get('status')!='EARLY_ROLE_PLAN_VALIDATED_NOT_EA_BOUND'):
        return ('block',None,'no complete verified manual role reservations')
    try:
        choices=tuple(role_plan['role_reservations'])
        members=tuple(str(x) for x in role_plan['all_16'])
        roles={j:str(sid) for j,sid in choices}
    except (KeyError,TypeError,ValueError):
        return ('block',None,'invalid school-role reservation')
    if (len(choices)!=5 or set(roles)!=CORE_STUDENT_JOBS
            or len(set(roles.values()))!=5 or
            not set(roles.values())<=set(members)):
        return ('block',None,'role reservation invalid or duplicated')
    job=FILTER_TO_JOB[filter_guid]
    reserved=roles[job]
    if not reserved.isdigit() or int(reserved)<1:
        return ('block',None,'invalid reserved student ID')
    if sim_constraints is not None:
        try:
            allowed=set(str(int(x)) for x in sim_constraints)
        except (ValueError,TypeError):
            return ('block',None,'unreadable explicit EA constraints')
        if reserved not in allowed:
            return ('block',None,'EA explicit requested IDs exclude registered student')
    return ('constrain',(int(reserved),),'one explicitly registered EA core student')
