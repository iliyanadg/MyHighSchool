"""M115: read-only assembly of native EA BouncerRequest + blank filter.

This resolves *both* concrete engine objects discovered by M109 and
sim_filter_service.py:
  situations.bouncer.bouncer_request.BouncerRequest
  filters.tunable.TunableSimFilter.BLANK_FILTER
The native object is passed into M114's existing shared invitation-scoped
filter/no-show pair. This function does NOT call stage_graph/install,
does NOT turn on any Bouncer hook, and grants no synthetic proof flags.

An independent game context/Bouncer request evidence provider is still
required to prove whether each exact invited NPC may safely bypass a
specific school SituationJob filter. Native blank presence alone does
not prove roster capacity, role eligibility or arrival.
"""
from mhs114_native_bouncer_owner import inspect_original_ea_bouncer_owner
from mhs114_school_bouncer_pair import build_school_bouncer_pair
from mhs115_native_blank_filter import inspect_native_blank_filter


def prepare_original_ea_bouncer_pair(session, context_provider):
    """Return (pair, evidence) without changing EA or the player's save."""
    outcome = {
        'kind': 'M115_LIVE_EA_NATIVE_BOUNCER_ASSEMBLY_READ_ONLY',
        'status': 'BLOCKED_UNVERIFIED_NATIVE_EA_OBJECTS',
        'game_modified': False,
        'bouncer_descriptors_modified': False,
        'blank_filter_source': 'filters.tunable.TunableSimFilter.BLANK_FILTER',
        'no_custom_sim_filter_created': True,
        'native_blank_ea_resolved': False,
        'native_bouncer_owner_resolved': False,
        'shared_invitation_scope_constructed': False,
        'native_ea_school_context_verified': False,
        'filter_override_authorized': False,
        'school_attendance_16_verified': False,
        'classroom_8_plus_8_seating_verified': False,
    }
    if not callable(context_provider):
        outcome['status'] = 'MISSING_NATIVE_EA_CONTEXT_PROVIDER'
        return None, outcome
    try:
        owner, owner_report = inspect_original_ea_bouncer_owner()
        if (owner is None
                or owner_report.get('status')
                != 'EA_OWNER_AVAILABLE_NOT_FILTER_AUTHORIZED'):
            outcome['status'] = 'EA_BOUNCER_OWNER_NOT_READY'
            return None, outcome
        outcome['native_bouncer_owner_resolved'] = True
        blank, blank_report = inspect_native_blank_filter()
        if (blank is None or blank_report.get('status') !=
                'EA_BLANK_CONSTANT_INSPECTED_NOT_BOUNCER_AUTHORIZED'):
            outcome['status'] = 'EA_NATIVE_BLANK_FILTER_NOT_READY'
            return None, outcome
        outcome['native_blank_ea_resolved'] = True
        pair, why = build_school_bouncer_pair(
            session, owner['owner'], blank, owner['teen_age'],
            owner['human_species'], owner['sim_info_lookup'],
            context_provider)
        if pair is None:
            outcome['status'] = why
            return None, outcome
        outcome['shared_invitation_scope_constructed'] = True
        outcome['status'] = 'EA_BOUNCER_PAIR_PREPARED_NOT_ACTIVATED'
        return pair, outcome
    except Exception as exc:
        outcome['status'] = 'EA_BOUNCER_ASSEMBLY_EXCEPTION'
        outcome['error_type'] = type(exc).__name__
        return None, outcome
