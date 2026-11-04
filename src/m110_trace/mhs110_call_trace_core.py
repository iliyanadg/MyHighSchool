"""Opt-in M110 pass-through diagnostic; Python 3.7, no Sims imports.

This temporarily wraps three live EA descriptors in *memory*. It does NOT
change rosters, tuning, Sim objects or situations, but wrapper installation
itself is a runtime modification and carries compatibility risk. Never arm
automatically; on any conflict refuse, and restore only own descriptors.
"""

TARGETS = (
    ('weekly_day', 'get_long_term_situation_count', 'classmethod',
     'venues.weekly_schedule_zone_director.WeeklyScheduleDay'),
    ('weekly_data', 'try_start', 'classmethod',
     'venues.weekly_schedule_zone_director.WeeklyScheduleSituationData'),
    ('situation_manager', 'create_situation', 'method',
     'situations.situation_manager.SituationManager'),
)
EVENT_LIMIT = 1024


def _guid(value):
    try:
        guid = getattr(value, 'guid64', None)
        return guid if type(guid) is int and guid > 0 else None
    except Exception:
        return None


def _related_guid(value, attribute):
    # Diagnostic metadata must never prevent or retry the native EA call.
    try:
        return _guid(getattr(value, attribute, None))
    except Exception:
        return None


def _old_hook_found(fn):
    try:
        return any(key.startswith('_mhs') and value is True
                   for key, value in vars(fn).items())
    except Exception:
        return True


