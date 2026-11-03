"""M114: resolve the ORIGINAL live EA BouncerRequest methods safely.

M109's in-game read-only report established exact owner:
situations.bouncer.bouncer_request.BouncerRequest, declaring all three
methods (__init__, get_additional_filter_terms, clone_for_replace).
This loads that same class and validates its unmodified method shapes.
It does not install any hook or provide a game-authorizing proof flag.

The blank filter is deliberately NOT guessed: the original native game
filter must be independently identified/verified for this patch. Any
missing EA type or unexpected monkey patch is a hard blocker.
"""
from mhs114_school_bouncer_pair import _valid_owner, EXPECTED_BOUNCER_OWNER


def inspect_original_ea_bouncer_owner():
    result = {
        'kind': 'M114_ORIGINAL_EA_BOUNCER_OWNER_READ_ONLY',
        'status': 'EA_BOUNCER_OWNER_NOT_READY',
        'expected_owner': EXPECTED_BOUNCER_OWNER,
        'actual_owner': None,
        'methods_owned_by_native_class': False,
        'game_modified': False,
        'native_bouncer_filter_proof': False,
        'native_blank_filter_verified': False,
        'native_ea_job_assignment_verified': False,
        'runtime_override_authorized': False,
    }
    try:
        from situations.bouncer.bouncer_request import BouncerRequest
        from sims.sim_info_types import Age, Species
        import services
        name = BouncerRequest.__module__ + '.' + BouncerRequest.__name__
        result['actual_owner'] = name
        if not _valid_owner(BouncerRequest):
            result['status'] = 'EA_BOUNCER_DESCRIPTOR_OWNER_MISMATCH'
            return None, result
        infos = services.sim_info_manager()
        lookup = getattr(infos, 'get', None) if infos is not None else None
        if not callable(lookup):
            result['status'] = 'EA_SIM_INFO_LOOKUP_UNAVAILABLE'
            return None, result
        if (getattr(Age, 'TEEN', None) is None
                or getattr(Species, 'HUMAN', None) is None):
            result['status'] = 'EA_HUMAN_TEEN_ENUMS_UNAVAILABLE'
            return None, result
        result['methods_owned_by_native_class'] = True
        result['status'] = 'EA_OWNER_AVAILABLE_NOT_FILTER_AUTHORIZED'
        # Return references only in caller memory; do not serialize
        # game objects, mutate EA classes or declare installation safe.
        return {
            'owner': BouncerRequest,
            'teen_age': Age.TEEN,
            'human_species': Species.HUMAN,
            'sim_info_lookup': lookup,
        }, result
    except Exception as exc:
        result['status'] = 'EA_BOUNCER_OWNER_READ_FAILED'
        result['error_type'] = type(exc).__name__
        return None, result
