"""M108 offline-only protection against losing a selected student's ID.

From the user's decompiled EA sources:
  BaseSituation.on_failed_to_spawn_sim_for_request() -> request.clone_for_replace(
      only_if_explicit=True)
  BaseSituation.submit_replace_request() -> request.clone_for_replace()
  BouncerRequest.clone_for_replace() creates a new request WITHOUT
      requested_sim_id, allowing a random replacement.

Prevent that conversion ONLY for already-recognised, exact school student
requests. Do not touch the EA no-show job tuning, teacher/cafeteria/staff,
other situations, school attendance itself, or saved Sim data.

DISABLED: No import/installation by a Mac build. The scoped policy requires
live facts that have NOT been proven in the user's game yet.
"""

REQUIRED_NO_SHOW_PROOFS = (
    'native_school_request_class_verified',
    'exact_school_request_provenance_verified',
    'student_filter_scope_installed',
    'bouncer_no_show_and_departure_paths_verified',
    'non_school_replacement_preservation_verified',
)


class SchoolNoShowGuard(object):
    """Never suppress a native replacement unless scope owns its request."""

    def __init__(self, school_filter_scope):
        if (not callable(getattr(school_filter_scope, 'is_tracked', None))
                or not callable(getattr(school_filter_scope, 'snapshot', None))):
            raise ValueError('M108 exact student scope required')
        self.school_scope = school_filter_scope
        self.suppressed_clones = 0
        self.outside_school_unchanged = 0

    def must_preserve_id(self, request):
        """False on ANY unknown request, old day, extra NPC, or other lot."""
        try:
            if not self.school_scope.is_tracked(request):
                return False
            sid = getattr(request, '_requested_sim_id', None)
            if type(sid) is not int or sid <= 0:
                return False
            if (getattr(request, '_continue_if_constraints_fail', None)
                    is not False):
                return False
            constraints = getattr(request, '_constrained_sim_ids', None)
            if (not isinstance(constraints, (set, frozenset))
                    or constraints != {sid}):
                return False
            # is_tracked verifies school/save/day, situation, job and exact
            # roster ID. The original EA job filter is unchanged globally.
            return True
        except (AttributeError, TypeError, ValueError):
            return False

    def snapshot(self):
        return {
            'kind': 'M108_OFFLINE_SCHOOL_EXACT_NO_SHOW_GUARD',
            'suppressed_random_student_clones': self.suppressed_clones,
            'outside_school_clone_calls_preserved': self.outside_school_unchanged,
            'native_no_show_hook_tested_in_game': False,
            'student_no_show_fallback_fully_blocked': False,
            'attendance_verified': False,
        }


def install_offline_only(request_class, guard, verified_proofs):
    """Wrap only EA BouncerRequest.clone_for_replace; never dispatch clones.

    The original BaseSituation callback remains intact. For a registered
    school student its call to clone_for_replace returns None; the original
    on_sim_unassigned_from_request callback can still remove a departing Sim.
    For unrelated requests the original EA clone method runs unchanged.

    In-game installation is intentionally NOT wired to this function.
    """
    if (not isinstance(guard, SchoolNoShowGuard)
            or not isinstance(verified_proofs, dict)
            or any(verified_proofs.get(k) is not True
                   for k in REQUIRED_NO_SHOW_PROOFS)):
        return None
    previous = getattr(request_class, 'clone_for_replace', None)
    if (not callable(previous)
            or getattr(previous, '_mhs108_no_show_guard', False)):
        return None

    def wrapped(self, *args, **kwargs):
        if guard.must_preserve_id(self):
            guard.suppressed_clones += 1
            # Never call the EA clone: it drops requested_sim_id.
            return None
        guard.outside_school_unchanged += 1
        return previous(self, *args, **kwargs)

    wrapped._mhs108_no_show_guard = True
    request_class.clone_for_replace = wrapped

    def uninstall():
        if request_class.clone_for_replace is not wrapped:
            return False
        request_class.clone_for_replace = previous
        return True

    return uninstall
