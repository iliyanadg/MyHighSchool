"""M109 stage adapter: capture and restore original EA method descriptors.

OFFLINE ONLY. No Sims imports or automatic installation. A future real EA
adapter must supply the EXACT target owner (including base classes when a
classmethod is inherited), method attributes, native M108 installer and
the expected hook marker. This object exposes {'install','restore'} stages
for M109SchoolActivation, and captures originals BEFORE any modifications.

Fail closed if another module changes a method between capture and restore.
Do not overwrite unknown third-party patches. Optional cleanup should also
revert per-request temporary filter mutations on affected BouncerRequests.
"""
_MISSING = object()

KNOWN_HOOKS = {
    'native_base_count': (
        'get_long_term_situation_count', '_mhs108_count_hook'),
    'native_precreate': ('create_situation', '_mhs108_precreate'),
    'school_filter_scope': (
        ('__init__', 'get_additional_filter_terms'),
        '_mhs108_school_filter'),
    'no_show_guard': ('clone_for_replace', '_mhs108_no_show_guard'),
    'unified_lessons': ('try_start', '_mhs108_unified_lessons'),
    'post_bouncer_observer': (
        'on_all_sims_spawned_during_zone_spin_up', '_mhs108_post_bouncer'),
}


def _marker_method(raw):
    return raw.__func__ if isinstance(raw, classmethod) else raw


class M109NativeStage(object):
    """A single M108 module, with emergency descriptor-level rollback.

    The underlying M108 installer may return a normal uninstall callback.
    The emergency restoration path is only for a partial install which
    already placed a recognizable M108 wrapper but never returned its
    own uninstall. It does not undo irreversible game-side EA situations.
    """

    def __init__(self, name, target_owner, installer, cleanup=None):
        if (name not in KNOWN_HOOKS
                or not isinstance(target_owner, type)
                or not callable(installer)
                or (cleanup is not None and not callable(cleanup))):
            raise ValueError('invalid native EA hook stage')
        self.name = name
        attribute, marker = KNOWN_HOOKS[name]
        self.attributes = (
            attribute if isinstance(attribute, tuple) else (attribute,))
        self.marker = marker
        self.target_owner = target_owner
        self._installer = installer
        self._cleanup = cleanup
        self._captured = None
        self._native_undo = None

    def _original_descriptors(self):
        return {attribute:
                self.target_owner.__dict__.get(attribute, _MISSING)
                for attribute in self.attributes}

    def _changes_safe(self):
        if self._captured is None:
            return False
        current = self._original_descriptors()
        for attribute in self.attributes:
            before = self._captured[attribute]
            after = current[attribute]
            if after is before:
                continue
            if after is _MISSING:
                return False
            if getattr(_marker_method(after), self.marker, False) is not True:
                return False
        return True

    def install(self, manifest, evidence):
        if self._captured is not None:
            return False
        originals = self._original_descriptors()
        # A stage attached to the wrong owner is not an acceptable
        # integration point even if the class inherits a similar method.
        if any(value is _MISSING for value in originals.values()):
            return False
        if any(getattr(_marker_method(value), self.marker, False) is True
               for value in originals.values()):
            return False
        self._captured = originals
        # This may raise AFTER patching only one method. M109 has
        # already registered restore(), so the marker-checked emergency
        # path will run even if no native uninstall callback was returned.
        self._native_undo = self._installer(manifest, evidence)
        if not callable(self._native_undo):
            return False
        if (not self._changes_safe()
                or any(self._original_descriptors()[attribute]
                       is self._captured[attribute]
                       for attribute in self.attributes)):
            return False
        return True

    def restore(self):
        if self._captured is None:
            # A never-installed stage may be restored safely.
            return True
        if not self._changes_safe():
            return False
        if self._native_undo is not None:
            try:
                if self._native_undo() is True:
                    # A callback could return success incorrectly.
                    if self._original_descriptors() == self._captured:
                        if self._cleanup is not None:
                            try:
                                if self._cleanup() is not True:
                                    return False
                            except Exception:
                                return False
                        self._captured = None
                        self._native_undo = None
                        return True
            except Exception:
                # Only restore still-recognizable own M108 wrappers.
                pass
        # Emergency raw descriptor restoration when the normal callback
        # was not obtained or could not restore a partially installed hook.
        if not self._changes_safe():
            return False
        for name, before in self._captured.items():
            if self._original_descriptors()[name] is before:
                continue
            setattr(self.target_owner, name, before)
        if self._cleanup is not None:
            try:
                if self._cleanup() is not True:
                    return False
            except Exception:
                return False
        if self._original_descriptors() != self._captured:
            return False
        self._native_undo = None
        self._captured = None
        return True

    def as_stage(self):
        return {'install': self.install, 'restore': self.restore}
