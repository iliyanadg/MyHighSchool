"""M106 post-game evidence: why the exact manually chosen 16 cannot be used.

The real user save exposed an error our synthetic tests missed:
12 of 13 registered NPCs passed EA Base, but the non-Base teenager
may not pass ANY EA Core filter. The earlier pilot only bridged a Core
role through the original EA Base filter, which CANNOT fix that case.

This module never authorizes a filter bypass. It reports exactly which
of the FIVE USER-CHOSEN role holders and EIGHT remaining students need
an independently verified school-specific selection mechanism.
No automatic reallocation of the user's role preferences is permitted.
"""
from mhs105_atomic_school_roster import BASE_JOB,CORE_JOBS,ALL_JOBS

CORE_ORDER=tuple(CORE_JOBS)


def _ids(items):
    if type(items) not in (tuple,list,set,frozenset):
        return None
    result=[]
    for raw in items:
        if type(raw) not in (int,str) or not str(raw).isdigit() or int(raw)<1:
            return None
        result.append(str(int(raw)))
    return tuple(result)


def _blocked(reason):
    return {'status':'INVALID_ROSTER_AUDIT','reason':reason,
            'roster_changed':False,'roles_changed':False,
            'traits_changed':False,'filter_overrides_authorized':False,
            'attendance_verified':False}


def audit_fixed_roster(classes,playable,preferred_roles,eligible):
    """Inspect all SIX scored original filters; no native filter is replaced.

    Unlike the experimental M106 optimizer, the actual manually assigned
    Core role holders are IMMUTABLE. This accounts for each of the 13 NPCs.
    """
    if (type(classes) not in (tuple,list) or len(classes)!=2
            or any(type(group) not in (tuple,list) or len(group)!=8
                   for group in classes)):
        return _blocked('expected exactly two classes with eight enrolled')
    groups=tuple(_ids(group) for group in classes)
    if None in groups:
        return _blocked('invalid enrolled ID')
    every=groups[0]+groups[1]
    if len(set(every))!=16:
        return _blocked('duplicate enrolled student')
    played=_ids(playable)
    if played is None or len(played)!=3 or len(set(played))!=3:
        return _blocked('expected three different playable teens')
    if not set(played)<=set(every):
        return _blocked('playable teen not enrolled')
    ordinary=tuple(sid for sid in every if sid not in set(played))
    if len(ordinary)!=13:
        return _blocked('expected thirteen enrolled NPC teens')
    if (type(preferred_roles) is not dict
            or set(preferred_roles)!=set(CORE_ORDER)):
        return _blocked('five confirmed EA school role IDs required')
    roles={}
    for job in CORE_ORDER:
        sim=_ids((preferred_roles[job],))
        if sim is None:
            return _blocked('invalid chosen role holder')
        roles[job]=sim[0]
    chosen=tuple(roles[job] for job in CORE_ORDER)
    if len(set(chosen))!=5 or not set(chosen)<=set(ordinary):
        return _blocked('special roles must reference five different enrolled NPCs')
    base_members=tuple(sid for sid in ordinary if sid not in set(chosen))
    if len(base_members)!=8:
        return _blocked('base cohort must contain exactly eight registered NPCs')
    if type(eligible) is not dict or set(eligible)!=set(ALL_JOBS):
        return _blocked('all six measured original EA filter sets required')
    checked={}
    for job in ALL_JOBS:
        vals=_ids(eligible[job])
        if vals is None:
            return _blocked('EA filter result not verifiably scored')
        checked[job]=frozenset(vals)

    core_rejected=tuple((job,roles[job]) for job in CORE_ORDER
                        if roles[job] not in checked[job])
    base_rejected=tuple(sid for sid in base_members
                        if sid not in checked[BASE_JOB])
    base_all=tuple(sid for sid in ordinary
                   if sid not in checked[BASE_JOB])
    no_original_filter=tuple(sid for sid in ordinary
                             if all(sid not in checked[job] for job in ALL_JOBS))
    core_can_use_existing_base=tuple((job,sid) for job,sid in core_rejected
                                     if sid in checked[BASE_JOB])
    core_without_existing_base=tuple((job,sid) for job,sid in core_rejected
                                     if sid not in checked[BASE_JOB])

    # An alternative school-only filter must be tested on real EA API and
    # all registered teens; the audit cannot grant it by fiat.
    return {
        'status':('FIXED_16_ORIGINAL_FILTERS_MATCH_NOT_EA_BOUND'
                  if not core_rejected and not base_rejected else
                  'FIXED_16_REQUIRES_UNVERIFIED_SCHOOL_SELECTION'),
        'classes':groups,'all_16':every,
        'playable':played,
        'original_assigned_core':tuple((job,roles[job])
                                       for job in CORE_ORDER),
        'remaining_original_base':base_members,
        'registered_npc_base_filter_rejected':base_all,
        'assigned_core_filter_rejected':core_rejected,
        'remaining_base_filter_rejected':base_rejected,
        'no_original_ea_student_filter':no_original_filter,
        'core_rejected_but_original_base_eligible':core_can_use_existing_base,
        'core_rejected_and_original_base_ineligible':core_without_existing_base,
        'enrolled':16,'playable_count':3,'core_count':5,'base_count':8,
        'roster_changed':False,'roles_changed':False,
        'traits_changed':False,'filter_overrides_authorized':False,
        'ea_job_binding_verified':False,'attendance_verified':False,
        'next_step':('Verify an independent school-only native SimFilter '
                     'for any of the specifically rejected enrolled teens; '
                     'do NOT enroll outside NPCs, alter traits, reallocate '
                     'manual roles, or bypass EA eligibility unverified.')
    }


def summary(audit,label=None):
    """Readable blocked report without exposing the whole save."""
    if not isinstance(audit,dict):
        return 'M106: audit non disponibile'
    if audit.get('status')=='INVALID_ROSTER_AUDIT':
        return 'M106 audit bloccata: '+audit['reason']
    if label is None:
        label=lambda sid: 'ID '+str(sid)
    core=audit['assigned_core_filter_rejected']
    base=audit['remaining_base_filter_rejected']
    excluded=audit['no_original_ea_student_filter']
    if not core and not base:
        return ('M106: 5 ruoli + 8 Base originali idonei; '
                'convocazione e presenze NON verificate')
    result=['M106: blocco riconosciuto, tutti i 16 iscritti restano fissi.',
            'Ruoli speciali scelti non idonei al filtro EA: {}'.format(
                len(core)),
            'Studenti degli 8 Base esclusi dal filtro EA: {}'.format(
                len(base))]
    if base:
        result.append('Base esclusi: '+', '.join(label(sid) for sid in base))
    if excluded:
        result.append('Senza filtro EA scolastico idoneo: '+
                      ', '.join(label(sid) for sid in excluded))
    result.append('Servira un filtro autonomo per la scuola, NON una sostituzione di Sim.')
    return tuple(result)
