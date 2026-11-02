"""M108 ONE school-only EA WeeklyScheduleSituationData.try_start hook.

OFFLINE EXPERIMENT ONLY: never imported by an installable TS4 script.
This merges M108 Class1 WithTrait/NoTrait and Class2 Others under ONE native
classmethod wrapper. No independent Class1/Other hook may coexist with it.

Actual EA job receipt (job -> assigned SimIDs) MUST be read *after* creation
from the original situation manager by a verified external provider. The
method's return ID and removed Sim set are NOT sufficient evidence of job
identity. Without a matching receipt the adapter does not confirm success
and does not remove Sims from the caller's original set. A real EA situation
might nevertheless have been created; we return its ID to avoid retrying.

The Class1 shadow class has NOT been validated with the EA hashed metaclass.
All live proof gates below are UNPROVEN. No saved-game modifications here.
"""
from mhs108_lesson_phase_policy import (
    PHASE_DATA, propose_phase_students,
)
from mhs108_class1_dual_route_budget import ClassOneDualRouteBudget
from mhs108_class1_shadow_cap import project_class1_tuning
from mhs108_class1_try_start_bridge import (
    EA_CLASS1_DATA_GUIDS, _native_modifier_counts, _verified_context,
)

CLASS_TWO = frozenset((297773, 304570))
CLASS_TWO_JOB_LAYOUT = {
    297773: (277919, 277918),
    304570: (280777, 277918, 278224),
}
REQUIRED_LIVE_GATES = (
    'original_weekly_ea_try_start_verified',
    'full_16_school_day_ea_membership_verified',
    'one_wrapper_no_legacy_stack_verified',
    'class1_shadow_native_metaclass_verified',
    'class1_native_two_route_eligibility_verified',
    'class2_exact_staff_job_mapping_verified',
    'native_post_creation_job_receipt_verified',
    'no_random_phase_fallback_verified',
    'npc_lot_capacity_verified',
)


def _guid(value):
    v = getattr(value, 'guid64', None)
    return v if type(v) is int and v > 0 else None


def _sid(sim):
    v = getattr(sim, 'sim_id', None)
    return str(v) if type(v) is int and v > 0 else None


def _ids(values):
    if not isinstance(values, (tuple, list, set, frozenset)):
        return None
    result = set()
    for v in values:
        if type(v) not in (int, str) or not str(v).isdigit() or int(v) <= 0:
            return None
        s = str(int(v))
        if s != str(v) or s in result:
            return None
        result.add(s)
    return result


def _receipt_valid(proof, situation_id, expected_job_ids):
    """Post-create witness: match exact EA situation+job IDs, no extras."""
    if not isinstance(proof, dict):
        return False
    if (proof.get('native_ea_guest_list_inspected') is not True
            or proof.get('situation_id') != situation_id
            or type(situation_id) is not int or situation_id <= 0):
        return False
    received = proof.get('ids_by_job')
    if not isinstance(received, dict) or set(received) != set(expected_job_ids):
        return False
    for job, expected in expected_job_ids.items():
        ids = _ids(received[job])
        if ids is None or ids != set(expected):
            return False
    # Every child and staff ID in the one EA situation is unique.
    all_groups = [str(value) for group in received.values()
                  for value in group]
    return len(all_groups) == len(set(all_groups))


def _staff_for_native_jobs(cls, manifest, context, data_guid):
    """Never select teacher/principal with only a generic staff whitelist."""
    if (context.get('verified_staff_jobs') is not True
            or context.get('native_job_layout_verified') is not True):
        return None
    expected_layout = CLASS_TWO_JOB_LAYOUT.get(data_guid)
    if expected_layout is None:
        return None
    try:
        actual_layout = tuple(_guid(e.job) for e in cls.job_assignments)
        if actual_layout != expected_layout:
            return None
        staff_by_job = context.get('verified_staff_by_job')
        if not isinstance(staff_by_job, dict):
            return None
        staff_jobs = expected_layout[1:]
        if set(staff_by_job) != set(staff_jobs):
            return None
        all_ids = set(manifest['all_16'])
        staff_ids = set()
        for job in staff_jobs:
            ids = _ids(staff_by_job[job])
            if ids is None or not ids:
                return None
            if job == 277918 and len(ids) > 2:
                return None
            if job == 278224 and len(ids) != 1:
                return None
            if staff_ids & ids or all_ids & ids:
                return None
            staff_ids.update(ids)
        observed = _ids(context.get('observed_on_lot'))
        if observed is None or not staff_ids <= observed:
            return None
        return {job: _ids(staff_by_job[job]) for job in staff_jobs}
    except (AttributeError, ValueError, TypeError):
        return None


