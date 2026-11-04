"""Read school admission, preparation, lesson and staffing without mutations.

Keep this separate from the attendance policy. An observed job, interaction
or nearby chair is evidence, never a command or a completion certificate.
"""
from itertools import islice

from mhs148_day_trace import observe_student
from mhs_queue_readback import queue_snapshot

SCHOOL_SITUATIONS = frozenset((277733, 298052, 298096, 278011,
                              293815, 304701, 297774, 304565, 304703, 304567))
# Only the long-lived EA Core/Venue/Vendor situation jobs establish
# the stable personnel roles that the M53 register can appoint.
# A lesson-phase "Teacher1" job is not proof of the MHS Classe 1 teacher:
# EA may reuse both base teachers in an unrelated phase.
STAFF_JOBS = {
    (298052,277895): 'teacher1',
    (298052,278963): 'teacher2',
    (298096,278223): 'principal',
    (298096,290196): 'custodians',
    (278011,278010): 'cafeteria',
}
PHASE_TEACHER_JOBS = frozenset((277918,297170,278224))
KNOWN_STAFF_TRAITS = {'teacher1': 300380, 'principal': 300487,
                      'custodians': 300488, 'cafeteria': 300519}


def _guid(value):
    for obj in (value, getattr(value, 'tuned_class', None), type(value)):
        result = getattr(obj, 'guid64', None)
        if type(result) is int and result > 0:
            return result
    return None


def _name(info):
    return ('{} {}'.format(getattr(info, 'first_name', ''),
                           getattr(info, 'last_name', '')).strip())[:160]


def school_memberships(sim, manager):
    """Same verified EA read API used by M124/M134; include prep and Core."""
    if sim is None:
        return {'available': False, 'reason': 'NOT_INSTANCED', 'jobs': []}
    reader = getattr(manager, 'get_situations_sim_is_in', None)
    if not callable(reader):
        return {'available': False, 'reason': 'MEMBERSHIP_API_UNAVAILABLE', 'jobs': []}
    rows = []
    try:
        situations = tuple(islice(iter(reader(sim)), 65))
        if len(situations) > 64:
            raise ValueError('MEMBERSHIP_LIMIT')
        for situation in situations:
            sid = _guid(situation)
            if sid not in SCHOOL_SITUATIONS:
                continue
            job_reader = getattr(situation, 'get_current_job_for_sim', None)
            role_reader = getattr(situation, 'get_current_role_state_for_sim', None)
            if not callable(job_reader):
                raise ValueError('JOB_API_UNAVAILABLE')
            job = _guid(job_reader(sim))
            role = _guid(role_reader(sim)) if callable(role_reader) else None
            rows.append({'situation_guid': sid, 'job_guid': job,
                         'role_guid': role,
                         'staff_role': STAFF_JOBS.get((sid,job)),
                         'phase_teacher_job': (
                             job if sid not in (298052,298096,278011)
                             and job in PHASE_TEACHER_JOBS else None)})
            if job is None:
                raise ValueError('NATIVE_JOB_NOT_EXPOSED')
        return {'available': True, 'reason': 'EA_SCHOOL_MEMBERSHIPS_READ', 'jobs': rows}
    except Exception as exc:
        return {'available': False, 'reason': 'READ_' + type(exc).__name__, 'jobs': rows}


def entry_window(clock):
    hour, minute = clock.get('hour'), clock.get('minute')
    if type(hour) is not int or type(minute) is not int or not 0 <= minute < 60:
        return None
    total = hour * 60 + minute
    if 570 <= total <= 630:
        return 'morning'
    if 810 <= total <= 870:
        return 'afternoon'
    return None


def staff_sample_period(clock):
    """At most five expensive all-Sim staff reads per school day.

    Match actual phase *observations*, not scheduled staff arrivals.
    The monitor reads the full school journal separately every 15 minutes;
    this function avoids repeating a world-wide scan on every sample.
    """
    if not isinstance(clock,dict):
        return None
    hour,minute=clock.get('hour'),clock.get('minute')
    if (type(hour) is not int or type(minute) is not int
            or not 0<=hour<=23 or not 0<=minute<60):
        return None
    total=hour*60+minute
    if 480<=total<570:
        return 'arrival'
    if 570<=total<660:
        return 'morning_lesson'
    if 660<=total<840:
        return 'lunch_and_preparation'
    if 840<=total<900:
        return 'afternoon_lesson'
    if 900<=total<=960:
        return 'school_end'
    return None


