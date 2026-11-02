"""M108: opt-in school-only EA Base situation count 6 -> 8 (offline).

EA snippets 277657 and 279958 tune six long-term Base situations,
created BEFORE the Core situation. The user's day needs EIGHT Base NPC
requests in addition to FIVE user-chosen Core NPCs and THREE playable
teens. The existing M96 hook proved the classmethod seam but was not
installed, since EA's Core roles were not reserved before the Base count.

This module reuses the SAME EA classmethod seam (never stacks with M96),
but binds it to M108's immutable 3+5+8 manifest and pre-schedule local
Core holds. No shipped script imports or activates this adapter.

An exact count returned by EA's count classmethod is not proof that
eight Base situations are created, spawn, survive Bouncer caps, or seat.
"""
SCHOOL_SCHEDULES = frozenset((277657, 279958))
BASE_SITUATION = 277733
EA_TUNED_BASE_COUNT = 6
MHS_BASE_COUNT = 8

REQUIRED_LIVE_GATES = (
    'original_ea_weekly_classmethod_verified',
    'schedule_provenance_verified',
    'school_zone_save_day_verified',
    'early_core_holds_verified_in_live_context',
    'native_core_and_base_invitation_hooks_verified',
    'school_only_bouncer_admission_verified',
    'school_only_no_show_guard_verified',
    'npc_lot_capacity_verified',
)


def _is_int(value):
    return type(value) is int


def _context_valid(session, context):
    if not isinstance(context, dict):
        return False
    try:
        manifest = session.manifest
        return (
            context.get('native_weekly_school_origin_verified') is True
            and context.get('school_verified') is True
            and context.get('ea_schedule_not_started') is True
            and context.get('schedule_guid') in SCHOOL_SCHEDULES
            and str(context.get('save_slot')) == manifest['save_slot']
            and _is_int(context.get('sim_day'))
            and context['sim_day'] == manifest['sim_day']
            and str(context.get('school_zone')) == manifest['school_zone']
        )
    except (AttributeError, KeyError, ValueError, TypeError):
        return False


def _manifest_valid(session):
    """No guessed fifth Core role; no changes to registered Sim IDs."""
    try:
        m = session.manifest
        hold = session._local_core_holds
        if (m['status'] != 'M108_INVITATIONS_PREPARED_NOT_GAME_AUTHORIZED'
                or hold is None or len(hold) != 5
                or tuple(hold) != tuple(m['core_assignments'])
                or len(m['classes']) != 2
                or any(len(c) != 8 for c in m['classes'])
                or len(m['all_16']) != 16
                or len(set(m['all_16'])) != 16
                or len(m['playable']) != 3
                or len(m['base_ids']) != 8
                or len(set(m['base_ids'])) != 8
                or session._base_cursor != 0
                or session._core_confirmed
                or session._pending
                or session._confirmed):
            return False
        core_ids = tuple(sid for _, sid in hold)
        if (len(set(core_ids)) != 5
                or len(set(m['playable'] + core_ids +
                           m['base_ids'])) != 16
                or set(m['playable'] + core_ids +
                       m['base_ids']) != set(m['all_16'])):
            return False
        return True
    except (AttributeError, KeyError, TypeError, ValueError):
        return False


def propose_native_base_count(original, schedule_guid, situation_guid,
                              session, context):
    """Return (8,8) *proposal* only for the original verified EA count.

    The EA classmethod might already have applied a playable-Sim
    adjustment. A distinct, live-verified integer deduction must explain
    it; never silently assume 6, 3, or 'six minus three playables'.
    """
    if (not _is_int(schedule_guid) or
            schedule_guid not in SCHOOL_SCHEDULES or
            not _is_int(situation_guid) or
            situation_guid != BASE_SITUATION or
            not _context_valid(session, context) or
            not _manifest_valid(session)):
        return original
    if (not isinstance(original, tuple) or len(original) != 2
            or not all(_is_int(x) and x >= 0 for x in original)):
        return original
    # No inferred adjustments. An actual EA observation must supply
    # this deduction (0 through 3), separately from the original count.
    adjustment = context.get('ea_original_playable_adjustment')
    if (not _is_int(adjustment) or not 0 <= adjustment <= 3 or
            context.get('ea_playable_adjustment_verified') is not True):
        return original
    expected_original = EA_TUNED_BASE_COUNT - adjustment
    if original != (expected_original, expected_original):
        return original
    # Defensive: the original observed number of native Base slots is
    # strictly less than the eight planned explicit Base invitations.
    return (MHS_BASE_COUNT, MHS_BASE_COUNT)


def install_offline_only(schedule_class, session, context_provider,
                         verified_live_gates):
    """Wrap original EA classmethod ONCE, allow clean uninstallation.

    Not a game entry point. The live gates do not yet have a verified
    provider. Unit tests use synthetic flags ONLY to test isolation.
    """
    if (not callable(context_provider) or
            not isinstance(verified_live_gates, dict) or
            any(verified_live_gates.get(key) is not True
                for key in REQUIRED_LIVE_GATES) or
            not _manifest_valid(session)):
        return None
    owner = None
    for cls in getattr(schedule_class, '__mro__', (schedule_class,)):
        descriptor = getattr(cls, '__dict__', {}).get(
            'get_long_term_situation_count')
        if isinstance(descriptor, classmethod):
            owner = cls
            break
    if owner is None:
        return None
    prior_descriptor = owner.__dict__['get_long_term_situation_count']
    previous = prior_descriptor.__func__
    if (getattr(previous, '_mhs96_count_hook', False)
            or getattr(previous, '_mhs105_schedule_audit', False)
            or getattr(previous, '_mhs108_count_hook', False)):
        return None

    def wrapped(cls, data, resolver):
        original = previous(cls, data, resolver)
        try:
            situation = getattr(data, 'situation', None)
            guid = getattr(situation, 'guid64', None)
            sguid = getattr(cls, 'guid64', None)
            if sguid not in SCHOOL_SCHEDULES or guid != BASE_SITUATION:
                return original
            context = context_provider()
            return propose_native_base_count(original, sguid, guid,
                                             session, context)
        except Exception:
            return original

    wrapped._mhs108_count_hook = True
    owner.get_long_term_situation_count = classmethod(wrapped)

    def uninstall():
        if (owner.__dict__.get('get_long_term_situation_count') is not None
                and isinstance(owner.__dict__[
                    'get_long_term_situation_count'], classmethod)
                and owner.__dict__[
                    'get_long_term_situation_count'].__func__ is wrapped):
            owner.get_long_term_situation_count = prior_descriptor
            return True
        return False

    return uninstall
