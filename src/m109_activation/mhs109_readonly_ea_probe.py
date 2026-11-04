"""M109 read-only inspection of *loaded EA class method shapes*.

This is a diagnostic contract, not a license to activate M108. It inspects
methods supplied by a future EA runtime adapter but changes NO objects and
produces NO trust flags for M109SchoolActivation.

The user's decompiled EA originals establish these method names:
 WeeklyScheduleDay.get_long_term_situation_count (classmethod)
 WeeklyScheduleSituationData.try_start (classmethod)
 SituationManager.create_situation / on_all_sims_spawned_during_zone_spin_up
 SituationManager.get (possibly inherited from a manager base)
 BouncerRequest.clone_for_replace / get_additional_filter_terms
 Bouncer.assign_all_sims_during_zone_spin_up / _monitor_npc_soft_cap
 BaseSituation.all_sims_in_job_gen / get_current_job_for_sim
The diagnostic must fail closed when a method is absent, a descriptor is
the wrong kind or a known MHS competing hook is already present.

Synthetic tests of these method shapes do NOT confirm that the game accepts
Class1 shadow tuning, school SimInfo eligibility, Bouncer caps or roster 16.
There is intentionally NO install() or EA hook in this file.
"""

METHOD_CONTRACT = (
    ('weekly_day', 'get_long_term_situation_count', 'classmethod'),
    ('weekly_data', 'try_start', 'classmethod'),
    ('situation_manager', 'create_situation', 'method'),
    ('situation_manager',
     'on_all_sims_spawned_during_zone_spin_up', 'method'),
    ('situation_manager', 'get', 'method'),
    ('bouncer_request', '__init__', 'method'),
    ('bouncer_request', 'get_additional_filter_terms', 'method'),
    ('bouncer_request', 'clone_for_replace', 'method'),
    ('bouncer', 'request_all_sims_during_zone_spin_up', 'method'),
    ('bouncer', 'assign_all_sims_during_zone_spin_up', 'method'),
    ('bouncer', '_monitor_npc_soft_cap', 'method'),
    ('base_situation', 'all_jobs_gen', 'method'),
    ('base_situation', 'all_sims_in_job_gen', 'method'),
    ('base_situation', 'all_sims_in_situation_gen', 'method'),
    ('base_situation', 'get_current_job_for_sim', 'method'),
)

KNOWN_CONFLICT_MARKERS = (
    '_mhs96_count_hook', '_mhs105_schedule_audit',
    '_mhs89_hook', '_mhs108_count_hook',
    '_mhs108_precreate', '_mhs108_school_filter',
    '_mhs108_no_show_guard', '_mhs108_exact_phase',
    '_mhs108_class1_bridge', '_mhs108_unified_lessons',
    '_mhs108_post_bouncer',
)


def _owner(class_object, name):
    """Find the exact descriptor owner instead of patching a subclass."""
    for parent in getattr(class_object, '__mro__', ()):
        if name in parent.__dict__:
            return parent, parent.__dict__[name]
    return None, None


def _function(descriptor):
    if isinstance(descriptor, (classmethod, staticmethod)):
        return descriptor.__func__
    return descriptor



# The six future M109 atomic stages and their precise EA descriptor owners.
# This inventory does not install hooks or authorize a controller.
HOOK_TARGET_CONTRACT = (
    ('native_base_count', 'weekly_day',
     ('get_long_term_situation_count',)),
    ('native_precreate', 'situation_manager', ('create_situation',)),
    ('school_filter_scope', 'bouncer_request',
     ('__init__', 'get_additional_filter_terms')),
    ('no_show_guard', 'bouncer_request', ('clone_for_replace',)),
    ('unified_lessons', 'weekly_data', ('try_start',)),
    ('post_bouncer_observer', 'situation_manager',
     ('on_all_sims_spawned_during_zone_spin_up',)),
)


