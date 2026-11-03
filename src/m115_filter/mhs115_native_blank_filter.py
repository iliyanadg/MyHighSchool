"""M115: resolve EA's native BLANK_FILTER rather than inventing tuning.

Original EA sim_filter_service.py, from the player's 2026-11-02
decompiled source, line 211:
    if sim_filter is None:
        sim_filter = filters.tunable.TunableSimFilter.BLANK_FILTER
This source is evidence that such a constant is used by EA, NOT proof
it is safe to bypass any particular Bouncer job. Never mutate it.

A blank native filter does NOT override Sim constraints, blacklist,
required story arcs, request exclusivity, capacity or job acceptance.
This is a read-only resolver: no BouncerRequest patch, no game command.
"""


def _empty(values):
    return type(values) in (tuple, list) and len(values) == 0


def inspect_native_blank_filter():
    """Return (native_filter, metadata); fail closed on any ambiguity.

    The only accepted object is the real EA class-level constant.
    We never construct a fake Tuning resource or accept a user-supplied
    lookalike object. Check the methods used by EA's sim_filter_service.
    """
    result = {
        'kind': 'M115_NATIVE_EA_BLANK_SIM_FILTER_READ_ONLY',
        'status': 'NOT_INSPECTED',
        'ea_constant_path': 'filters.tunable.TunableSimFilter.BLANK_FILTER',
        'native_constant_loaded': False,
        'filter_terms_observed_empty': False,
        'conform_terms_observed_empty': False,
        'aggregate_filter_observed_false': False,
        'filter_repurpose_flag_observed': False,
        'game_modified': False,
        'bouncer_request_patched': False,
        'native_filter_job_eligibility_verified': False,
        'bouncer_blank_filter_safe_in_game': False,
        'native_school_16_membership_verified': False,
        'activation_authorized': False,
    }
    try:
        from filters.tunable import TunableSimFilter
        source = getattr(TunableSimFilter, 'BLANK_FILTER', None)
        if source is None:
            result['status'] = 'NATIVE_EA_BLANK_FILTER_MISSING'
            return None, result
        terms = getattr(source, 'get_filter_terms', None)
        conform = getattr(source, 'get_additional_conform_terms', None)
        aggregate = getattr(source, 'is_aggregate_filter', None)
        if not all(callable(x) for x in (terms, conform, aggregate)):
            result['status'] = 'NATIVE_EA_BLANK_FILTER_METHODS_MISSING'
            return None, result
        filter_terms = terms()
        conform_terms = conform()
        is_aggregate = aggregate()
        result['filter_terms_observed_empty'] = _empty(filter_terms)
        result['conform_terms_observed_empty'] = _empty(conform_terms)
        result['aggregate_filter_observed_false'] = is_aggregate is False
        repurpose = getattr(source, 'repurpose_game_breaker', None)
        result['filter_repurpose_flag_observed'] = type(repurpose) is bool
        if not all((
                result['filter_terms_observed_empty'],
                result['conform_terms_observed_empty'],
                result['aggregate_filter_observed_false'],
                result['filter_repurpose_flag_observed'])):
            result['status'] = 'NATIVE_EA_BLANK_FILTER_NOT_PLAIN'
            return None, result
        result['native_constant_loaded'] = True
        result['status'] = 'EA_BLANK_CONSTANT_INSPECTED_NOT_BOUNCER_AUTHORIZED'
        return source, result
    except Exception as exc:
        result['status'] = 'NATIVE_EA_BLANK_FILTER_READ_FAILED'
        result['error_type'] = type(exc).__name__
        return None, result


def native_blank_matches(candidate):
    """Identity check against the same live EA constant, not a fake GUID."""
    native, report = inspect_native_blank_filter()
    return (native is not None and candidate is native
            and report['native_constant_loaded'] is True)
