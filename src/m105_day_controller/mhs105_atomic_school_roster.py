"""M105: entire school-day participant planner, pure Python 3.7.

Solves *all* five school core roles jointly with eight Base Student slots,
rather than testing one NPC invitation at a time. Requires EA's actual
per-SimFilter eligibility results, not tuning GUIDs or guessed teen age.

NO EA hooks; NO Sim spawns; NO role changes; NO classroom routing.
If special-role assignments are suggested rather than user-confirmed,
they are NOT accepted as actual EA bindings or saved appointments.
"""
from itertools import combinations

BASE_JOB=277894
CORE_JOBS=(278965,278966,278967,278968,303765)
ALL_JOBS=(BASE_JOB,)+CORE_JOBS
CLASS_SIZE=8
CLASS_COUNT=2

def _id(raw):
    if type(raw) not in (str,int):
        return None
    value=str(raw)
    if not value.isdigit() or int(value)<=0 or str(int(value))!=value:
        return None
    return value

def _blocked(reason,**details):
    data={'status':'BLOCKED','reason':reason,
          'changes_to_ea':False,
          'core_roles_reserved_before_ea':False,
          'actual_ea_role_bindings_verified':False,
          'attendance_verified':False}
    data.update(details)
    return data

def _normalise_ids(raw):
    if not isinstance(raw,(tuple,list,set,frozenset)):
        return None
    ids=tuple(_id(sid) for sid in raw)
    if None in ids:
        return None
    return frozenset(ids)

def _solve(core_jobs,candidates,eligible_base,non_playable,pins):
    """Backtracking: find a disjoint core assignment leaving 8 Base-eligible.

    An NPC who fails the EA Base filter MUST occupy a compatible core job;
    moving that NPC to the Base pool just to fill a headcount is forbidden.
    """
    ordered=tuple(non_playable)
    possible={job:tuple(sid for sid in ordered if sid in candidates[job])
              for job in core_jobs}
    # Filter fixed/user-confirmed role choices first.
    chosen=dict(pins)
    used=set(chosen.values())
    pending=tuple(sorted((j for j in core_jobs if j not in chosen),
                         key=lambda j:(len(possible[j]),core_jobs.index(j))))
    def visit(i):
        if i==len(pending):
            leftovers=tuple(sid for sid in ordered if sid not in used)
            if len(leftovers)!=8 or not set(leftovers)<=eligible_base:
                return None
            return dict(chosen),leftovers
        job=pending[i]
        for sid in possible[job]:
            if sid in used:
                continue
            used.add(sid)
            chosen[job]=sid
            found=visit(i+1)
            if found is not None:
                return found
            del chosen[job]
            used.remove(sid)
        return None
    return visit(0)

def plan_school_day(classes,playable_ids,ea_eligible_by_job,
                    confirmed_core_assignments=None,
                    propose_missing_roles=False):
    """Produce one whole-day 3 + 5 + 8 roster plan; never modify EA.

    confirmed_core_assignments maps EA CORE job ID -> chosen Sim ID.
    If some choices are missing and propose_missing_roles=True, compute a
    deterministic *suggestion* for review, NEVER a confirmed assignment.
    Real EA binding and school capacity must be proved independently.
    """
    if not isinstance(classes,(tuple,list)) or len(classes)!=CLASS_COUNT:
        return _blocked('exactly two classes are required')
    groups=[]
    for group in classes:
        if not isinstance(group,(tuple,list)) or len(group)!=CLASS_SIZE:
            return _blocked('each class requires exactly eight students')
        values=tuple(_id(sid) for sid in group)
        if None in values:
            return _blocked('invalid registered student ID')
        groups.append(values)
    everyone=groups[0]+groups[1]
    if len(set(everyone))!=16:
        return _blocked('duplicate enrolled student ID')
    played=_normalise_ids(playable_ids)
    if played is None or len(played)!=3 or not played<=set(everyone):
        return _blocked('three distinct enrolled playable students required')
    non_playable=tuple(sid for sid in everyone if sid not in played)
    if len(non_playable)!=13:
        return _blocked('expected thirteen enrolled non-playable students')

    # Require results of ALL SIX current EA SimFilter jobs. An absent
    # result or a guessed global list cannot silently count as eligibility.
    if (not isinstance(ea_eligible_by_job,dict)
            or set(ea_eligible_by_job)!=set(ALL_JOBS)):
        return _blocked('live eligibility for six EA school jobs missing')
    eligible={}
    for job in ALL_JOBS:
        values=_normalise_ids(ea_eligible_by_job[job])
        if values is None:
            return _blocked('invalid EA eligibility for job {}'.format(job))
        eligible[job]=values
    npc_set=set(non_playable)
    base_eligible=eligible[BASE_JOB] & npc_set
    core_candidates={job:eligible[job]&npc_set for job in CORE_JOBS}

    if confirmed_core_assignments is None:
        confirmed_core_assignments={}
    if (not isinstance(confirmed_core_assignments,dict)
            or not set(confirmed_core_assignments)<=set(CORE_JOBS)
            or any(type(j) is not int for j in confirmed_core_assignments)):
        return _blocked('unknown or invalid core job assignment')
    pins={}
    for job,raw in confirmed_core_assignments.items():
        sid=_id(raw)
        if sid is None or sid not in core_candidates[job]:
            return _blocked('assigned student not eligible for core job {}'.format(job))
        pins[job]=sid
    if len(set(pins.values()))!=len(pins):
        return _blocked('one student selected for multiple core roles')

    # Five core roles leave precisely eight Base places. A student
    # ineligible for Base can only be retained in a compatible core role.
    not_base=tuple(sid for sid in non_playable if sid not in base_eligible)
    if len(not_base)>5:
        return _blocked('more than five NPCs fail the EA Base filter',
                        base_ineligible_count=len(not_base))
    if len(pins)<5 and not propose_missing_roles:
        return _blocked('complete five manual special-role appointments first',
                        assigned_core_roles=len(pins),
                        base_ineligible_count=len(not_base))
    found=_solve(CORE_JOBS,core_candidates,base_eligible,non_playable,pins)
    if found is None:
        return _blocked('no collision-free role and Base allocation',
                        base_ineligible_count=len(not_base),
                        assigned_core_roles=len(pins))
    core,normal=found
    # Prefer the EA-defined order for outputs, even when backtracking
    # processes constrained jobs first.
    core_roles=tuple((job,core[job]) for job in CORE_JOBS)
    assigned=tuple(sid for _,sid in core_roles)
    if len(set(assigned))!=5 or set(assigned)&played or set(normal)&set(assigned):
        return _blocked('internal overlapping student allocation')
    if set(played)|set(assigned)|set(normal)!=set(everyone):
        return _blocked('not all sixteen students are allocated')

    confirmed=(len(pins)==5)
    return {
        'status':('PREPARED_NOT_EA_BOUND' if confirmed
                  else 'PROPOSAL_NEEDS_MANUAL_CONFIRMATION'),
        'changes_to_ea':False,
        'classes':tuple(groups),
        'all_16':everyone,
        'playable':tuple(sid for sid in everyone if sid in played),
        'core_role_assignments':core_roles,
        'normal_base_ids':normal,
        'base_invites_needed':len(normal),
        'core_count':5,
        'playable_count':3,
        'base_ineligible_in_core':sum(sid in set(not_base) for sid in assigned),
        'all_core_appointments_confirmed':confirmed,
        'core_roles_reserved_before_ea':False,
        'actual_ea_role_bindings_verified':False,
        'school_zone_and_capacity_verified':False,
        'attendance_verified':False,
    }
