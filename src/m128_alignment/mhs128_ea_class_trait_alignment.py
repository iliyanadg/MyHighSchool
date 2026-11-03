"""M128 strict two-class EA Class1 trait alignment.

Original EA tuning: super_HighSchool_Active_AttendClass_NPC 297779
allows Class1 trait 293779 + Class1 whiteboard state 276075, or
absence of Class1 trait + Class2 whiteboard state 276077.
No seating, routing or EA timetable changes are claimed.
"""
CLASS1_TRAIT_ID=293779


def planned_changes(groups,sim_info_manager,trait,age,species):
    """Validate entire roster before proposing any trait mutation."""
    if len(groups)!=2 or any(len(group)!=8 for group in groups):
        raise ValueError('REQUIRES_TWO_GROUPS_OF_EIGHT')
    ids=[str(sid) for group in groups for sid in group]
    if len(set(ids))!=16:
        raise ValueError('DUPLICATE_STUDENT')
    if trait is None:
        raise ValueError('EA_CLASS1_TRAIT_NOT_LOADED')
    rows=[]
    for klass,group in enumerate(groups,1):
        for sid in group:
            info=sim_info_manager.get(int(sid))
            if (info is None or getattr(info,'age',None)!=age
                    or getattr(info,'species',None)!=species):
                raise ValueError('ENROLLED_SIM_MISSING_OR_NOT_HUMAN_TEEN')
            tracker=getattr(info,'trait_tracker',None)
            check=getattr(tracker,'has_trait',None)
            if not callable(check):
                raise ValueError('TRAIT_TRACKER_UNAVAILABLE')
            actual=bool(check(trait))
            expected=klass==1
            rows.append({
                'sim_id':str(sid),'registered_class':klass,
                'ea_class1_trait_present':actual,
                'ea_class1_trait_expected':expected,
                'requires_change':actual!=expected,
                'action':'add' if expected else 'remove',
                'sim_info':info,
                'trait_tracker':tracker,
            })
    return rows


def public_rows(rows):
    return [{key:value for key,value in row.items()
             if key not in ('sim_info','trait_tracker')}
            for row in rows]


def align_roster_trait(rows,trait):
    """Opt-in. Atomic *preflight*, best-effort rollback after exceptions."""
    mismatches=[row for row in rows if row['requires_change']]
    for row in mismatches:
        tracker=row['trait_tracker']
        method=getattr(tracker,'add_trait' if
                       row['ea_class1_trait_expected'] else
                       'remove_trait',None)
        undo=getattr(tracker,'remove_trait' if
                     row['ea_class1_trait_expected'] else
                     'add_trait',None)
        if not callable(method) or not callable(undo):
            return {'success':False,'changed':0,
                    'reason':'TRAIT_MUTATOR_UNAVAILABLE'}
    changed=[]
    try:
        for row in mismatches:
            tracker=row['trait_tracker']
            method=getattr(tracker,'add_trait' if
                           row['ea_class1_trait_expected'] else
                           'remove_trait')
            method(trait)
            if not tracker.has_trait(trait)==row['ea_class1_trait_expected']:
                raise RuntimeError('TRAIT_POSTCHECK_FAILED')
            changed.append(row)
    except Exception as exc:
        rollback_ok=True
        for row in reversed(changed):
            tracker=row['trait_tracker']
            method=getattr(tracker,'remove_trait' if
                           row['ea_class1_trait_expected'] else
                           'add_trait',None)
            try:
                if method is None:
                    raise RuntimeError('NO_REVERSE_METHOD')
                method(trait)
                rollback_ok=rollback_ok and (
                    bool(tracker.has_trait(trait))==
                    row['ea_class1_trait_present'])
            except Exception:
                rollback_ok=False
        return {'success':False,'changed':len(changed),
                'reason':type(exc).__name__,
                'rollback_verified':rollback_ok}
    return {'success':True,'changed':len(changed),
            'reason':'ALIGNED' if mismatches else 'ALREADY_ALIGNED'}
