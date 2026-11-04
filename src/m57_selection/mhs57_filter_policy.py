"""M57: safe deterministic EA pre-selection constraints for school situations.

The only EA APIs touched by the runtime adapter are SimFilterService
.submit_filter/.submit_matching_filter, whose documented signatures include
sim_constraints. Do not tune EA resources or alter SimInfo traits/careers.
Numbers are filter tuning GUIDs listed in Zerbu's EP12 presets.

"Strict" here means restricting requested candidates, not guaranteeing EA
chooses or spawns a full 16/24-student school. Core club filters are never
forced without validated role assignments: fallback to vanilla for them.
"""
from mhs57_school_manifest import ManifestError

def is_competing_high_school_mod(file_name):
    """Conservative filename check for known HIGH-SCHOOL selection controllers.

    Do not block on the name of a creator. Sonozaki also publishes unrelated
    Elementary School and Mega Interactions content: those cannot be treated
    as proof that an EP12 high-school selection controller is installed.

    This is a name-based warning, not a definitive package-content scanner.
    Unknown mods may still conflict; only known school-controller names
    trigger the automatic fail-closed guard.
    """
    if not isinstance(file_name, str):
        return False
    lower=file_name.lower()
    if not lower.endswith(('.package', '.ts4script')):
        return False
    base=lower.rsplit('/',1)[-1].rsplit('\\\\',1)[-1]
    normalized=''.join(ch for ch in base if ch.isascii() and ch.isalnum())

    # Translation-only and unrelated mods should not disable EP12 controls.
    # Check the stronger controller marker BEFORE interpreting the creator.
    markers=(
        'highschoolmanagement',
        'choosehighschoolclassmate',
        'chooseyourhighschoolclassmate',
        'highschoolmoreclassmate',
        'highschoolmorestudent',
        'morestudents18',
        'ksuihuhmorestudents',
        'copperdalestories',
        'hsclassmatecontroller',
    )
    if any(marker in normalized for marker in markers):
        if ('traduzione' in normalized or 'translation' in normalized or
                'localization' in normalized) and not (
                'merged' in normalized or 'allinone' in normalized):
            return False
        return True
    # Some old More Students mods ship without author or school in filename.
    # They are known to replace the active school population.
    if normalized.startswith('morestudents') and not (
            'translation' in normalized or 'traduzione' in normalized):
        return True
    return False


STUDENT_FILTER=280516
STAFF_FILTERS={
    296396:'teacher1',
    300741:'teacher2',
    300742:'principal',
    300743:'cafeteria',
    300744:'custodians'
}
CORE_FILTERS=frozenset((276592,276594,276595,276596,303766,280466))
SCHOOL_FILTERS=frozenset((STUDENT_FILTER,)+tuple(STAFF_FILTERS)+tuple(CORE_FILTERS))


def guid_for_filter(tuning):
    if tuning is None:
        return None
    for obj in (tuning, type(tuning)):
        try:
            guid=getattr(obj,'guid64',None)
            if guid is not None:
                return int(guid)
        except (TypeError,ValueError,AttributeError):
            pass
    return None


def choose_constraints(manifest,filter_guid,original_constraints=None,exclude_student_ids=()):
    """(action, filtered_ids) where action=constrain, preserve or bypass.

    For a registered role, exclude IDs from the currently active household,
    since EA should handle actively accompanied teens separately.
    Empty staff appointments never modify EA's existing staffing flow.
    If EA provided specific constraints and they don't intersect, *bypass*
    the override: never override a caller's explicit Sim request.
    """
    guid=int(filter_guid) if filter_guid is not None else None
    if guid==STUDENT_FILTER:
        selected=manifest.to_invite
        role='student'
    elif guid in STAFF_FILTERS:
        role=STAFF_FILTERS[guid]
        selected=frozenset(manifest.staff_ids[role])
    elif guid in CORE_FILTERS:
        return ('preserve',None,'Core team/mean role not assigned in MHS')
    else:
        return ('bypass',None,'Not an EP12 school filter')

    if not selected:
        return ('preserve',None,'No enrolled candidates for '+role)
    selected=set(int(x) for x in selected)
    # M60 trial: prefer enrolled students NOT already instantiated on this zone.
    # Preserve original EA candidates if all are already present, or when EA
    # requested explicit constraints. Never add non-registered students.
    if guid==STUDENT_FILTER and original_constraints is None and exclude_student_ids:
        missing=selected.difference(int(x) for x in exclude_student_ids)
        if missing:
            selected=missing
    if original_constraints is not None:
        try:
            old=set(int(x) for x in original_constraints)
        except (ValueError,TypeError):
            return ('bypass',None,'Unrecognized caller constraints')
        if not old:
            return ('bypass',None,'Caller requested an empty candidate list')
        selected &= old
        if not selected:
            return ('bypass',None,'Caller explicit IDs do not intersect registry')
    return ('constrain',tuple(sorted(selected)),role)


def apply_constraints(args,kwargs,method,manifest,exclude_student_ids=()):
    """Return cloned arguments plus a diagnostic, never change originals.

    submit_matching_filter positional sim_filter index 1, constraints index 4;
    submit_filter positional sim_filter index 0, constraints index 3.
    """
    if method=='matching':
        filter_i,constraints_i=1,4
    elif method=='filter':
        filter_i,constraints_i=0,3
    else:
        raise ManifestError('Unsupported EA filter method')
    copied=list(args)
    options=dict(kwargs)
    tuning=options.get('sim_filter',copied[filter_i] if len(copied)>filter_i else None)
    guid=guid_for_filter(tuning)
    if guid not in SCHOOL_FILTERS:
        return tuple(args),dict(kwargs),('bypass',guid,'Not school filter')
    original=options.get(
        'sim_constraints',copied[constraints_i] if len(copied)>constraints_i else None)
    action, ids, note=choose_constraints(manifest,guid,original,exclude_student_ids)
    if action!='constrain':
        return tuple(args),dict(kwargs),(action,guid,note)
    if len(copied)>constraints_i:
        copied[constraints_i]=ids
    else:
        options['sim_constraints']=ids
    if method=='matching':
        # Disallow EA silently abandoning this exact list to pick a random Sim.
        for key,index in (('continue_if_constraints_fail',8),
                          ('conform_if_constraints_fail',9)):
            if len(copied)>index:
                copied[index]=False
            else:
                options[key]=False
    return tuple(copied),options,('constrain',guid,note)
