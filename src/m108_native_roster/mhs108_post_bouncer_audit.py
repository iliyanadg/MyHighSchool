"""M108: read-only *post-Bouncer* native EA SituationJob membership audit.

SOURCE: user-supplied EA originals:
- SituationManager.get(situation_id) (pre_destroy_situation_by_id etc.)
- BaseSituation.all_jobs_gen()
- BaseSituation.all_sims_in_job_gen(job_type)
- BaseSituation.all_sims_in_situation_gen()
- SituationManager.on_all_situations_created_during_zone_spin_up()
  REQUESTS Sim spawning, whereas on_all_sims_spawned_during_zone_spin_up()
  calls bouncer.assign_all_sims_during_zone_spin_up().

NEVER audit a newly returned create_situation ID as if it were a completed
assignment. Caller must provide an independently VERIFIED post-Bouncer phase
barrier (not a boolean guessed from the creation callback). None of this
establishes seating or routing to assigned blackboards.

No game hooks, no Sim spawning, no tuning change. Python 3.7 compatible.
"""
from mhs108_native_invitation import (
    prepare_fixed_manifest, InvitationPlanError,
)
from mhs108_lesson_phase_policy import PHASE_DATA

EA_PHASE_BY_SITUATION = {
    spec[2]: (spec[0], spec[1], spec[3],
              (277918, 278224) if spec[2] == 304567 else
              (277918,) if spec[2] == 297774 else ())
    for spec in PHASE_DATA.values()
}


def _guid(job):
    value = getattr(job, 'guid64', None)
    return value if type(value) is int and value > 0 else None


def _sim_id(sim):
    # Actual EA Sim objects expose .id. Some script contexts also expose
    # .sim_id. Never accept two disagreeing identifiers.
    first = getattr(sim, 'id', None)
    second = getattr(sim, 'sim_id', None)
    value = first if first is not None else second
    if (first is not None and second is not None and first != second):
        return None
    if type(value) is not int or value < 1:
        return None
    return str(value)


def _ids(values):
    if not isinstance(values, (list, tuple, set, frozenset)):
        return None
    result = set()
    for value in values:
        if (type(value) not in (str, int)
                or not str(value).isdigit()
                or str(int(value)) != str(value)
                or int(value) <= 0
                or str(value) in result):
            return None
        result.add(str(value))
    return result