def install_offline_only(weekly_data_class, manifest, context_provider,
                         class1_budget_provider, post_ea_receipt_provider,
                         live_proofs):
    """Single original EA hook, both registered classrooms, no global tuning."""
    if (not callable(context_provider)
            or not callable(class1_budget_provider)
            or not callable(post_ea_receipt_provider)
            or not isinstance(live_proofs, dict)
            or any(live_proofs.get(gate) is not True
                   for gate in REQUIRED_LIVE_GATES)):
        return None
    owner = None
    for cls in getattr(weekly_data_class, '__mro__', (weekly_data_class,)):
        d = cls.__dict__.get('try_start')
        if isinstance(d, classmethod):
            owner = cls
            break
    if owner is None:
        return None
    previous_descriptor = owner.__dict__['try_start']
    original = previous_descriptor.__func__
    if any(getattr(original, flag, False) for flag in (
            '_mhs108_exact_phase', '_mhs108_class1_bridge',
            '_mhs108_unified_lessons')):
        return None
    # A cloned dict is not enough to protect a caller from mutating it;
    # validate against immutable canonical roster on every phase proposal.
    blocked_receipts = []

    def wrapped(cls, sims, sim_info, duration,
                additional_sim_ids, situation_job_count):
        guid = _guid(cls)
        if guid not in PHASE_DATA:
            return original(cls, sims, sim_info, duration,
                            additional_sim_ids, situation_job_count)
        try:
            context = context_provider(cls)
            if (not isinstance(context, dict)
                    or context.get('mhs_unified_school_active') is not True):
                return original(cls, sims, sim_info, duration,
                                additional_sim_ids, situation_job_count)

            spec = PHASE_DATA[guid]
            if _guid(cls.situation) != spec[2]:
                return None
            if (not isinstance(cls.job_assignments, (tuple, list))
                    or not cls.job_assignments
                    or _guid(cls.job_assignments[0].job) != spec[3]):
                return None

            if guid in EA_CLASS1_DATA_GUIDS:
                coordinator = class1_budget_provider(cls, context)
                if not _verified_context(
                        coordinator,
                        dict(context, mhs_class1_dual_route_active=True), guid):
                    return None
                counts = _native_modifier_counts(cls, situation_job_count)
                if counts is None:
                    return None
                ticket_context = dict(
                    context,
                    ea_job_counts_verified=True,
                    ea_route_test_results_verified=(
                        context.get('ea_route_test_results_verified')),
                    native_school_phase_origin_verified=(
                        context.get('native_school_phase_origin_verified')),
                )
                ticket = coordinator.prepare(
                    guid, counts, context.get('verified_native_eligible_ids'),
                    ticket_context)
                if ticket is None:
                    return None
                expected_students = set(ticket['exact_candidate_ids'])
                if not expected_students:
                    if not coordinator.confirm(ticket, (), None):
                        coordinator.cancel(ticket)
                    return None
                projection = project_class1_tuning(cls, ticket)
                if projection is None:
                    coordinator.cancel(ticket)
                    return None
                expected_jobs = {spec[3]: expected_students}
                allowed = expected_students
            else:
                coordinator = None
                ticket = None
                projection = cls
                phase_result = propose_phase_students(
                    manifest, guid, spec[2], spec[3], context,
                    context.get('observed_on_lot'),
                    context.get('observed_ea_school_members'),
                    context.get('verified_native_eligible_ids'))
                if phase_result.get('status') != 'PROPOSED_NOT_EA_ASSIGNED':
                    return None
                expected_students = set(phase_result['exact_npc_ids'])
                staff = _staff_for_native_jobs(cls, manifest, context, guid)
                if staff is None:
                    return None
                expected_jobs = {spec[3]: expected_students}
                expected_jobs.update(staff)
                allowed = set().union(*expected_jobs.values())

            restricted = set(sim for sim in sims if _sid(sim) in allowed)
            if (len(restricted) != len(allowed)
                    or set(_sid(sim) for sim in restricted) != allowed):
                if coordinator is not None:
                    coordinator.cancel(ticket)
                return None
            before = restricted.copy()
        except Exception:
            return None

        try:
            # Exactly ONE native EA call; it may create side effects.
            situation_id = original(
                projection, restricted, sim_info, duration,
                additional_sim_ids, situation_job_count)
        except Exception:
            if coordinator is not None:
                coordinator.cancel(ticket)
            raise

        if situation_id is None:
            if coordinator is not None:
                coordinator.cancel(ticket)
            return None

        # The EA original may have assigned the wrong job or a partial set.
        # Inspect its *actual* guest list: simply checking set difference
        # cannot distinguish a student from a principal/teacher assignment.
        try:
            proof = post_ea_receipt_provider(cls, situation_id, context)
            native_ok = _receipt_valid(proof, situation_id, expected_jobs)
            removed = before.difference(restricted)
            native_ok = (native_ok
                         and set(_sid(s) for s in removed) == allowed
                         and len(removed) == len(allowed))
            if coordinator is not None and native_ok:
                key = (cls.situation, cls.job_assignments[0].job)
                actual_count = situation_job_count.get(key, 0)
                expected_stage_count = (
                    context.get('expected_native_class1_job_count_after'))
                # The request's original EA student-job total must match
                # what the post-create observer independently recorded.
                native_ok = (
                    type(actual_count) is int
                    and type(expected_stage_count) is int
                    and actual_count == expected_stage_count)
            if native_ok and coordinator is not None:
                native_ok = coordinator.confirm(
                    ticket, expected_students, situation_id)
            if native_ok:
                sims.difference_update(removed)
            else:
                if coordinator is not None:
                    coordinator.cancel(ticket)
                blocked_receipts.append((guid, situation_id))
        except Exception:
            if coordinator is not None:
                coordinator.cancel(ticket)
            blocked_receipts.append((guid, situation_id))
        # Return the EA result even if a wrong assignment already occurred.
        # Retrying it would be unsafe. No unsupported promise of rollback.
        return situation_id

    wrapped._mhs108_unified_lessons = True
    owner.try_start = classmethod(wrapped)

    def uninstall():
        current = owner.__dict__.get('try_start')
        if not isinstance(current, classmethod) or current.__func__ is not wrapped:
            return False
        owner.try_start = previous_descriptor
        return True

    uninstall.blocked_receipts = blocked_receipts
    return uninstall