class M110Trace(object):
    """Three exact native EA method calls, without changing return values."""

    def __init__(self):
        self._original = {}
        self._wrapped = {}
        self._active = False
        self._locked = False
        self._events = []
        self._total = 0
        self._errors = []
        self._counts = {item[1]: 0 for item in TARGETS}

    def _record(self, stage, phase, guid, result=None,
                related_guid=None):
        # Logging must never block or modify an EA callback.
        try:
            self._counts[stage] += (1 if phase == 'enter' else 0)
            self._total += 1
            if len(self._events) >= EVENT_LIMIT:
                return
            event = {'n': self._total, 'method': stage,
                     'phase': phase, 'target_guid': guid}
            if related_guid is not None:
                event['related_situation_guid'] = related_guid
            if stage in ('create_situation', 'try_start') and phase == 'return':
                # This is NOT proof of a spawned Sim or assigned EA job.
                if result is None:
                    event['ea_return_state'] = 'NONE'
                elif type(result) is bool:
                    event['ea_return_state'] = (
                        'TRUE' if result else 'FALSE')
                elif type(result) is int:
                    event['ea_return_state'] = (
                        'POSITIVE_INT' if result > 0 else 'NONPOSITIVE_INT')
                else:
                    event['ea_return_state'] = 'OTHER'
            if stage == 'get_long_term_situation_count' and phase == 'return':
                if (type(result) is tuple and len(result) == 2
                        and all(type(x) is int and 0 <= x <= 100
                                for x in result)):
                    event['ea_count_pair'] = list(result)
            self._events.append(event)
        except Exception:
            pass

    def _make_wrapper(self, method_name, descriptor):
        original = descriptor.__func__ if isinstance(descriptor, classmethod) else descriptor
        tracker = self
        if method_name == 'get_long_term_situation_count':
            def wrapper(cls, *args, **kwargs):
                guid = _guid(cls)
                data = args[0] if args else kwargs.get('data')
                related = _related_guid(data, 'situation')
                tracker._record(method_name, 'enter', guid,
                                related_guid=related)
                try:
                    result = original(cls, *args, **kwargs)
                except BaseException:
                    tracker._record(method_name, 'raise', guid,
                                    related_guid=related)
                    raise
                tracker._record(method_name, 'return', guid, result,
                                related_guid=related)
                return result
            wrapped = classmethod(wrapper)
        elif method_name == 'try_start':
            def wrapper(cls, *args, **kwargs):
                guid = _guid(cls)
                related = _related_guid(cls, 'situation')
                tracker._record(method_name, 'enter', guid,
                                related_guid=related)
                try:
                    result = original(cls, *args, **kwargs)
                except BaseException:
                    tracker._record(method_name, 'raise', guid,
                                    related_guid=related)
                    raise
                tracker._record(method_name, 'return', guid, result,
                                related_guid=related)
                return result
            wrapped = classmethod(wrapper)
        else:
            def wrapper(self, *args, **kwargs):
                situation_type = args[0] if args else kwargs.get('situation_type')
                guid = _guid(situation_type)
                tracker._record(method_name, 'enter', guid)
                try:
                    result = original(self, *args, **kwargs)
                except BaseException:
                    tracker._record(method_name, 'raise', guid)
                    raise
                tracker._record(method_name, 'return', guid, result)
                return result
            wrapped = wrapper
        wrapper._mhs110_trace_wrapper = True
        return wrapped

    def start(self, classes):
        if self._active or self._locked or self._original:
            return False
        if not isinstance(classes, dict):
            self._errors.append('CLASSES_UNAVAILABLE')
            return False
        candidates = []
        for key, name, kind, expected_owner in TARGETS:
            owner = classes.get(key)
            if (not isinstance(owner, type)
                    or owner.__module__ + '.' + owner.__name__ != expected_owner
                    or name not in owner.__dict__):
                self._errors.append('OWNER_CHANGED_' + name)
                return False
            descriptor = owner.__dict__[name]
            if kind == 'classmethod':
                if not isinstance(descriptor, classmethod):
                    self._errors.append('DESCRIPTOR_CHANGED_' + name)
                    return False
                fn = descriptor.__func__
            else:
                if isinstance(descriptor, (classmethod, staticmethod)):
                    self._errors.append('DESCRIPTOR_CHANGED_' + name)
                    return False
                fn = descriptor
            if not callable(fn) or _old_hook_found(fn):
                self._errors.append('CONFLICTING_HOOK_' + name)
                return False
            candidates.append((owner, name, descriptor))
        try:
            for owner, name, desc in candidates:
                wrapper = self._make_wrapper(name, desc)
                self._original[name] = (owner, desc)
                self._wrapped[name] = wrapper
                setattr(owner, name, wrapper)
                if owner.__dict__.get(name) is not wrapper:
                    raise RuntimeError('EA_OWNER_REJECTED_' + name)
        except Exception:
            self._errors.append('WRAPPER_INSTALL_FAILED')
            if not self._restore():
                self._locked = True
            return False
        self._active = True
        return True

    def _restore(self):
        # Atomic precheck: on partial install some descriptors are still
        # original. Reject only a THIRD-PARTY replacement, not an untouched
        # original. Never overwrite a wrapper we do not own.
        for name, (owner, descriptor) in self._original.items():
            current = owner.__dict__.get(name)
            if (current is not descriptor
                    and current is not self._wrapped.get(name)):
                self._errors.append('OTHER_WRAPPER_REPLACED_M110')
                return False
        ok = True
        for name, (owner, descriptor) in reversed(list(self._original.items())):
            if owner.__dict__.get(name) is descriptor:
                continue
            try:
                setattr(owner, name, descriptor)
                if owner.__dict__.get(name) is not descriptor:
                    ok = False
            except Exception:
                ok = False
        if not ok:
            self._errors.append('RESTORE_INCOMPLETE')
            return False
        self._original.clear()
        self._wrapped.clear()
        self._active = False
        return True

    def stop(self):
        if not self._active and not self._original:
            return False
        result = self._restore()
        self._locked = not result
        return result

    def report(self):
        return {
            'kind': 'M110_OPT_IN_PASS_THROUGH_RUNTIME_TRACE',
            'status': ('RESTORE_CONFLICT' if self._locked else
                       'OBSERVING' if self._active else 'INACTIVE'),
            'temporary_runtime_wrappers_active': self._active,
            'runtime_descriptors_temporarily_modified': bool(self._original),
            'sim_roster_or_ea_tuning_mutated_by_m110': False,
            'ea_gameplay_functions_called_unchanged': True,
            'proves_16_students_or_classrooms': False,
            'third_party_hooks_absence_verified': False,
            'event_limit': EVENT_LIMIT,
            'event_total': self._total,
            'events_kept': len(self._events),
            'event_details_truncated': self._total > len(self._events),
            'event_counts': dict(self._counts),
            'events': list(self._events),
            'errors': list(self._errors),
        }
