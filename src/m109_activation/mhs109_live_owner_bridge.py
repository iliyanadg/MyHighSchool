"""M109: map the six EA hook owners from the live game method layout.

READ-ONLY integration bridge. The M109 probe demonstrated the names and
declaring classes on a real Mac Sims 4 installation (2026-11-03). This
module resolves the *actual Python class objects* provided by a future
live adapter, not owners guessed from class names or from a JSON file.

It NEVER installs a hook, imports Sims, validates the school day, proves
EA provenance, or authorizes the 16-student controller. Synthetic classes
can satisfy the same shape; this is only one prerequisite for integration.
Python 3.7 compatible.
"""
from mhs109_readonly_ea_probe import (
    HOOK_TARGET_CONTRACT, inspect_runtime_shapes,
)

# Exact owners measured in the user's opt-in in-game M109 report.
# SituationManager.get is inherited from IndexedManager; it is a read-only
# lookup and intentionally NOT a target for any of the six patch stages.
EXPECTED_EA_OWNERS = {
    'weekly_day':
        'venues.weekly_schedule_zone_director.WeeklyScheduleDay',
    'weekly_data':
        'venues.weekly_schedule_zone_director.WeeklyScheduleSituationData',
    'situation_manager':
        'situations.situation_manager.SituationManager',
    'bouncer_request':
        'situations.bouncer.bouncer_request.BouncerRequest',
}


def _declaring_owner(native_class, name):
    for base in getattr(native_class, '__mro__', ()):
        if name in base.__dict__:
            return base
    return None


def resolve_six_native_stage_owners(classes):
    """Return six exact declaring class *references* only when all match EA.

    Raises ValueError on missing, wrapped, split, inherited-to-wrong-owner
    or incompatible descriptors. A successful return is NOT a game
    authorization and is NOT a proof of actual EA situation creation.
    The caller must obtain the classes from independently observed game
    imports; do not trust a JSON file to supply runtime class objects.
    """
    if not isinstance(classes, dict):
        raise ValueError('NATIVE_CLASSES_NOT_SUPPLIED')
    observed = inspect_runtime_shapes(classes)
    if (observed['status'] != 'METHOD_SHAPES_AVAILABLE_UNVERIFIED'
            or observed['method_count_available'] !=
            observed['method_count_expected']
            or observed['hook_target_count_located_unverified'] !=
            observed['hook_target_count_expected']
            or observed['hook_target_count_expected'] != 6
            or observed['problems']):
        raise ValueError('NATIVE_METHODS_CHANGED_OR_CONFLICTING')

    owners = {}
    for stage, class_key, names in HOOK_TARGET_CONTRACT:
        native_cls = classes.get(class_key)
        expected_name = EXPECTED_EA_OWNERS.get(class_key)
        if not isinstance(native_cls, type) or not expected_name:
            raise ValueError('MISSING_EA_CLASS_' + stage)
        actual = tuple(_declaring_owner(native_cls, n) for n in names)
        if (not actual or any(o is None for o in actual)
                or any(o is not actual[0] for o in actual[1:])):
            raise ValueError('SPLIT_OR_MISSING_STAGE_OWNER_' + stage)
        owner = actual[0]
        if owner.__module__ + '.' + owner.__name__ != expected_name:
            raise ValueError('EA_STAGE_OWNER_CHANGED_' + stage)
        owners[stage] = owner

    if len(owners) != 6:
        raise ValueError('INCOMPLETE_STAGE_GRAPH')
    # Class references only. No install(), no class mutation, no proof flags.
    return owners
