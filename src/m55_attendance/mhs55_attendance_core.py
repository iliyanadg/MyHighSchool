"""M55 full-roster attendance engine for The Sims 4 school test saves.

Pure deterministic planning: 2/3 classes, eight pupils each, same identities
every day. The roster is frozen at school-session start, not rewritten.
This engine cannot guarantee that EA will instantiate or seat a Sim.
"""
BASE_STUDENT_SITUATION = 277733
BASE_STUDENT_JOB = 277894
CAPACITY_PER_CLASS = 8


class AttendanceError(ValueError):
    pass


def valid_student(info, teen_age, human_species):
    return (info is not None and getattr(info, 'age', None) == teen_age
            and getattr(info, 'species', None) == human_species)


def situation_guid(instance):
    for candidate in (type(instance), getattr(instance, 'situation_type', None), instance):
        if candidate is None:
            continue
        try:
            value = getattr(candidate, 'guid64', None)
            if value is not None:
                return int(value)
        except (ValueError, AttributeError, TypeError):
            pass
    return None


def school_running(manager, all_sims, teen_age):
    """Only run when real EA NPC Base Student school situations are observed."""
    get_for_sim = getattr(manager, 'get_situations_sim_is_in', None)
    if not callable(get_for_sim):
        return False
    for info in all_sims:
        if getattr(info, 'age', None) != teen_age:
            continue
        try:
            getter = getattr(info, 'get_sim_instance', None)
            sim = getter() if callable(getter) else None
            if sim is not None:
                if any(situation_guid(s) == BASE_STUDENT_SITUATION
                       for s in tuple(get_for_sim(sim) or ())):
                    return True
        except Exception:
            continue
    return False


def already_in_base_student(manager, info):
    getter = getattr(manager, 'get_situations_sim_is_in', None)
    if not callable(getter):
        raise AttendanceError('Controllo duplicati EA assente')
    instance_fn = getattr(info, 'get_sim_instance', None)
    try:
        instance = instance_fn() if callable(instance_fn) else None
        return bool(instance is not None and any(
            situation_guid(s) == BASE_STUDENT_SITUATION
            for s in tuple(getter(instance) or ())))
    except Exception:
        raise AttendanceError('Controllo duplicati EA fallito')


def roster_plan(roster, class_count, look_up, teen_age, human_species):
    """Validate every requested pupil and return immutable class/Sim pairs.

    Missing, aged-up, deceased or non-human Sims are never summoned. We don't
    silently generate replacements. The Class 3 registry remains independent
    but EA has no third built-in classroom controller.
    """
    if class_count not in (2, 3):
        raise AttendanceError('Attivare 2 o 3 classi')
    if not callable(look_up):
        raise AttendanceError('Archivio Sims indisponibile')
    planned = []
    invalid = []
    seen = set()
    for klass in range(1, class_count + 1):
        members = roster.class_members(klass)
        if len(members) > CAPACITY_PER_CLASS:
            raise AttendanceError('Superati 8 iscritti in Classe {}'.format(klass))
        for sid in members:
            if sid in seen:
                raise AttendanceError('Studente duplicato nel registro')
            seen.add(sid)
            info = look_up(int(sid))
            if valid_student(info, teen_age, human_species):
                planned.append((klass, sid))
            else:
                invalid.append((klass, sid))
    return tuple(planned), tuple(invalid)


class DailyAttendance(object):
    """State stays in memory, scoped to slot + game day + live zone.

    Mark attempts BEFORE calling EA, so an exception cannot cause a retry
    storm. No daily attendance-history or JSON mutations are introduced.
    """
    def __init__(self, slot, zone_id, day, planned, invalid=()):
        self.slot = str(slot)
        self.zone_id = str(zone_id)
        self.day = int(day)
        self.planned = tuple(planned)
        self.invalid = tuple(invalid)
        self._attempted = set()
        self._outcomes = {}
        self._index = 0

    def same_session(self, slot, zone_id, day):
        return (str(slot), str(zone_id), int(day)) == (
            self.slot, self.zone_id, self.day)

    def next_batch(self, maximum=3):
        if type(maximum) is not int or not 1 <= maximum <= 8:
            raise AttendanceError('Limite batch non valido')
        result = []
        while self._index < len(self.planned) and len(result) < maximum:
            klass, sid = self.planned[self._index]
            self._index += 1
            if sid in self._attempted:
                continue
            self._attempted.add(sid)
            result.append((klass, sid))
        return tuple(result)

    def record(self, sid, result):
        if sid not in self._attempted or result not in (
                'requested', 'present', 'playable', 'missing', 'failed'):
            raise AttendanceError('Esito della convocazione non valido')
        self._outcomes[sid] = result

    @property
    def done(self):
        return self._index >= len(self.planned)

    def summary(self):
        counts = {key: 0 for key in (
            'requested', 'present', 'playable', 'missing', 'failed')}
        for status in self._outcomes.values():
            counts[status] += 1
        counts['pending'] = len(self.planned) - len(self._attempted)
        counts['ineligible'] = len(self.invalid)
        counts['total'] = len(self.planned) + len(self.invalid)
        return counts


def create_student_request(manager, info, situation_tuning, job_tuning,
                           guest_list_type, guest_info_type, purpose):
    """Exactly one EA create_situation call for ONE known, enlisted Sim."""
    if (situation_tuning is None or
            int(getattr(situation_tuning, 'guid64', -1)) != BASE_STUDENT_SITUATION or
            job_tuning is None or
            int(getattr(job_tuning, 'guid64', -1)) != BASE_STUDENT_JOB):
        raise AttendanceError('Risorse EP12 non trovate')
    create = getattr(manager, 'create_situation', None)
    if not callable(create):
        raise AttendanceError('API di convocazione EA non trovata')
    guest_list = guest_list_type(invite_only=True)
    guest = guest_info_type.construct_from_purpose(
        int(info.sim_id), job_tuning, purpose)
    guest_list.add_guest_info(guest)
    result = create(situation_tuning, guest_list=guest_list,
                    user_facing=False, creation_source='MY HIGH SCHOOL M55 roster')
    if not result:
        raise AttendanceError('EA non ha accettato la richiesta')
    return result
