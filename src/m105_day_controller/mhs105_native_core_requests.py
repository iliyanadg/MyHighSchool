"""M105 native EA *core* SimFilter request adapter, pure Python 3.7.

Prepares the five native Bouncer submit_matching_filter calls for the
five manually confirmed school special roles. Uses only the existing EA
request; never creates a situation, spawns a Sim, alters staff, or assigns
any school job. THIS MODULE DOES NOT INSTALL AN EA HOOK.

One accepted filter result is NOT proof that the Sim spawned/held a role.
A separate live runtime must verify those five actual EA role bindings.
"""
from mhs105_atomic_school_roster import CORE_JOBS
from mhs93_verified_jobs import VERIFIED_SPECS

FILTER_TO_CORE_JOB={VERIFIED_SPECS[job][0]:job for job in CORE_JOBS}

def core_request_arguments(plan,method,filter_guid,args,kwargs,
                           verified_school=False,verified_save=False,
                           verified_day=False,original_bouncer=False):
    """(action, args, kwargs, reason): safely constrain exactly one EA job.

    Only actual original Bouncer matching calls within verified EP12 school
    may be changed. Explicit original EA constraints must not be rewritten.
    A 'block' result means a future caller must refuse the MHS override
    and must not pretend the role has been reserved or matched.
    """
    values=tuple(args)
    options=dict(kwargs)
    if method!='matching' or filter_guid not in FILTER_TO_CORE_JOB:
        return 'preserve',values,options,'not a student core matching request'
    if not all((verified_school,verified_save,verified_day,original_bouncer)):
        return 'preserve',values,options,'unverified EA school context'
    if (not isinstance(plan,dict)
            or plan.get('status')!='PREPARED_NOT_EA_BOUND'
            or plan.get('all_core_appointments_confirmed') is not True
            or plan.get('base_invites_needed')!=8
            or plan.get('playable_count')!=3
            or plan.get('core_count')!=5):
        return 'block',values,options,'not a complete confirmed 16-student plan'
    assignments=plan.get('core_role_assignments')
    if (not isinstance(assignments,(tuple,list)) or len(assignments)!=5):
        return 'block',values,options,'missing five core role assignments'
    try:
        reserved=dict(assignments)
        if set(reserved)!=set(CORE_JOBS) or len(set(reserved.values()))!=5:
            return 'block',values,options,'invalid or duplicated role assignments'
        enrolled=set(plan['all_16'])
        played=set(plan['playable'])
        base=set(plan['normal_base_ids'])
        if (len(enrolled)!=16 or len(played)!=3 or len(base)!=8
                or set(reserved.values()) & played
                or set(reserved.values()) & base
                or set(reserved.values())|played|base != enrolled):
            return 'block',values,options,'roster allocation no longer consistent'
        sid=reserved[FILTER_TO_CORE_JOB[filter_guid]]
        if type(sid) is not str or not sid.isdigit() or int(sid)<1:
            return 'block',values,options,'invalid role-bound Sim ID'
    except (TypeError,ValueError,KeyError):
        return 'block',values,options,'unreadable core plan'

    # EA SimFilterService.submit_matching_filter signature: index 4
    # is sim_constraints; index 8/9 are fallback flags, as verified
    # in M104's native request pilot. Do not touch EA callback/priority.
    existing=(options['sim_constraints'] if 'sim_constraints' in options
              else values[4] if len(values)>4 else None)
    if existing is not None:
        # If EA targeted another Sim already, it is unsafe to usurp
        # this job; we must not claim our selected teen was bound.
        return 'block',values,options,'EA request already has explicit target'
    out=list(values)
    target=(int(sid),)
    if len(out)>4:
        out[4]=target
    else:
        options['sim_constraints']=target
    for key,index in (('continue_if_constraints_fail',8),
                      ('conform_if_constraints_fail',9)):
        if len(out)>index:
            out[index]=False
        else:
            options[key]=False
    return ('constrain',tuple(out),options,
            'one enrolled human teen proposed for this EA core role')