class NativeJobAudit(object):
    """Track native CREATE receipts until a separately-proven assignment.

    Expected jobs are a complete partition of this ONE situation's Sims.
    Do not include all 16 school children in one situation: the player
    phase, Class1 With/NoTrait and Class2 are different EA situations.
    """

    def __init__(self, manifest):
        if (not isinstance(manifest, dict)
                or manifest.get('status') !=
                'M108_INVITATIONS_PREPARED_NOT_GAME_AUTHORIZED'):
            raise ValueError('original complete M108 roster required')
        try:
            canonical = prepare_fixed_manifest(
                manifest['classes'], manifest['playable'],
                dict(manifest['core_assignments']),
                manifest['save_slot'], manifest['sim_day'],
                manifest['school_zone'])
            if any(manifest.get(k) != canonical[k]
                   for k in ('classes','playable','all_16',
                             'core_assignments','base_ids',
                             'save_slot','sim_day','school_zone')):
                raise ValueError('M108 manifest inconsistent')
        except (KeyError, TypeError, ValueError, InvitationPlanError):
            raise ValueError('M108 manifest inconsistent')
        self.manifest = canonical
        self._pending = {}
        self._verified = {}
        self._failed = {}
        self._created_ids = set()
        self._invited_students_by_phase = {}

    def register_created(self, situation_id, situation_type_guid,
                         expected_by_job, phase_key):
        """Receipt from original try_start: CREATED, never ASSIGNED."""
        if (type(situation_id) is not int or situation_id <= 0
                or type(situation_type_guid) is not int
                or situation_type_guid <= 0
                or not isinstance(phase_key, tuple)
                or len(phase_key) != 4
                or situation_id in self._created_ids
                or not isinstance(expected_by_job, dict)
                or not expected_by_job
                or situation_type_guid not in EA_PHASE_BY_SITUATION
                or str(phase_key[0]) != self.manifest['save_slot']
                or type(phase_key[1]) is not int
                or phase_key[1] != self.manifest['sim_day']
                or str(phase_key[2]) != self.manifest['school_zone']
                or phase_key[3] not in ('09:30','10:00','13:30','14:00')):
            return False
        stage, class_index, student_job, staff_jobs = (
            EA_PHASE_BY_SITUATION[situation_type_guid])
        if (stage != ('prepare' if phase_key[3] in ('09:30','13:30')
                      else 'lesson')):
            return False
        if set(expected_by_job) != {student_job} | set(staff_jobs):
            return False
        registered_class = self.manifest['classes'][class_index - 1]
        npc_in_class = set(registered_class) - set(self.manifest['playable'])
        student_ids = _ids(expected_by_job[student_job])
        if student_ids is None or not student_ids <= npc_in_class:
            return False
        if not student_ids:
            # EA need not create a situation with an empty guest list.
            return False
        earlier = self._invited_students_by_phase.get(phase_key, set())
        if student_ids & earlier:
            return False
        copied = {}
        seen = set()
        for job, raw in expected_by_job.items():
            ids = _ids(raw)
            if type(job) is not int or job <= 0 or ids is None:
                return False
            if seen & ids:
                return False
            seen.update(ids)
            copied[job] = frozenset(ids)
        if not seen:
            return False
        # Staff job holders can never be enrolled students/playables.
        school_all = set(self.manifest['all_16'])
        staff_ids = seen - student_ids
        if school_all & staff_ids:
            return False
        self._invited_students_by_phase.setdefault(
            phase_key, set()).update(student_ids)
        self._created_ids.add(situation_id)
        self._pending[situation_id] = {
            'type': situation_type_guid,
            'expected': copied,
            'phase': phase_key,
        }
        return True

    def observe(self, situation_id, situation_manager, barrier):
        """Read EA job assignments only AFTER a trusted Bouncer barrier.

        Return WAITING while assignment is not independently proven.
        Assignment may still be late/changing; verify again for each phase.
        """
        if situation_id in self._verified:
            return self._verified[situation_id]
        if situation_id in self._failed:
            return self._failed[situation_id]
        item = self._pending.get(situation_id)
        if item is None:
            return {'status': 'UNKNOWN_SITUATION'}
        if (not isinstance(barrier, dict)
                or barrier.get('ea_bouncer_assignment_completed') is not True
                or barrier.get('post_bouncer_source_verified') is not True
                or barrier.get('phase_key') != item['phase']
                or barrier.get('situation_id') != situation_id):
            return {
                'status': 'CREATED_AWAITING_BOUNCER',
                'situation_id': situation_id,
                'native_job_assignment_verified': False,
                'seating_verified': False,
            }
        try:
            situation = situation_manager.get(situation_id)
            if situation is None:
                return self._fail(situation_id, 'EA_SITUATION_MISSING')
            situation_guid = _guid(situation)
            if situation_guid != item['type']:
                return self._fail(situation_id, 'WRONG_EA_SITUATION_TYPE')
            jobs = tuple(situation.all_jobs_gen())
            if len(jobs) != len(item['expected']):
                return self._fail(situation_id, 'EA_JOB_LAYOUT_MISMATCH')
            by_guid = {}
            for job in jobs:
                guid = _guid(job)
                if guid is None or guid in by_guid:
                    return self._fail(situation_id, 'EA_JOB_LAYOUT_MISMATCH')
                by_guid[guid] = job
            if set(by_guid) != set(item['expected']):
                return self._fail(situation_id, 'EA_JOB_LAYOUT_MISMATCH')
            observed = {}
            for guid, job in by_guid.items():
                members = tuple(situation.all_sims_in_job_gen(job))
                ids = tuple(_sim_id(sim) for sim in members)
                if None in ids or len(set(ids)) != len(ids):
                    return self._fail(situation_id, 'DUPLICATE_OR_UNKNOWN_SIM')
                observed[guid] = set(ids)
            actual_all = tuple(situation.all_sims_in_situation_gen())
            all_ids = tuple(_sim_id(sim) for sim in actual_all)
            if None in all_ids or len(set(all_ids)) != len(all_ids):
                return self._fail(situation_id, 'DUPLICATE_OR_UNKNOWN_SIM')
            if (set(all_ids) != set().union(*observed.values())
                    or sum(len(v) for v in observed.values()) != len(all_ids)):
                return self._fail(situation_id, 'EA_JOB_MEMBERSHIP_INCONSISTENT')
            if any(observed[job] != target
                   for job, target in item['expected'].items()):
                return self._fail(situation_id, 'WRONG_EA_SIM_OR_JOB')
        except Exception:
            return self._fail(situation_id, 'EA_JOB_READ_FAILED')
        result = {
            'status': 'NATIVE_JOBS_MATCH',
            'situation_id': situation_id,
            'phase_key': item['phase'],
            'native_job_assignment_verified': True,
            'seating_verified': False,
            'actual_ids_by_job': {
                k: tuple(sorted(values))
                for k, values in observed.items()},
        }
        self._verified[situation_id] = result
        del self._pending[situation_id]
        return result

    def _fail(self, situation_id, reason):
        result = {
            'status': reason,
            'situation_id': situation_id,
            'native_job_assignment_verified': False,
            'seating_verified': False,
        }
        self._failed[situation_id] = result
        self._pending.pop(situation_id, None)
        return result

    def snapshot(self):
        return {
            'native_created_awaiting_bouncer': len(self._pending),
            'native_jobs_verified': len(self._verified),
            'native_jobs_rejected': len(self._failed),
            'all_registered_16_seated_verified': False,
            'full_day_attendance_verified': False,
        }
