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
    TravelSlotGuard, IdentityError, positive_slot, VerifiedSlotBindings,
    synthetic_slot_for_guid)

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
        from sims.sim_info_types import Species
        from mhs34_settings import SettingsStore
        folder = os.path.dirname(_slot_cache().path)
        # Identity must survive *incomplete* edits: a removed student,
        # disabled activation or a missing Core role is not a different save.
        # Attendance preflight separately enforces 8+8 and all five roles.
        if not os.path.isfile(SettingsStore(folder).path(slot)):
            return False
        if not os.path.isfile(RosterStore(folder).path(slot)):
            return False
        settings = SettingsStore(folder).load(slot)
        if settings.class_count != 2:
            return False
        roster = RosterStore(folder).load(slot)
        groups = tuple(tuple(str(s) for s in roster.class_members(i))
                       for i in (1,2))
        ids = groups[0] + groups[1]
        if not (1 <= len(ids) <= 20 and len(set(ids)) == len(ids)):
            return False
        manager = services.sim_info_manager()
        getter = getattr(manager, 'get', None)
        if not callable(getter):
            return False
        matching = 0
        for sid in ids:
            info = getter(int(sid))
            if (info is not None and
                    getattr(info, 'species', None) == Species.HUMAN):
                matching += 1
        # Teenagers can age up or die between saves; the identifier must
        # still be recoverable to allow the menu to remove/reassign them.
        # The EA classroom controller checks actual teenage eligibility
        # before inviting anybody; identity restoration does not.
        return matching >= min(3, len(ids))
    except Exception:
        return False



_MIGRATION_DIAGNOSTIC = 'NOT_NEEDED'


def _adopt_legacy_school_registry(stable, household_id):
    """Convert an already chosen legacy 2x8 roster to isolated GUID storage.

    Only the first verified HOME bootstrap may do this. All four original
    JSON files remain byte-for-byte untouched. An unrelated save cannot be
    assigned based on its display name or a guessed EA numeric slot.
    """
    global _MIGRATION_DIAGNOSTIC
    try:
        import services
        from sims.sim_info_types import Age, Species
        from mhs_save_as_copy import import_unique_copy, SaveAsCopyError
        from mhs34_settings import SettingsStore
        from mhs53_staff_store import StaffStore
        from mhs97_core_role_store import CoreRoleStore
        from mhs56_slot_identity import stable_token, positive_id
        if stable_token(stable) is None or positive_id(household_id) is None:
            _MIGRATION_DIAGNOSTIC='EA_GUID_OR_HOUSEHOLD_UNAVAILABLE'
            return None
        binding=_slot_cache()
        if binding.has_identity(stable, household_id):
            _MIGRATION_DIAGNOSTIC='AMBIGUOUS_EXISTING_BINDING'
            return None
        target=synthetic_slot_for_guid(stable)
        folder=os.path.dirname(binding.path)
        stores=(SettingsStore(folder),RosterStore(folder),
                StaffStore(folder),CoreRoleStore(folder))
        if any(os.path.lexists(store.path(target)) for store in stores):
            # Never claim a pre-existing high-range store as another save.
            _MIGRATION_DIAGNOSTIC='GUID_STORE_ALREADY_EXISTS_UNBOUND'
            return None
        household=services.active_household()
        manager=services.sim_info_manager()
        if household is None or manager is None:
            _MIGRATION_DIAGNOSTIC='EA_SIM_MANAGER_NOT_READY'
            return None
        played=tuple(str(info.sim_id) for info in household.sim_info_gen()
                     if getattr(info,'age',None)==Age.TEEN and
                        getattr(info,'species',None)==Species.HUMAN)
        if not played:
            _MIGRATION_DIAGNOSTIC='NO_PLAYABLE_TEEN_FOR_SAFE_IMPORT'
            return None
        try:
            report=import_unique_copy(
                folder,target,manager,Age.TEEN,Species.HUMAN,
                (Age.YOUNGADULT,Age.ADULT,Age.ELDER),played)
        except SaveAsCopyError as exc:
            _MIGRATION_DIAGNOSTIC='SAFE_IMPORT_'+str(exc)[:110]
            return None
        if not _saved_roster_matches_live_game(target):
            _MIGRATION_DIAGNOSTIC='IMPORTED_ROSTER_NOT_IN_EA_SAVE'
            return None
        if not binding.remember(target,stable,household_id):
            _MIGRATION_DIAGNOSTIC='VERIFIED_BINDING_DISK_WRITE_FAILED'
            return None
        _MIGRATION_DIAGNOSTIC='IMPORTED_FROM_'+report['source']
        return target
    except Exception as exc:
        _MIGRATION_DIAGNOSTIC='UNEXPECTED_'+type(exc).__name__
        return None


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
            binding=_slot_cache()
            candidate = binding.unique(stable, household_id)
            if candidate is not None and _saved_roster_matches_live_game(candidate):
                _SLOT_GUARD.resolve(candidate, stable, household_id)
                _CACHED_RECOVERY = True
            elif candidate is None and not binding.has_identity(stable,household_id):
                # Migration of pre-M160 saves: only from a HOME lot, and
                # only after verifying all 16 existing students/staff/Core
                # identities in the current EA save. The source JSON stays
                # untouched and the new GUID store is independent.
                try:
                    import mhs145_classroom_controller as controller
                    zone,schedule=controller.zone_schedule()
                    home=(zone is not None and
                          schedule not in controller.SCHOOL_SCHEDULES)
                except (ImportError, AttributeError, TypeError, ValueError):
                    home=False
                if home:
                    candidate=_adopt_legacy_school_registry(stable,household_id)
                    if candidate is not None:
                        _SLOT_GUARD.resolve(candidate,stable,household_id)
                        _CACHED_RECOVERY=True

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
        result = _SLOT_GUARD.resolve(
            slot, stable, household_id, allow_travel=allow_travel,
            verified_home_write=verified_home_write)
        if (_CACHED_RECOVERY and verified_home_write and
                _saved_roster_matches_live_game(result)):
            # User may switch household within the same verified save.
            # Remember its new household only after the same GUID and
            # controller/home context were positively validated.
            _slot_cache().remember(result, stable, household_id)
        return result
    except (IdentityError, ValueError, TypeError, AttributeError,
            ImportError) as exc:
        raise BridgeError('Slot EA non verificato: {}'.format(str(exc)[:125]))

def slot_identity_status():
    """Read-only identity diagnostic, independent from the game's UI."""
    guard = _SLOT_GUARD
    return ('Fonte slot: {} | slot verificato: {} | guid ancorato: {} '
            '| nucleo ancorato: {} | recupero: {}'.format(
                guard.last_source, guard.slot or 'no',
                'si' if guard.stable_guid is not None else 'no',
                'si' if guard.household_id is not None else 'no',
                _MIGRATION_DIAGNOSTIC))


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
