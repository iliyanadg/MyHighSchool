"""M106 prototype: the player's enrolled sixteen have priority over EA role filters.

Offline planner ONLY. This code does not patch SimFilters, assign jobs, create
school situations, move Sims, alter traits, or change the M105 Mac release.
A successful candidate describes a *possible future school-only filter bridge*.
It is never evidence that a native EA job accepted a student or that 16
students physically attended school.

EA 298052 has five distinct student Core roles. Its Base student situation
277733 is separate and the original schedule 277657 can request only six
Base situations. Both barriers require separate runtime engineering.
"""
from mhs105_atomic_school_roster import BASE_JOB, CORE_JOBS, ALL_JOBS

CORE_ORDER=tuple(CORE_JOBS)
CLASS_SIZE=8
PLAYABLE_COUNT=3


def _id(value):
    if type(value) not in (int,str):
        return None
    value=str(value)
    if not value.isdigit() or int(value)<1 or str(int(value))!=value:
        return None
    return value


def _blocked(reason):
    return {'status':'BLOCKED','reason':reason,
            'roster_mutated':False,'traits_mutated':False,
            'ea_school_filter_changed':False,'ea_job_binding_verified':False,
            'attendance_verified':False}


def propose_roster_first(classes, playable, eligibility, preferred_roles=None):
    """Find a candidate 3 playable + 5 Core + 8 Base without replacing teens.

    A Core role can use (a) its original job filter, or (b) an enrolled
    teen who passes EA Base Student, *only if* a future separately verified
    school-only filter adapter can safely bridge that job. This function
    does NOT install or authorize that adapter.

    Optimize for retaining the user's currently chosen five role holders,
    then for the fewest hypothetical Core filter bridges. Never invent
    external teenage NPCs or assume an ineligible Sim passes an EA filter.
    """
    if (not isinstance(classes,(tuple,list)) or len(classes)!=2
            or any(type(g) not in (tuple,list) or len(g)!=CLASS_SIZE
                   for g in classes)):
        return _blocked('two classes of eight required')
    groups=tuple(tuple(_id(x) for x in group) for group in classes)
    everyone=groups[0]+groups[1]
    if None in everyone or len(set(everyone))!=16:
        return _blocked('sixteen different registered Sim IDs required')
    if type(playable) not in (tuple,list,set,frozenset):
        return _blocked('three playable IDs required')
    played=tuple(_id(x) for x in playable)
    if None in played or len(set(played))!=PLAYABLE_COUNT or not set(played)<=set(everyone):
        return _blocked('exactly three enrolled playable teens required')
    if (type(eligibility) is not dict
            or set(eligibility)!=set(ALL_JOBS)):
        return _blocked('all six genuine EA filter result sets required')
    valid={}
    for job in ALL_JOBS:
        raw=eligibility[job]
        if type(raw) not in (tuple,list,set,frozenset):
            return _blocked('invalid scored EA result set')
        ids=tuple(_id(x) for x in raw)
        if None in ids:
            return _blocked('invalid Sim ID in EA result set')
        valid[job]=frozenset(ids)
    if preferred_roles is None:
        preferred_roles={}
    if type(preferred_roles) is not dict or not set(preferred_roles)<=set(CORE_ORDER):
        return _blocked('invalid original manual role appointments')
    preferred={}
    for job,raw in preferred_roles.items():
        sid=_id(raw)
        if sid is None:
            return _blocked('unreadable manual role appointment')
        preferred[job]=sid
    if len(set(preferred.values()))!=len(preferred):
        return _blocked('same Sim manually appointed twice')

    regular=tuple(sid for sid in everyone if sid not in set(played))
    base=valid[BASE_JOB]
    if sum(sid in base for sid in regular)<8:
        return _blocked('fewer than eight enrolled NPCs pass original EA Base filter')
    candidates={}
    for job in CORE_ORDER:
        candidates[job]=tuple(sid for sid in regular
                              if sid in valid[job] or sid in base)
        if not candidates[job]:
            return _blocked('no registered NPC can fill Core job {}'.format(job))

    best=[None]
    used=set()
    assigned={}
    def search(index,preserved,bridged):
        if index==len(CORE_ORDER):
            leftover=tuple(sid for sid in regular if sid not in used)
            if len(leftover)!=8 or any(sid not in base for sid in leftover):
                return
            # Prefer user's original choices above every other preference;
            # tie-break by fewer bridges and deterministic registration order.
            score=(-preserved,bridged,
                   tuple(regular.index(assigned[job]) for job in CORE_ORDER))
            if best[0] is None or score<best[0][0]:
                best[0]=(score,tuple((job,assigned[job])
                                    for job in CORE_ORDER),leftover)
            return
        job=CORE_ORDER[index]
        for sid in candidates[job]:
            if sid in used:
                continue
            used.add(sid)
            assigned[job]=sid
            remaining=tuple(x for x in regular if x not in used)
            if sum(x in base for x in remaining)>=8:
                search(index+1,preserved+(preferred.get(job)==sid),
                       bridged+(sid not in valid[job]))
            del assigned[job]
            used.remove(sid)
    search(0,0,0)
    if best[0] is None:
        return _blocked('no 5 Core + 8 EA-eligible Base partition for the fixed 16')

    score,core,normal=best[0]
    original=tuple((job,sid) for job,sid in core if sid in valid[job])
    bridge=tuple((job,sid) for job,sid in core if sid not in valid[job])
    return {
        'status':'BRIDGE_CANDIDATE_ONLY_NOT_EA_BOUND',
        'classes':groups,'all_16':everyone,
        'playable':tuple(sid for sid in everyone if sid in set(played)),
        'core_role_assignments':core,'normal_base_ids':normal,
        'original_ea_core_candidates':original,
        'school_only_bridge_candidates':bridge,
        'preferred_role_assignments_preserved':-score[0],
        'school_only_bridge_count':len(bridge),
        'core_count':5,'base_count':8,'playable_count':3,
        'roster_mutated':False,'traits_mutated':False,
        'ea_school_filter_changed':False,'ea_job_binding_verified':False,
        'school_capacity_verified':False,'classroom_routing_verified':False,
        'attendance_verified':False,
        'adapter_authorized':False,
        'note':('Original EA eligibility is distinct from a proposed safe '
                'school-only filter bridge. This is not a game fix.')
    }
