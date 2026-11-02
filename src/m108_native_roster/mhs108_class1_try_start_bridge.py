"""M108: OFFLINE-ONLY bridge of Class1 dual-route cap into original EA try_start.

The real WeeklyScheduleSituationSet.start invokes
WeeklyScheduleSituationData.try_start(cls, sims, sim_info, duration,
additional_sim_ids, situation_job_count). The two Class1 branches have one
shared MHS roster and native upper-bound modifiers.

This bridge forwards the original EA method ONE time, with a detached
tuning projection and an exact temporary set of registered Class1 NPCs.
It does not alter the tuning, class trait, Bouncer or shared EA Sim set until
the native method has successfully selected ALL precise candidates.

SAFETY: No actual game runtime proof exists. This file is NOT imported by
a released Mac script. Never enable this from an installed game entrypoint.
"""
from mhs108_class1_dual_route_budget import (
    ClassOneDualRouteBudget, PHASES, STUDENT_JOB, EA_PLAYER_JOB,
)
from mhs108_class1_shadow_cap import project_class1_tuning

REQUIRED_LIVE_GATES = (
    'original_ea_try_start_classmethod_verified',
    'mhs_school_origin_and_full_roster_verified',
    'native_class1_both_routes_tuning_verified',
    'live_ea_player_phase_count_verified',
    'live_ea_route_eligibility_results_verified',
    'class1_shadow_type_accepted_by_native_ea_verified',
    'native_class1_situation_job_counts_verified',
    'bouncer_and_school_membership_verified',
    'staff_and_other_class_untouched_verified',
)


def _guid(value):
    v = getattr(value, 'guid64', None)
    return v if type(v) is int and v > 0 else None


def _sid(sim):
    v = getattr(sim, 'sim_id', None)
    return str(v) if type(v) is int and v > 0 else None


def _phase_data_guid_set():
    ids = set()
    for item in PHASES.values():
        ids.add(item['with_trait_data'])
        ids.add(item['no_trait_data'])
    return frozenset(ids)


EA_CLASS1_DATA_GUIDS = _phase_data_guid_set()


def _native_modifier_counts(cls, situation_job_count):
    """Read real EA (tunedSituation,tunedJob) counts without inserting keys.

    The EA defaultdict uses actual *tuning objects* as map keys, not the
    numeric IDs used by MHS immutable planner.
    """
    if not callable(getattr(situation_job_count, 'get', None)):
        return None
    try:
        entries = cls.job_assignments
        if len(entries) != 1 or _guid(entries[0].job) != STUDENT_JOB:
            return None
        result = {}
        for mod in entries[0].upper_bound_count_modifiers:
            situation_guid, job_guid = _guid(mod.situation), _guid(mod.job)
            if situation_guid is None or job_guid is None:
                return None
            raw = situation_job_count.get((mod.situation, mod.job), 0)
            if type(raw) is not int or raw < 0:
                return None
            result[(situation_guid, job_guid)] = raw
        # The WithTrait route has no prior WithTrait modifier.
        # The planner defaults its prior WithTrait count to 0.
        return result
    except (AttributeError, IndexError, TypeError, ValueError):
        return None


def _verified_context(coordinator, context, guid):
    if not isinstance(coordinator, ClassOneDualRouteBudget):
        return False
    if not isinstance(context, dict):
        return False
    if context.get('mhs_class1_dual_route_active') is not True:
        return False
    if context.get('native_school_phase_origin_verified') is not True:
        return False
    if context.get('ea_job_counts_verified') is not True:
        return False
    if context.get('ea_route_test_results_verified') is not True:
        return False
    if context.get('native_ea_candidate_set_verified') is not True:
        return False
    m = coordinator.manifest
    original_ctx = coordinator.context
    if (str(context.get('save_slot')) != m['save_slot']
            or type(context.get('sim_day')) is not int
            or context['sim_day'] != m['sim_day']
            or str(context.get('zone_id')) != m['school_zone']
            or context.get('time_window') != original_ctx['time_window']
            or context.get('schedule_guid') != original_ctx.get('schedule_guid')
            or coordinator._route(guid) is None):
        return False
    return True


