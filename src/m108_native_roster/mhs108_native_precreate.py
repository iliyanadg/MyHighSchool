"""M108 offline-only adapter for the *original* EA situation creation call.

No automatic install, no script entry point, no Mac beta. This follows M89's
verified seam but covers both EA Base 277733 and Core 298052 situations.
Only usable after separately proven native gates; mock-green is NOT game-green.
"""
from mhs108_native_invitation import BASE_SITUATION, CORE_SITUATION


REQUIRED_LIVE_GATES = (
    'native_school_origin_verified',
    'verified_before_schedule_core_hold',
    'school_only_filter_admission_verified',
    'no_show_and_departure_fallback_blocked',
    'eight_native_base_situations_verified',
    'class_one_eight_phase_slots_verified',
    'class_two_eight_phase_slots_verified',
    'npc_lot_capacity_verified',
    'native_teacher_and_staff_preserved',
)


def _all_proven(proof):
    """Every flag must be explicitly True; no optimistic defaults."""
    return (isinstance(proof, dict) and
            all(proof.get(name) is True for name in REQUIRED_LIVE_GATES))


def install(manager_class, session, context_provider, proven_live_gates):
    """Return an uninstall callback or None.

    This function deliberately has NO runtime invocation path. Production
    must separately verify gates from actual EA gameplay, not just populate
    a dict with True. In tests, the gates are simulated to check behavior.
    """
    if (not _all_proven(proven_live_gates) or
            not callable(context_provider) or
            not callable(getattr(session, 'preview', None)) or
            not callable(getattr(session, 'acknowledge_created', None)) or
            not callable(getattr(session, 'cancel', None)) or
            not getattr(session, '_local_core_holds', None)):
        return None
    original = getattr(manager_class, 'create_situation', None)
    if (not callable(original) or
            getattr(original, '_mhs89_hook', False) or
            getattr(original, '_mhs108_precreate', False)):
        return None

    def wrapped(self, situation_type, *args, **kwargs):
        guid = getattr(situation_type, 'guid64', None)
        if guid not in (BASE_SITUATION, CORE_SITUATION):
            return original(self, situation_type, *args, **kwargs)

        # Original EA accepts guest_list as its first positional argument.
        # If both forms are provided, never interpret an ambiguous call.
        if 'guest_list' in kwargs and args:
            return original(self, situation_type, *args, **kwargs)
        guest_list = kwargs.get('guest_list', args[0] if args else None)
        try:
            context = context_provider()
        except Exception:
            return original(self, situation_type, *args, **kwargs)

        # A verification of venue or creation_source text alone is not enough.
        # Unverified context must leave the vanilla game unchanged.
        if not session._valid_origin(context):
            return original(self, situation_type, *args, **kwargs)

        ticket, replacement = session.preview(guid, guest_list, context)
        if ticket is None or replacement is None:
            # With all real gates proven, a verified school Base/Core call
            # that cannot use one of the fixed enrolled IDs must NOT spawn
            # an unregistered random teenager.
            return None

        try:
            if 'guest_list' in kwargs:
                call_kwargs = dict(kwargs, guest_list=replacement)
                created = original(self, situation_type, *args, **call_kwargs)
            elif args:
                created = original(self, situation_type, replacement,
                                   *args[1:], **kwargs)
            else:
                # Never improvise an absent EA guest list.
                session.cancel(ticket)
                return None
        except Exception:
            session.cancel(ticket)
            # DO NOT retry original: an exception may follow partial EA work.
            raise

        if not session.acknowledge_created(ticket, created):
            session.cancel(ticket)
        return created

    wrapped._mhs108_precreate = True
    manager_class.create_situation = wrapped

    def uninstall():
        if manager_class.create_situation is not wrapped:
            return False
        manager_class.create_situation = original
        return True

    return uninstall
