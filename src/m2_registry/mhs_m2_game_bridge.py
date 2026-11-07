"""M2 engine-facing helpers, NOT yet bound to the M1 picker confirmation.

Imports game modules lazily, so offline Python tests can load this module.
No patching of EA classes or interaction injection here.
"""
import os
from mhs_m2_roster import canonical_sim_id, RosterError
from mhs_m2_store import RosterStore, EnrollmentService


class BridgeError(RuntimeError):
    pass


from mhs56_slot_identity import (
    TravelSlotGuard, IdentityError, positive_slot, VerifiedSlotBindings)

_SLOT_GUARD = TravelSlotGuard()
_CACHED_RECOVERY = False
_LAST_BOUND = None


def _slot_cache():
    root = os.path.join(os.path.expanduser('~'), 'Documents',
        'Electronic Arts', 'The Sims 4', 'MY_HIGH_SCHOOL_M25_TEST_DATA')
    return VerifiedSlotBindings(os.path.join(
        root, 'MHS_VerifiedSaveIdentity.json'))


def _saved_roster_matches_live_game(slot):
    """Read-only check before trusting a cached EA GUID across restarts."""
    try:
        import services
        from sims.sim_info_types import Age, Species
        from mhs34_settings import SettingsStore
        from mhs97_core_role_store import CoreRoleStore
        folder = os.path.dirname(_slot_cache().path)
        settings = SettingsStore(folder).load(slot)
        if not settings.active or settings.class_count != 2:
            return False
        roster = RosterStore(folder).load(slot)
        groups = tuple(tuple(str(s) for s in roster.class_members(i))
                       for i in (1,2))
        ids = groups[0] + groups[1]
        if (len(groups[0]) != 8 or len(groups[1]) != 8 or
                len(set(ids)) != 16):
            return False
        core = CoreRoleStore(folder).load(slot)
        if (not core.complete or
                not set(core.chosen().values()) <= set(ids)):
            return False
        manager = services.sim_info_manager()
        getter = getattr(manager, 'get', None)
        if not callable(getter):
            return False
        for sid in ids:
            info = getter(int(sid))
            if (info is None or
                    getattr(info, 'age', None) != Age.TEEN or
                    getattr(info, 'species', None) != Species.HUMAN):
                return False
        return True
    except Exception:
        return False



def current_slot(allow_travel=False):
    """Resolve the real EA save, or a uniquely validated prior binding.

    Binding is created only when EA supplied the real numeric slot in an
    earlier session, and live registered Sim IDs still match exactly.
    """
    global _CACHED_RECOVERY, _LAST_BOUND
    try:
        import services
        persistence = services.get_persistence_service()
        if persistence is None:
            raise BridgeError('Servizio EA del salvataggio non disponibile')
        proto = persistence.get_save_slot_proto_buff()
        slot = getattr(proto, 'slot_id', None)
        getter = getattr(persistence, 'get_save_slot_proto_guid', None)
        stable = getter() if callable(getter) else None
        household = services.active_household()
        household_id = getattr(household, 'id', None)
        real = positive_slot(slot)
        if real is not None:
            _CACHED_RECOVERY = False
            result = _SLOT_GUARD.resolve(real, stable, household_id)
            identity = (result, str(stable), str(household_id))
            if identity != _LAST_BOUND and _saved_roster_matches_live_game(result):
                if _slot_cache().remember(result, stable, household_id):
                    _LAST_BOUND = identity
            return result

        # A cold start is accepted only if a REAL slot was previously
        # observed for exactly this stable EA save GUID and household.
        if _SLOT_GUARD.slot is None:
            candidate = _slot_cache().unique(stable, household_id)
            if candidate is not None and _saved_roster_matches_live_game(candidate):
                _SLOT_GUARD.resolve(candidate, stable, household_id)
                _CACHED_RECOVERY = True

        verified_home_write = False
        try:
            import mhs145_classroom_controller as controller
            runtime = controller._RUNTIME
            zone, schedule = controller.zone_schedule()
            at_home = (zone is not None and
                       schedule not in controller.SCHOOL_SCHEDULES)
            verified_home_write = bool(
                at_home and _SLOT_GUARD.slot is not None and
                ((runtime is not None and runtime.active and
                  not runtime.in_school() and
                  runtime.slot == _SLOT_GUARD.slot) or
                 (_CACHED_RECOVERY and
                  _saved_roster_matches_live_game(_SLOT_GUARD.slot))))
        except (ImportError, AttributeError, TypeError, ValueError):
            verified_home_write = False
        return _SLOT_GUARD.resolve(
            slot, stable, household_id, allow_travel=allow_travel,
            verified_home_write=verified_home_write)
    except (IdentityError, ValueError, TypeError, AttributeError,
            ImportError) as exc:
        raise BridgeError('Slot EA non verificato: {}'.format(str(exc)[:125]))

def slot_identity_status():
    """Read-only identity diagnostic, independent from the game's UI."""
    guard = _SLOT_GUARD
    return ('Fonte slot: {} | slot verificato: {} | guid ancorato: {} '
            '| nucleo ancorato: {}'.format(
                guard.last_source, guard.slot or 'no',
                'si' if guard.stable_guid is not None else 'no',
                'si' if guard.household_id is not None else 'no'))


def teenager_checker(sim_id):
    """Verify chosen Sim IDs against current save's SimInfo manager.

    Never assume everything visible in a portrait picker is a teen.
    """
    import services
    from sims.sim_info_types import Age
    sid = canonical_sim_id(sim_id)
    manager = services.sim_info_manager()
    if manager is None:
        return False
    try:
        info = manager.get(int(sid))
    except (AttributeError, TypeError):
        info = None
    if info is None:
        for candidate in manager.get_all():
            cid = getattr(candidate, 'sim_id', getattr(candidate, 'id', None))
            if cid is not None and str(cid) == sid:
                info = candidate
                break
    return info is not None and info.age == Age.TEEN


def default_store():
    """M2 prototype data folder, separate from v1.6 registry data."""
    root = os.path.join(os.path.expanduser('~'), 'Documents',
                        'Electronic Arts', 'The Sims 4', 'MY_HIGH_SCHOOL_M2_DATA')
    return RosterStore(root)


def receive_selected_ids(klass, sim_ids, store=None, slot_provider=None, is_teen=None):
    """For use only when a verified picker callback passes real chosen Sim IDs.

    This function is NOT called by current ConfirmClass1/2 XML.
    """
    service = EnrollmentService(store or default_store(),
                                slot_provider or current_slot,
                                is_teen or teenager_checker)
    return service.enroll_selection(klass, sim_ids)