def install_offline_only(ea_weekly_data_class, coordinator_provider,
                         context_provider, live_proofs):
    """Never stack against a different M108 try_start wrapper.

    A caller must supply the SAME coordinator instance for both Class1
    routes in one exact school phase. Tests use synthetic proofs only.
    """
    if (not callable(coordinator_provider)
            or not callable(context_provider)
            or not isinstance(live_proofs, dict)
            or any(live_proofs.get(key) is not True
                   for key in REQUIRED_LIVE_GATES)):
        return None
    owner = None
    for cls in getattr(ea_weekly_data_class, '__mro__',
                       (ea_weekly_data_class,)):
        descriptor = cls.__dict__.get('try_start')
        if isinstance(descriptor, classmethod):
            owner = cls
            break
    if owner is None:
        return None
    descriptor = owner.__dict__['try_start']
    original = descriptor.__func__
    if (getattr(original, '_mhs108_exact_phase', False)
            or getattr(original, '_mhs108_class1_bridge', False)):
        return None

    def wrapped(cls, sims, sim_info, duration, additional_sim_ids,
                situation_job_count):
        guid = _guid(cls)
        if guid not in EA_CLASS1_DATA_GUIDS:
            return original(cls, sims, sim_info, duration,
                            additional_sim_ids, situation_job_count)
        try:
            context = context_provider(cls)
            if (not isinstance(context, dict)
                    or context.get('mhs_class1_dual_route_active') is not True):
                # Vanilla when mod is inactive. No change to EA.
                return original(cls, sims, sim_info, duration,
                                additional_sim_ids, situation_job_count)
            coordinator = coordinator_provider(cls, context)
            if not _verified_context(coordinator, context, guid):
                return None
            counts = _native_modifier_counts(cls, situation_job_count)
            if counts is None:
                return None
            ticket = coordinator.prepare(
                guid, counts, context.get('verified_native_eligible_ids'),
                context)
            if ticket is None:
                return None
            expected_ids = set(ticket['exact_candidate_ids'])
            if not expected_ids:
                # This native route has no approved registered students.
                # Do not create an empty EA situation or seek replacements.
                if not coordinator.confirm(ticket, (), None):
                    coordinator.cancel(ticket)
                return None
            projection = project_class1_tuning(cls, ticket)
            if projection is None:
                coordinator.cancel(ticket)
                return None
            restricted = set(sim for sim in sims
                             if _sid(sim) in expected_ids)
            actual_ids = set(_sid(sim) for sim in restricted)
            if (actual_ids != expected_ids or
                    len(restricted) != len(expected_ids)):
                coordinator.cancel(ticket)
                return None
            before = restricted.copy()
            situation_key = (cls.situation, cls.job_assignments[0].job)
            old_count = situation_job_count.get(situation_key, 0)
            if type(old_count) is not int or old_count < 0:
                coordinator.cancel(ticket)
                return None
        except Exception:
            # A failed verification must not fall back to random EA NPCs.
            return None

        try:
            # Invoke the original EA Python function, not the wrapper,
            # with a detached class view and the exact selected NPCs.
            created = original(projection, restricted, sim_info, duration,
                               additional_sim_ids, situation_job_count)
        except Exception:
            coordinator.cancel(ticket)
            raise  # Never retry a partially successful native EA call.

        if created is None:
            coordinator.cancel(ticket)
            return None

        assigned_sims = before.difference(restricted)
        assigned_ids = tuple(_sid(s) for s in assigned_sims)
        new_count = situation_job_count.get(situation_key, 0)
        if (type(new_count) is not int or
                new_count - old_count != len(assigned_sims)):
            coordinator.cancel(ticket)
            # Native EA may already have side effects. Report the
            # situation ID to avoid a second random native attempt,
            # but do not propagate a bad assignment to the shared set.
            return created
        if coordinator.confirm(ticket, assigned_ids, created):
            sims.difference_update(assigned_sims)
        # A partial/wrong EA result is blocked by coordinator.confirm.
        # We still return an already-created EA ID to prevent retries.
        return created

    wrapped._mhs108_class1_bridge = True
    owner.try_start = classmethod(wrapped)

    def uninstall():
        d = owner.__dict__.get('try_start')
        if not isinstance(d, classmethod) or d.__func__ is not wrapped:
            return False
        owner.try_start = descriptor
        return True

    return uninstall