def entry_snapshot(clock, groups, info_manager, situation_manager, class_trait):
    rows = []
    for klass, group in enumerate(groups, 1):
        for sid in group:
            info = info_manager.get(int(sid))
            row = observe_student(info, klass)
            row['sim_id'] = str(sid)
            row['name'] = _name(info)
            try:
                sim = info.get_sim_instance() if info is not None else None
                row['native_school_memberships'] = school_memberships(sim, situation_manager)
                tracker = getattr(info, 'trait_tracker', None)
                row['ea_class1_trait_present'] = (bool(tracker.has_trait(class_trait))
                    if tracker is not None and class_trait is not None else None)
                queue = queue_snapshot(sim)
                row['queue_details_available'] = queue['available']
                row['queue_read_reason'] = queue['reason']
                row['queued_actions'] = queue['queued_names']
                row['running_parent_actions'] = queue['active_parent_names']
            except Exception as exc:
                row['observation_error'] = type(exc).__name__
            rows.append(row)
    return {'clock': clock, 'period': entry_window(clock), 'students': rows,
            'world_mutations': 0, 'routing_progress_not_observed': True}


def staff_snapshot(roster, info_manager, situation_manager, trait_manager):
    """Compare the saved choices with actual native jobs; never appoint staff.

    get_all is already used by the staff picker. Stop at a bounded count and
    mark partial reads explicitly; absence in partial data proves nothing.
    """
    expected = {key: list(roster.members(key)) for key in roster.roles}
    result = {'expected': expected, 'selected_sims': [], 'observed_staff': [],
              'complete': True, 'errors': [], 'world_mutations': 0,
              'selection_bridge_implemented': False,
              'registry_is_not_native_assignment': True,
              'native_staff_job_capacity_not_inferred_from_registry': True}
    for sid in sorted(roster.all_ids()):
        info = info_manager.get(int(sid))
        row = {'sim_id': sid, 'name': _name(info), 'known_role_traits': {}}
        try:
            sim = info.get_sim_instance() if info is not None else None
            row['sim_present'] = sim is not None
            row['native_school_memberships'] = school_memberships(sim, situation_manager)
            for role, trait_id in KNOWN_STAFF_TRAITS.items():
                trait = trait_manager.get(trait_id) if trait_manager is not None else None
                tracker = getattr(info, 'trait_tracker', None)
                row['known_role_traits'][role] = (bool(tracker.has_trait(trait))
                    if tracker is not None and trait is not None else None)
        except Exception as exc:
            row['observation_error'] = type(exc).__name__
            result['complete'] = False
        result['selected_sims'].append(row)
    try:
        infos = tuple(islice(iter(info_manager.get_all()), 4097))
        if len(infos) > 4096:
            result['complete'] = False
            result['errors'].append('SIM_INFO_LIMIT')
        for info in infos[:4096]:
            sim = info.get_sim_instance()
            if sim is None:
                continue
            memberships = school_memberships(sim, situation_manager)
            if not memberships['available']:
                result['complete'] = False
            jobs = [job for job in memberships['jobs'] if job['staff_role'] is not None]
            if jobs:
                result['observed_staff'].append({'sim_id': str(info.sim_id),
                    'name': _name(info), 'jobs': jobs})
    except Exception as exc:
        result['complete'] = False
        result['errors'].append('STAFF_READ_' + type(exc).__name__)
    comparison = {}
    for role, wanted in expected.items():
        actual = sorted({row['sim_id'] for row in result['observed_staff']
                         if any(job['staff_role'] == role for job in row['jobs'])})
        comparison[role] = {'expected': wanted, 'observed': actual,
                            'matches': (set(wanted) == set(actual)
                                        if result['complete'] else None)}
    result['comparison'] = comparison
    return result
