"""M108 read-only school NPC soft-cap preflight (no cap bypass).

EA original Bouncer._monitor_npc_soft_cap is gated by active household
and zone-running state; it uses:
  SimSpawner.number_of_npcs_instantiated
  SimSpawner.number_of_npcs_leaving
  SimSpawner.npc_soft_cap
and can expedite NPC departures when the limit is reached/exceeded.
Its reservation requests can separately modify the effective NPC cap.

The school requires 13 exact nonplayable teens PLUS the selected real
NPC staff. There is no universal fixed "20 Sim lot limit" in this policy.
All counts must be observed during the *same* native zone epoch.

No modification to spawner, Bouncer, live NPCs, or Sim traits.
"""
from mhs108_native_invitation import (
    prepare_fixed_manifest, InvitationPlanError,
)


def _ids(values):
    if not isinstance(values, (list, tuple, set, frozenset)):
        return None
    result = set()
    for value in values:
        if (type(value) not in (str, int) or
                not str(value).isdigit() or
                str(int(value)) != str(value) or
                int(value) <= 0 or str(value) in result):
            return None
        result.add(str(value))
    return result


def _report(status, reason='', **kw):
    result = {
        'status': status,
        'reason': reason,
        'changes_to_game': False,
        'npc_spawner_capacity_verified': False,
        'school_attendance_verified': False,
        'seating_verified': False,
    }
    result.update(kw)
    return result


def assess_npc_school_capacity(
        manifest, school_staff_npc_ids, present_npc_ids,
        leaving_npc_ids, number_of_npcs_instantiated,
        number_of_npcs_leaving, npc_soft_cap, context):
    """Conservatively project school NPC total after missing NPCs arrive.

    This is a snapshot, NOT an admission/priority guarantee. Bouncer can
    still replace requests or expel NPCs later if the counts change.
    """
    if not isinstance(manifest, dict):
        return _report('INVALID_ROSTER')
    try:
        canonical = prepare_fixed_manifest(
            manifest['classes'], manifest['playable'],
            dict(manifest['core_assignments']),
            manifest['save_slot'], manifest['sim_day'],
            manifest['school_zone'])
        for key in ('classes', 'playable', 'all_16',
                    'core_assignments', 'base_ids',
                    'save_slot', 'sim_day', 'school_zone'):
            if manifest.get(key) != canonical[key]:
                return _report('INVALID_ROSTER')
        students = set(canonical['base_ids']) | set(
            sid for _, sid in canonical['core_assignments'])
        staff = _ids(school_staff_npc_ids)
        here = _ids(present_npc_ids)
        leaving = _ids(leaving_npc_ids)
        if (staff is None or not staff or here is None or leaving is None
                or students & staff or not leaving <= here
                or staff & set(canonical['playable'])
                or not all(type(i) is int and i >= 0 for i in (
                    number_of_npcs_instantiated,
                    number_of_npcs_leaving, npc_soft_cap))
                or number_of_npcs_instantiated < len(here)
                or number_of_npcs_leaving < len(leaving)
                or number_of_npcs_leaving > number_of_npcs_instantiated
                or len(here) < len(leaving)):
            return _report('INVALID_NPC_OBSERVATION')
        if (not isinstance(context, dict)
                or context.get('native_ea_spawner_counters_verified') is not True
                or context.get('school_staff_ids_verified') is not True
                or context.get('active_household_present') is not True
                or context.get('zone_running') is not True
                or str(context.get('save_slot')) != canonical['save_slot']
                or context.get('sim_day') != canonical['sim_day']
                or str(context.get('zone_id')) != canonical['school_zone']):
            return _report('UNVERIFIED_NPC_CONTEXT')
    except (ValueError, TypeError, KeyError, InvitationPlanError):
        return _report('INVALID_NPC_OBSERVATION')

    required = students | staff
    at_risk = tuple(sorted(required & leaving))
    missing = tuple(sorted(required - here))
    if at_risk:
        return _report(
            'REGISTERED_STUDENT_OR_STAFF_LEAVING',
            'an exact required school NPC is already departing',
            required_school_npc_total=len(required),
            leaving_required_ids=at_risk,
            missing_required_ids=missing)
    if npc_soft_cap <= 0:
        return _report('INVALID_NPC_OBSERVATION')
    remaining_not_leaving = (
        number_of_npcs_instantiated - number_of_npcs_leaving)
    predicted = remaining_not_leaving + len(missing)
    margin = npc_soft_cap - predicted
    details = {
        'required_school_npc_total': len(required),
        'enrolled_school_npc_count': len(students),
        'verified_staff_npc_count': len(staff),
        'existing_npcs_not_leaving': remaining_not_leaving,
        'missing_required_ids': missing,
        'predicted_instantiated_npcs': predicted,
        'observed_npc_soft_cap': npc_soft_cap,
        'projected_soft_cap_margin': margin,
        # At equality the EA Bouncer may replace a lower-priority
        # already assigned NPC with a higher-priority unfulfilled request.
        'npc_spawner_capacity_verified': margin > 0,
    }
    if margin == 0:
        return _report(
            'SCHOOL_NPC_SOFT_CAP_AT_LIMIT',
            'EA Bouncer can evict an NPC even at the exact soft cap',
            **details)
    if margin < 0:
        return _report(
            'SCHOOL_NPC_SOFT_CAP_SHORTFALL',
            'native Bouncer can expedite departures; no cap bypass',
            **details)
    return _report(
        'SCHOOL_NPC_CAPACITY_SNAPSHOT_OK',
        'instantaneous count margin only, not an EA attendance guarantee',
        **details)
