"""Offline-only prototype of native EA school-specific Core filter arguments.

No game imports, no hook installation. A PROPOSAL_ONLY result never changes
EA gameplay. Actual use requires later verification of the API, Bouncer
origin, original school zone, role membership, and physical attendance.
"""
from mhs93_verified_jobs import VERIFIED_SPECS
from mhs105_atomic_school_roster import CORE_JOBS,BASE_JOB

CORE_FILTER_TO_JOB={VERIFIED_SPECS[job][0]:job for job in CORE_JOBS}
BASE_FILTER_GUID=VERIFIED_SPECS[BASE_JOB][0]


def propose_school_only_filter_arguments(plan, filter_guid, args, kwargs,
                                         ea_base_filter,
                                         school=False, same_save=False,
                                         same_day=False, native_bouncer=False):
    """Prepare (action,args,kwargs,reason); DOES NOT CALL EA.

    Only original school Core SimFilter matching requests with no explicit
    EA target may receive this proposal. For a genuinely eligible Core Sim,
    keep the original filter. If a selected teen passes only original Base,
    prepare an alternative school-only Base filter but DO NOT activate it.
    """
    original=('PRESERVE',tuple(args),dict(kwargs),'not a verified school bridge')
    if (not all((school is True,same_save is True,same_day is True,
                 native_bouncer is True))
            or type(filter_guid) is not int
            or filter_guid not in CORE_FILTER_TO_JOB
            or not isinstance(plan,dict)
            or plan.get('status')!='BRIDGE_CANDIDATE_ONLY_NOT_EA_BOUND'
            or plan.get('adapter_authorized') is not False):
        return original
    core=plan.get('core_role_assignments')
    bridged=plan.get('school_only_bridge_candidates')
    if (not isinstance(core,(tuple,list)) or len(core)!=5
            or not isinstance(bridged,(tuple,list))):
        return original
    mapping=dict(core)
    override=dict(bridged)
    job=CORE_FILTER_TO_JOB[filter_guid]
    target=mapping.get(job)
    if (type(target) is not str or not target.isdigit()
            or job not in mapping or target not in plan.get('all_16',())):
        return original
    if len(set(mapping.values()))!=5:
        return original
    values=list(args)
    options=dict(kwargs)
    if not values or type(values[0]) is not int or values[0]!=1:
        return original
    if 'number_of_sims_to_find' in options:
        return original
    tuning=options.get('sim_filter',values[1] if len(values)>1 else None)
    if tuning is None:
        return original
    explicit=(options.get('sim_constraints') if 'sim_constraints' in options
              else values[4] if len(values)>4 else None)
    if explicit is not None:
        return original
    if job in override:
        if override[job]!=target or ea_base_filter is None:
            return original
        chosen_filter=ea_base_filter
        label='school-only Base filter proposal; EA job binding unproved'
    else:
        chosen_filter=tuning
        label='original Core filter proposal; EA job binding unproved'
    if 'sim_filter' in options:
        options['sim_filter']=chosen_filter
    elif len(values)>1:
        values[1]=chosen_filter
    else:
        return original
    if len(values)>4:
        values[4]=(int(target),)
    else:
        options['sim_constraints']=(int(target),)
    for key,index in (('continue_if_constraints_fail',8),
                      ('conform_if_constraints_fail',9)):
        if len(values)>index:
            values[index]=False
        else:
            options[key]=False
    return ('PROPOSAL_ONLY',tuple(values),options,label)
