"""Guarded supplemental EA school staff, never a parallel school controller.

The original high-school venue and cafeteria situations remain in charge.
An additional *separate* EA situation can be requested once for a selected
missing custodian or for an additional cafeteria station. Successful creation
is not proof of a native job or of actual service; the normal readback must
confirm both. If the situation or the workstation cannot be verified, leave
the running school untouched. Python 3.7 compatible, no EA imports.
"""

VENUE_SITUATION = 298096
CUSTODIAN_JOB = 290196
CAFETERIA_SITUATION = 278011
CAFETERIA_JOB = 278010


def _ident(value):
    if type(value) not in (str, int):
        return None
    result = str(value)
    return result if result.isdigit() and int(result) > 0 and str(int(result)) == result else None


def _minute(clock):
    if not isinstance(clock, dict):
        return None
    h, m = clock.get('hour'), clock.get('minute')
    if type(h) is not int or type(m) is not int or not (0 <= h < 24 and 0 <= m < 60):
        return None
    return h * 60 + m


def supplemental_staff_window(clock):
    """Only at school, after first native staff arrival and before lunch."""
    now = _minute(clock)
    return now is not None and 10 * 60 + 30 <= now < 11 * 60 + 30


def _definition_identity(obj):
    definition = getattr(obj, 'definition', None)
    if definition is None:
        return None
    key = getattr(definition, 'id', None)
    if type(key) is not int or key <= 0:
        return None
    names = []
    for entry in (definition, getattr(obj, 'tuning', None)):
        if entry is None:
            continue
        for field in ('name', '__name__', 'debug_name', 'tuning_file_name'):
            try:
                value = getattr(entry, field, None)
                if isinstance(value, str):
                    names.append(value)
            except Exception:
                pass
    text = ''.join(c.lower() for c in ' '.join(names) if c.isalnum())
    if ('cafeteria' not in text or
            not ('station' in text or 'stall' in text) or
            not ('highschool' in text or 'lunchspecial' in text)):
        return None
    return key


def count_verified_school_cafeteria_stations(manager, native_station=None):
    """Count unique real High School cafeteria counters, without guessing.

    Prefer the real station being tended by EA's existing High School
    TendObjectSituation: its actual object definition identifies matching
    additional stations even if local game tuning names are unavailable.
    Otherwise require recognizable cafeteria station tuning names. Unknown
    manager API or definition cannot authorize additional vendors.
    """
    if manager is None:
        return None
    getter = getattr(manager, 'get_all', None)
    if not callable(getter):
        return None
    try:
        reference=getattr(native_station, 'definition', None)
        reference_id=getattr(reference, 'id', None)
        if type(reference_id) is not int or reference_id <= 0:
            reference_id=None
        objects = tuple(getter())
        if len(objects) > 2000:
            return None
        matched = set()
        for obj in objects:
            ident=_definition_identity(obj)
            definition=getattr(obj,'definition',None)
            defined_id=getattr(definition,'id',None)
            object_id=getattr(obj, 'id', None)
            if type(object_id) is not int or object_id <= 0:
                continue
            if ((reference_id is not None and defined_id==reference_id) or
                    (reference_id is None and ident is not None)):
                matched.add(object_id)
        return len(matched)
    except Exception:
        return None



def native_cafeteria_workstation(situation, manager):
    """Read a real native TendObjectSituation's workstation if exposed.

    Each EA version can choose a different field layout. We only accept an
    object with an actual definition/id, never a guessed tuning/Sim ID.
    """
    if getattr(situation, 'guid64', None) != CAFETERIA_SITUATION:
        return None
    for field in ('get_tend_object','get_target_object','_tend_object',
                  'tend_object','_object_to_tend','_target_object'):
        try:
            value=getattr(situation,field,None)
            if callable(value):
                value=value()
            if type(value) is int and manager is not None:
                getter=getattr(manager,'get',None)
                value=getter(value) if callable(getter) else None
            definition=getattr(value,'definition',None)
            if (type(getattr(definition,'id',None)) is int and
                    type(getattr(value,'id',None)) is int):
                return value
        except Exception:
            continue
    return None


def additional_staff_plan(selected, observed, pending_cafeteria,
                          clock, stations, already_attempted=()):
    """Return the next single exact employee; no random substitution.

    selected/observed map role -> sequence of Sim IDs. observed must come
    from actual EA situation jobs, never guest receipts. All selected IDs
    must have been validated during the existing per-save day preflight.
    A second venue situation has only a janitor guest, not a principal.
    Vendor extras require actual additional counters.
    """
    if not supplemental_staff_window(clock):
        return None, 'OUTSIDE_SUPPLEMENTAL_STAFF_WINDOW'
    if not isinstance(selected, dict) or not isinstance(observed, dict):
        return None, 'NATIVE_STAFF_OBSERVATION_UNAVAILABLE'
    tried = set(str(x) for x in already_attempted)
    janitors = tuple(_ident(x) for x in selected.get('custodians', ()))
    actual = set(_ident(x) for x in observed.get('custodians', ()))
    actual.discard(None)
    if len(janitors) == 2 and None not in janitors and len(set(janitors)) == 2:
        present = tuple(x for x in janitors if x in actual)
        missing = tuple(x for x in janitors if x not in actual)
        if (len(present) == 1 and len(missing) == 1 and
                missing[0] not in tried):
            return {'role': 'custodians', 'sim_id': missing[0],
                    'situation_guid': VENUE_SITUATION,
                    'job_guid': CUSTODIAN_JOB}, 'ONE_SELECTED_CUSTODIAN_MISSING'

    cafeteria = tuple(_ident(x) for x in selected.get('cafeteria', ()))
    pending = tuple(_ident(x) for x in pending_cafeteria)
    served = set(_ident(x) for x in observed.get('cafeteria', ()))
    served.discard(None)
    if (not cafeteria or None in cafeteria or len(set(cafeteria)) != len(cafeteria)
            or None in pending or not set(pending) <= set(cafeteria)):
        return None, 'INVALID_CAFETERIA_SELECTION'
    if cafeteria[0] not in served:
        return None, 'PRIMARY_CAFETERIA_WORKER_NOT_IN_NATIVE_JOB'
    if type(stations) is not int:
        return None, 'CAFETERIA_STATION_COUNT_UNVERIFIED'
    for index,sid in enumerate(pending):
        if sid in served:
            continue
        if any(prior not in served for prior in pending[:index]):
            return None, 'PREVIOUS_EXTRA_CAFETERIA_WORKER_NOT_IN_NATIVE_JOB'
        if sid in tried:
            return None, 'EXTRA_CAFETERIA_NATIVE_JOB_PENDING_READBACK'
        if stations < len(served) + 1:
            return None, 'ADDITIONAL_CAFETERIA_STATION_REQUIRED'
        return {'role': 'cafeteria', 'sim_id': sid,
                'situation_guid': CAFETERIA_SITUATION,
                'job_guid': CAFETERIA_JOB}, 'SEPARATE_NATIVE_CAFETERIA_STATION'
    return None, 'NO_ELIGIBLE_MISSING_NATIVE_STAFF'
