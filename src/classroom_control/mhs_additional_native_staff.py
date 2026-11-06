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
    if 'cafeteria' not in text or not ('station' in text or 'stall' in text):
        return None
    return key


def count_verified_school_cafeteria_stations(manager):
    """Conservatively count distinct high-school cafeteria station objects.

    Never count menus, Sims, venue props or an untyped food counter. Unknown
    object manager shape yields None (no extra workers created).
    """
    if manager is None:
        return None
    getter = getattr(manager, 'get_all', None)
    if not callable(getter):
        return None
    try:
        objects = tuple(getter())
        if len(objects) > 2000:
            return None
        matched = set()
        for obj in objects:
            ident = _definition_identity(obj)
            object_id = getattr(obj, 'id', None)
            if ident is not None and type(object_id) is int and object_id > 0:
                matched.add(object_id)
        return len(matched)
    except Exception:
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
    for sid in pending:
        if sid not in served and sid not in tried:
            if stations < len(served) + 1:
                return None, 'ADDITIONAL_CAFETERIA_STATION_REQUIRED'
            return {'role': 'cafeteria', 'sim_id': sid,
                    'situation_guid': CAFETERIA_SITUATION,
                    'job_guid': CAFETERIA_JOB}, 'SEPARATE_NATIVE_CAFETERIA_STATION'
    return None, 'NO_ELIGIBLE_MISSING_NATIVE_STAFF'