def inspect_hook_targets(classes, method_observations):
    """Read-only owner inventory for the six M109 hook stages.

    A stage is only *located*, never game-authorized. In particular,
    SchoolFilterScope must patch both methods on their true owners; when
    those owners differ, the current single-owner adapter cannot be used.
    """
    by_key = {(item['class_key'], item['method_name']): item
              for item in method_observations}
    observations = []
    for stage, class_key, names in HOOK_TARGET_CONTRACT:
        methods = [by_key.get((class_key, name)) for name in names]
        owners = tuple(item['declaring_owner'] for item in methods
                       if item is not None and item['declaring_owner'])
        native_cls = classes.get(class_key) if isinstance(classes, dict) else None
        owner_objects = tuple(_owner(native_cls, name)[0] for name in names)
        if (len(methods) != len(names) or
                any(item is None or
                    item['status'] != 'METHOD_AVAILABLE_NOT_LIVE_VERIFIED'
                    for item in methods)):
            status = 'STAGE_BLOCKED_BY_METHOD_CONTRACT'
        elif (any(owner is None for owner in owner_objects) or
              any(owner is not owner_objects[0]
                  for owner in owner_objects[1:])):
            status = 'STAGE_OWNER_SPLIT_OR_UNKNOWN'
        else:
            status = 'STAGE_TARGET_LOCATED_NOT_LIVE_VERIFIED'
        observations.append({
            'stage': stage,
            'class_key': class_key,
            'method_names': names,
            'declaring_owners': owners,
            'status': status,
        })
    return tuple(observations)


def inspect_runtime_shapes(classes):
    """Observe loaded method descriptors without touching EA runtime.

    Input values are the class objects from the CURRENT loaded game,
    obtained independently by a read-only adapter. A synthetic caller
    could pass fake objects; therefore this report can NEVER authorize
    M109 hook activation by itself.
    """
    if not isinstance(classes, dict):
        classes = {}
    items = []
    problems = []
    for key, name, kind in METHOD_CONTRACT:
        obj = classes.get(key)
        owner, descriptor = _owner(obj, name)
        status = 'METHOD_AVAILABLE_NOT_LIVE_VERIFIED'
        detail = ''
        if not isinstance(obj, type):
            status = 'EA_CLASS_NOT_SUPPLIED'
        elif owner is None:
            status = 'ORIGINAL_METHOD_MISSING'
        elif kind == 'classmethod' and not isinstance(descriptor, classmethod):
            status = 'EA_METHOD_DESCRIPTOR_MISMATCH'
        elif kind == 'method' and isinstance(descriptor, (
                classmethod, staticmethod)):
            status = 'EA_METHOD_DESCRIPTOR_MISMATCH'
        elif not callable(_function(descriptor)):
            status = 'EA_METHOD_NOT_CALLABLE'
        elif any(getattr(_function(descriptor), marker, False)
                 for marker in KNOWN_CONFLICT_MARKERS):
            status = 'COMPETING_SCHOOL_HOOK_ALREADY_INSTALLED'
        if status != 'METHOD_AVAILABLE_NOT_LIVE_VERIFIED':
            problems.append((key, name, status))
        if owner is not None:
            detail = owner.__module__ + '.' + owner.__name__
        items.append({
            'class_key': key,
            'method_name': name,
            'descriptor_kind': kind,
            'declaring_owner': detail,
            'status': status,
        })
    hook_targets = inspect_hook_targets(classes, items)
    located = sum(item['status'] == 'STAGE_TARGET_LOCATED_NOT_LIVE_VERIFIED'
                  for item in hook_targets)
    known_markers = [
        {'class_key': key, 'method_name': name, 'status': status}
        for key, name, status in problems
        if status == 'COMPETING_SCHOOL_HOOK_ALREADY_INSTALLED'
    ]
    return {
        'kind': 'M109_READ_ONLY_EA_METHOD_DIAGNOSTIC',
        'status': ('METHOD_SHAPES_AVAILABLE_UNVERIFIED'
                   if not problems else 'NATIVE_EA_METHODS_NOT_READY'),
        'method_observations': tuple(items),
        'problems': tuple(problems),
        'method_count_expected': len(METHOD_CONTRACT),
        'method_count_available': len(METHOD_CONTRACT) - len(problems),
        'hook_target_observations': hook_targets,
        'hook_target_count_expected': len(HOOK_TARGET_CONTRACT),
        'hook_target_count_located_unverified': located,
        'known_mhs_hook_markers_found': tuple(known_markers),
        # No supported read-only scan can certify all third-party patches.
        'absence_of_other_school_hooks_verified': False,
        'runtime_hook_install_authorized': False,
        # Not a real SimInfo test, calendar invocation or Bouncer proof.
        'activation_authorized_by_game': False,
        'ea_live_provenance_verified': False,
        'school_situation_assignment_verified': False,
        'full_16_student_attendance_verified': False,
        'mutated_game_objects': False,
    }
