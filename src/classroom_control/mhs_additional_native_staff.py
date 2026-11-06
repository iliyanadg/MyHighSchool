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
# EP12 native tuning: object_marketStalls_CafeteriaStation_HighSchool
# GameObject tuning ID 277994, not the separate OBJD definition ID.
EA_HSY_CAFETERIA_OBJECT_TUNING = 277994
EA_HSY_CAFETERIA_TUNING_NAME = 'object_marketStalls_CafeteriaStation_HighSchool'


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
    """After EA's first staff arrival, before lunch, with job readback.

    The slot-15 report confirmed one custodial native job by 09:30, so
    10:30 was an unnecessary delay for the second selected custodian.
    A request can proceed only when one real staff membership is found.
    """
    now = _minute(clock)
    return now is not None and 9 * 60 + 40 <= now < 11 * 60 + 30


def _definition_identity(obj):
    """Only count genuine cafeteria counter *objects* on this school lot."""
    definition=getattr(obj,'definition',None)
    key=getattr(definition,'id',None)
    if type(key) is not int or key<=0:
        return None
    values=[]
    for entry in (definition,getattr(obj,'tuning',None),obj):
        if entry is None:
            continue
        for field in ('name','__name__','debug_name','tuning_file_name'):
            try:
                v=getattr(entry,field,None)
                if isinstance(v,str):
                    values.append(v)
            except Exception:
                pass
    name=''.join(c.lower() for c in ' '.join(values) if c.isalnum())
    # EA and current HSY custom objects can omit the literal HighSchool
    # prefix from their object definition. The station's object type is
    # enough *inside the verified High School venue*; never count generic
    # food service displays or university-only campus vending props.
    if (('cafeteriastation' in name or
         ('cafeteria' in name and 'counter' in name)) and
            'university' not in name and 'discoveruniversity' not in name):
        return key
    return None


def _ea_hsy_object_tuning_identity(obj):
    """Match the exact EA EP12 cafeteria GameObject tuning (not OBJD).

    TS4 object instances can expose their tuned class via different
    public/native links. Check only bounded known tuning metadata, never
    equate definition.id (OBJD) to the GameObject tuning instance.
    """
    if obj is None:
        return False
    definition=getattr(obj,'definition',None)
    candidates=[obj,type(obj),getattr(obj,'tuning',None),
                getattr(definition,'cls',None),
                getattr(definition,'tuned_class',None)]
    for method in ('get_tuned_class',):
        get=getattr(definition,method,None)
        if callable(get):
            try:
                candidates.append(get())
            except Exception:
                pass
    for source in candidates:
        if source is None:
            continue
        for field in ('guid64','tuning_id','tuning_file_id'):
            try:
                guid=getattr(source,field,None)
                if type(guid) is int and guid==EA_HSY_CAFETERIA_OBJECT_TUNING:
                    return True
            except Exception:
                pass
        for field in ('__name__','name','tuning_file_name'):
            try:
                label=getattr(source,field,None)
                if isinstance(label,str) and (
                        label==EA_HSY_CAFETERIA_TUNING_NAME or
                        label.split('.')[-1]==EA_HSY_CAFETERIA_TUNING_NAME):
                    return True
            except Exception:
                pass
    return False


def _ea_hsy_station_tag_match(obj, tag):
    """True only for the exact tag in EA situation 278011's object filter."""
    if tag is None or obj is None:
        return False
    has=getattr(obj,'has_tag',None)
    if callable(has):
        try:
            return bool(has(tag))
        except Exception:
            pass
    getter=getattr(obj,'get_tags',None)
    if callable(getter):
        try:
            return tag in tuple(getter())
        except Exception:
            pass
    return False


def _school_objects(manager):
    if manager is None:
        return None
    # Sims 4 services.object_manager() commonly exposes values(), whereas
    # SimInfoManager exposes get_all(). Restrict to at most 2000 live objects.
    for method in ('values','get_all'):
        get=getattr(manager,method,None)
        if callable(get):
            try:
                found=tuple(get())
                return found if len(found)<=2000 else None
            except Exception:
                continue
    return None


def school_cafeteria_station_probe(manager,native_station=None,school_tag=None):
    """Bounded evidence for counting and later reading real EA workstations."""
    items=_school_objects(manager)
    if items is None:
        return {'count':None,'reason':'OBJECT_MANAGER_UNSUPPORTED'}
    reference=getattr(native_station,'definition',None)
    reference_id=getattr(reference,'id',None)
    if type(reference_id) is not int or reference_id<=0:
        reference_id=None
    ids=set()
    definitions=set()
    matched_ea=set()
    matched_tag=set()
    for obj in items:
        oid=getattr(obj,'id',None)
        did=getattr(getattr(obj,'definition',None),'id',None)
        if type(oid) is not int or oid<=0:
            continue
        # Prioritize exact verified EA EP12 tuning over a display name.
        ea_tuning=_ea_hsy_object_tuning_identity(obj)
        ea_tag=_ea_hsy_station_tag_match(obj,school_tag)
        named=_definition_identity(obj)
        if ea_tuning:
            matched_ea.add(oid)
        if ea_tag:
            matched_tag.add(oid)
        if (ea_tuning or ea_tag or
                (reference_id is not None and did==reference_id) or
                (reference_id is None and named is not None)):
            ids.add(oid)
            if type(did) is int:
                definitions.add(did)
    return {'count':len(ids),
            'reason':('EA_NATIVE_STATION_TAG_MATCH'
                      if matched_tag else 'EA_HSY_TUNING_277994_MATCH'
                      if matched_ea else 'NATIVE_STATION_DEFINITION_MATCH'
                      if reference_id is not None else
                      'NAMED_CAFETERIA_STATIONS_MATCHED' if ids else
                      'NO_RECOGNIZED_STATIONS'),
            'ea_hsy_tuning_id':EA_HSY_CAFETERIA_OBJECT_TUNING,
            'ea_hsy_objects_found':len(matched_ea),
            'native_tagged_stations_found':len(matched_tag),
            'native_tag_available':school_tag is not None,
            'object_manager_count':len(items),
            'matched_definition_ids':sorted(definitions)[:8]}


def count_verified_school_cafeteria_stations(manager,native_station=None,
                                            school_tag=None):
    return school_cafeteria_station_probe(
        manager,native_station,school_tag)['count']



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
    Missing original EA principal, second teacher and second janitor are
    requested only in their ALREADY RUNNING native situations. Never create
    a duplicate Core/Venue situation, which could recruit extra students or
    overwrite correctly employed staff. Vendor extras require real counters.
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

    # Exact recovery requests stay within an existing EA school situation:
    # the first teacher/one janitor must be observed in the corresponding
    # original job, proving the situation has started. We never infer
    # employment from an invitation receipt or a newly created situation.
    for role, companion, situation_guid, job_guid in (
            ('principal', 'custodians', VENUE_SITUATION, 278223),
            ('teacher2', 'teacher1', 298052, 278963)):
        ids = tuple(_ident(x) for x in selected.get(role, ()))
        working = set(_ident(x) for x in observed.get(role, ()))
        working.discard(None)
        witnesses = set(_ident(x) for x in observed.get(companion, ()))
        witnesses.discard(None)
        if (len(ids) == 1 and ids[0] is not None and
                ids[0] not in working and ids[0] not in tried and
                witnesses):
            return {'role': role, 'sim_id': ids[0],
                    'situation_guid': situation_guid,
                    'job_guid': job_guid}, (
                        'SELECTED_' + role.upper() + '_MISSING_IN_NATIVE_JOB')

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
