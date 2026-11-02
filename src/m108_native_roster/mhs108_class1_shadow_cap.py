"""M108 temporary *non-global* class-one EA phase tuning projection.

EA's WeeklyScheduleSituationData.try_start classmethod reads cls fields:
job_assignments, default_job_order, default_met_minimum_jobs,
default_need_minimum_jobs, situation and user_facing.

Never write a replacement upper_bound into the original EA tuned snippet
or the shared job/role tuning. Instead prepare an isolated Python shadow
class for RESEARCH ONLY. A future controlled adapter might invoke the
ORIGINAL method with the shadow, but this is NOT VERIFIED with the native
EA hashed tuning metaclass and is NOT included in any release.

The caller must ALSO restrict the input Sim set to the exact candidate
IDs in the ClassOneDualRouteBudget ticket. This shadow alone is NOT a
student selection filter and does not override EA's tests/trait rules.
"""
from types import SimpleNamespace
from mhs108_class1_dual_route_budget import (
    EA_ORIGINAL_CLASS1_UPPER, STUDENT_JOB, EA_PLAYER_JOB, PHASES,
)


def _guid(value):
    guid = getattr(value, 'guid64', None)
    return guid if type(guid) is int and guid > 0 else None


def project_class1_tuning(original_ea_class, ticket):
    """Return a detached class containing one copied EA student job.

    None on any unknown original tuning, wrong native modifier pair,
    or malformed prior-verified ticket. NEVER mutate an EA object.
    """
    if not isinstance(ticket, dict):
        return None
    phase = ticket.get('phase')
    route = ticket.get('route')
    data = PHASES.get(phase)
    if route not in ('with_trait', 'no_trait') or data is None:
        return None
    expected_data = data[
        'with_trait_data' if route == 'with_trait'
        else 'no_trait_data']
    expected_situation = data[
        'with_trait_situation' if route == 'with_trait'
        else 'no_trait_situation']
    if (ticket.get('data_guid') != expected_data
            or ticket.get('native_situation') != expected_situation
            or ticket.get('native_student_job') != STUDENT_JOB
            or ticket.get('native_original_tuned_upper') != 6
            or ticket.get('changes_to_ea_tuning') is not False
            or _guid(original_ea_class) != expected_data
            or _guid(getattr(original_ea_class, 'situation', None))
            != expected_situation):
        return None
    proposed_upper = ticket.get('proposed_per_call_tuned_upper')
    candidates = ticket.get('exact_candidate_ids')
    modifiers = ticket.get('playables_in_global_ea_phase')
    with_trait_count = ticket.get('native_already_in_with_trait')
    effective = ticket.get('proposed_effective_upper')
    if (type(proposed_upper) is not int or not 0 <= proposed_upper <= 11
            or type(modifiers) is not int or not 0 <= modifiers <= 3
            or type(with_trait_count) is not int
            or type(candidates) is not tuple
            or len(candidates) > 8
            or len(candidates) != len(set(candidates))
            or any(type(x) is not str or not x.isdigit() for x in candidates)
            or type(effective) is not int
            or effective != len(candidates)
            or proposed_upper !=
            (modifiers + (with_trait_count if route == 'no_trait' else 0)
             + effective)):
        return None
    try:
        assignments = original_ea_class.job_assignments
        if len(assignments) != 1:
            return None
        old_entry = assignments[0]
        old_interval = old_entry.sim_count
        if (_guid(old_entry.job) != STUDENT_JOB
                or type(old_interval.lower_bound) is not int
                or old_interval.lower_bound != 0
                or old_interval.upper_bound != EA_ORIGINAL_CLASS1_UPPER):
            return None
        actual_modifiers = set((
            _guid(mod.situation), _guid(mod.job))
            for mod in old_entry.upper_bound_count_modifiers)
        needed_modifiers = {
            (data['player_situation'], EA_PLAYER_JOB)}
        if route == 'no_trait':
            needed_modifiers.add(
                (data['with_trait_situation'], STUDENT_JOB))
        if actual_modifiers != needed_modifiers:
            return None
        # Preserve original resolver/test objects by identity.
        shadow_entry = SimpleNamespace(
            job=old_entry.job,
            sim_count=SimpleNamespace(
                lower_bound=old_interval.lower_bound,
                upper_bound=proposed_upper),
            tests=old_entry.tests,
            upper_bound_count_modifiers=
                old_entry.upper_bound_count_modifiers,
        )
        job = old_entry.job
        attributes = {
            'guid64': expected_data,
            'situation': original_ea_class.situation,
            'job_assignments': (shadow_entry,),
            'default_job_order': [job],
            'default_need_minimum_jobs': {},
            'default_met_minimum_jobs': {job: shadow_entry},
            'user_facing': original_ea_class.user_facing,
        }
        original_name = str(original_ea_class)

        class _ViewMetaclass(type):
            def __str__(cls):
                # EA logs 'creation_source=str(cls)' during try_start.
                return original_name

        projected = _ViewMetaclass(
            'M108UnreleasedClassOnePhaseShadow', (object,), attributes)
        if (projected.job_assignments[0].sim_count.upper_bound !=
                proposed_upper
                or old_entry.sim_count.upper_bound != 6):
            return None
        return projected
    except (AttributeError, KeyError, TypeError, ValueError):
        return None
