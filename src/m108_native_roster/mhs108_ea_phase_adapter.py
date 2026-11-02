"""M108 disabled native WeeklyScheduleSituationData.try_start adapter.

This method was read from the user's decompiled EA original on 2026-11-02:
WeeklyScheduleSituationData.try_start(
    cls, sims, sim_info, duration, additional_sim_ids, situation_job_count)
checks minimum-required jobs first and optional jobs second PER Sim in the mutable 'sims' set, then creates a native EA
situation with its actual matched guest list, and upon successful creation
runs sims.difference_update(assigned_sims).

This opt-in adapter narrows only the *temporary* candidate set for the
verified MHS school phase, then propagates EA's successful removal back
to the SAME original shared set. No fake Sim spawn, lesson time override,
hidden trait manipulation or alternate situation creation.

UNRELEASED: all live runtime proof flags remain unavailable. Do not call
install_offline_only from any game entrypoint.
"""
from mhs108_lesson_phase_policy import (
    PHASE_DATA, WINDOWS, propose_phase_students,
)

REQUIRED_LIVE_GATES = (
    'original_weekly_schedule_try_start_verified',
    'school_schedule_phase_call_provenance_verified',
    'exact_ea_school_student_membership_verified',
    'phase_native_eligibility_test_results_verified',
    'original_tuned_phase_capacity_compatible',
    'class_one_trait_variants_coordinated',
    'verified_teacher_and_principal_ids_available',
    'no_random_extra_student_fallback_verified',
)


def _guid(obj):
    value = getattr(obj, 'guid64', None)
    return value if type(value) is int and value > 0 else None


def _sim_id(sim):
    value = getattr(sim, 'sim_id', None)
    if type(value) is int and value > 0:
        return str(value)
    return None


def _origin_checked_for_exact_phase(cls, spec):
    try:
        expected_situation, expected_job = spec[2], spec[3]
        if _guid(cls.situation) != expected_situation:
            return False
        jobs = cls.job_assignments
        if (not isinstance(jobs, (tuple, list))
                or not jobs or _guid(jobs[0].job) != expected_job):
            return False
        return True
    except (AttributeError, IndexError, TypeError):
        return False


def install_offline_only(weekly_situation_data_class, manifest,
                         context_provider, live_proofs):
    """Wrap the ORIGINAL EA classmethod, or return None without patching.

    The provider must return authoritative zone/day/school facts and
    real on-lot/EA membership, original phase eligibility results,
    plus exact selected teacher/principal IDs for multi-job situations.
    Synthetic flags in tests prove only adapter logic.
    """
    if (not callable(context_provider)
            or not isinstance(live_proofs, dict)
            or any(live_proofs.get(key) is not True
                   for key in REQUIRED_LIVE_GATES)):
        return None
    owner = None
    for parent in getattr(weekly_situation_data_class, '__mro__',
                          (weekly_situation_data_class,)):
        descriptor = getattr(parent, '__dict__', {}).get('try_start')
        if isinstance(descriptor, classmethod):
            owner = parent
            break
    if owner is None:
        return None
    prior = owner.__dict__['try_start']
    original = prior.__func__
    if getattr(original, '_mhs108_exact_phase', False):
        return None

    def wrapped(cls, sims, sim_info, duration, additional_sim_ids,
                situation_job_count):
        guid = _guid(cls)
        spec = PHASE_DATA.get(guid)
        if spec is None:
            return original(cls, sims, sim_info, duration,
                            additional_sim_ids, situation_job_count)
        try:
            context = context_provider(cls)
            if (not isinstance(context, dict)
                    or context.get('mhs_lesson_router_active') is not True):
                # Inactive or unrelated requests keep the EA game intact.
                return original(cls, sims, sim_info, duration,
                                additional_sim_ids, situation_job_count)
            if not _origin_checked_for_exact_phase(cls, spec):
                # Active but inconsistent school tuning must NOT assign
                # unregistered students using a guessed phase mapping.
                return None
            staff_ids = context.get('verified_staff_ids')
            if (context.get('verified_staff_roles') is not True
                    or not isinstance(staff_ids, (tuple, list, set, frozenset))
                    or any(type(x) not in (int, str)
                           or not str(x).isdigit() or int(x) <= 0
                           for x in staff_ids)):
                return None
            staff_ids = set(str(int(x)) for x in staff_ids)
            if (staff_ids & set(manifest['all_16'])
                    or (spec[1] == 2 and not staff_ids)):
                return None
            report = propose_phase_students(
                manifest, guid, spec[2], spec[3], context,
                context.get('observed_on_lot'),
                context.get('observed_ea_school_members'),
                context.get('verified_native_eligible_ids'))
            if report.get('status') != 'PROPOSED_NOT_EA_ASSIGNED':
                # Fail closed for a recognized active MHS phase.
                return None
            # Class1 phase data contains student jobs only. Never pass
            # teachers/principal into a Class1-only situation.
            allowed = set(report['exact_npc_ids'])
            if spec[1] == 2:
                allowed.update(staff_ids)
            # Do not mutate the shared EA set unless original creation
            # successfully removed Sims from its private restricted copy.
            restricted = set(sim for sim in sims
                             if _sim_id(sim) in allowed)
            if not restricted:
                return None
            before = restricted.copy()
        except Exception:
            # A broken MHS preflight must not spawn outside classmates.
            return None

        # Call EA's original function EXACTLY ONCE. Propagate native
        # exceptions without retry; original may already have side effects.
        created = original(cls, restricted, sim_info, duration,
                           additional_sim_ids, situation_job_count)
        if created is not None:
            assigned = before.difference(restricted)
            sims.difference_update(assigned)
        return created

    wrapped._mhs108_exact_phase = True
    owner.try_start = classmethod(wrapped)

    def uninstall():
        current = owner.__dict__.get('try_start')
        if (not isinstance(current, classmethod)
                or current.__func__ is not wrapped):
            return False
        owner.try_start = prior
        return True

    return uninstall
