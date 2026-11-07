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
    synthetic_slot_for_guid, NamedSaveBindings, save_name_token,
    synthetic_slot_for_named_save)

_SLOT_GUARD = TravelSlotGuard()
_CACHED_RECOVERY = False
_LAST_BOUND = None
_LAST_SAVE_TITLE = None
_LAST_ZONE_TOKEN = None


def _named_slot_cache():
    root = os.path.dirname(_slot_cache().path)
    return NamedSaveBindings(os.path.join(root, 'MHS_VerifiedSaveNames.json'))


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


def _is_at_home():
    try:
        import mhs145_classroom_controller as controller
        zone, schedule = controller.zone_schedule()
        return zone is not None and schedule not in controller.SCHOOL_SCHEDULES
    except (ImportError, AttributeError, TypeError, ValueError):
        return False


def _adopt_legacy_school_registry(stable, household_id,
                                  save_title=None, previous_slot=None):
    """Safely clone a verified school into an isolated Save As identity.

    A distinct EA save title is *additional* evidence only. The four source
    registries must pass the full live SimInfo verification, never a name-only
    match. Two legacy slots with identical school configurations are safe
    sources; divergent candidates cannot be chosen by filename or timestamp.
    """
    global _MIGRATION_DIAGNOSTIC
    try:
        import services
        from sims.sim_info_types import Age, Species
        from mhs_save_as_copy import (
            import_unique_copy, import_copy, prepare_copy, SaveAsCopyError)
        from mhs34_settings import SettingsStore
        from mhs53_staff_store import StaffStore
        from mhs97_core_role_store import CoreRoleStore
        from mhs56_slot_identity import stable_token, positive_id
        title = save_name_token(save_title)
        if stable_token(stable) is None or positive_id(household_id) is None:
            _MIGRATION_DIAGNOSTIC = 'EA_GUID_OR_HOUSEHOLD_UNAVAILABLE'
            return None
        binding = _slot_cache()
        named = _named_slot_cache()
        if title is None and binding.has_identity(stable, household_id):
            _MIGRATION_DIAGNOSTIC = 'AMBIGUOUS_EXISTING_BINDING'
            return None
        if title is not None and named.has_conflict(stable, title):
            _MIGRATION_DIAGNOSTIC = 'DUPLICATE_SAVE_NAME_UNSAFE'
            return None
        target = (synthetic_slot_for_named_save(stable, title) if title
                  else synthetic_slot_for_guid(stable))
        folder = os.path.dirname(binding.path)
        stores = (SettingsStore(folder), RosterStore(folder),
                  StaffStore(folder), CoreRoleStore(folder))
        if any(os.path.lexists(store.path(target)) for store in stores):
            _MIGRATION_DIAGNOSTIC = 'TARGET_STORE_ALREADY_EXISTS_UNBOUND'
            return None
        household = services.active_household()
        manager = services.sim_info_manager()
        if household is None or manager is None:
            _MIGRATION_DIAGNOSTIC = 'EA_SIM_MANAGER_NOT_READY'
            return None
        played = tuple(str(info.sim_id) for info in household.sim_info_gen()
                       if getattr(info, 'age', None) == Age.TEEN and
                          getattr(info, 'species', None) == Species.HUMAN)
        if not played:
            _MIGRATION_DIAGNOSTIC = 'NO_PLAYABLE_TEEN_FOR_SAFE_IMPORT'
            return None
        inputs = (manager, Age.TEEN, Species.HUMAN,
                  (Age.YOUNGADULT, Age.ADULT, Age.ELDER), played)
        try:
            if previous_slot is not None:
                # The previous active HOME session is the trustworthy source
                # for a second or third Save As, even if other saves diverge.
                report = import_copy(folder, previous_slot, target, *inputs)
            elif title:
                # M165 cache can contain two real slots for the SAME GUID.
                # Accept them only if their *complete* school payloads are
                # equivalent after rebinding to the new target slot.
                sources = sorted(set(item['slot'] for item in binding._load()
                                     if item['guid'] == stable_token(stable) and
                                     item['household'] == str(household_id)),
                                 key=int)
                candidates = []
                for source in sources:
                    try:
                        candidates.append(prepare_copy(
                            folder, source, target, *inputs))
                    except SaveAsCopyError:
                        continue
                if candidates:
                    signature = candidates[0]['configuration']
                    if any(row['configuration'] != signature
                           for row in candidates[1:]):
                        raise SaveAsCopyError('AMBIGUOUS_LEGACY_SAVE_AS')
                    report = import_copy(folder, candidates[0]['source'],
                                         target, *inputs)
                else:
                    report = import_unique_copy(folder, target, *inputs)
            else:
                report = import_unique_copy(folder, target, *inputs)
        except SaveAsCopyError as exc:
            _MIGRATION_DIAGNOSTIC = 'SAFE_IMPORT_' + str(exc)[:110]
            return None
        if not _saved_roster_matches_live_game(target):
            _MIGRATION_DIAGNOSTIC = 'IMPORTED_ROSTER_NOT_IN_EA_SAVE'
            return None
        if title:
            remembered = named.remember(target, stable, title, household_id)
        else:
            remembered = binding.remember(target, stable, household_id)
        if not remembered:
            _MIGRATION_DIAGNOSTIC = 'VERIFIED_BINDING_DISK_WRITE_FAILED'
            return None
        _MIGRATION_DIAGNOSTIC = 'IMPORTED_FROM_' + report['source']
        return target
    except Exception as exc:
        _MIGRATION_DIAGNOSTIC = 'UNEXPECTED_' + type(exc).__name__
        return None


def current_slot(allow_travel=False):
    """Resolve the active EA save, including *distinctly named* Save As forks.

    The normal numerical EA slot remains preferred when it can be observed.
    If EA exposes a scratch slot after a cold restart, the exact EA save name
    resolves to a separately verified roster. If two saves remain indistinct,
    fail closed; never silently mix school registries.
    """
    global _CACHED_RECOVERY, _LAST_BOUND, _LAST_SAVE_TITLE, _LAST_ZONE_TOKEN
    try:
        import services
        persistence = services.get_persistence_service()
        if persistence is None:
            raise BridgeError('Servizio EA del salvataggio non disponibile')
        proto = persistence.get_save_slot_proto_buff()
        slot = getattr(proto, 'slot_id', None)
        title = save_name_token(getattr(proto, 'slot_name', None))
        getter = getattr(persistence, 'get_save_slot_proto_guid', None)
        stable = getter() if callable(getter) else None
        household = services.active_household()
        household_id = getattr(household, 'id', None)
        real = positive_slot(slot)
        zone_object = getattr(services, 'current_zone', lambda: None)()
        zone_token = id(zone_object) if zone_object is not None else None
        named = _named_slot_cache() if title else None
        if named is not None and named.has_conflict(stable, title):
            raise BridgeError('Nomi di salvataggio duplicati: identita ambigua')

        if real is not None:
            # An already named, separately validated store may be synthetic.
            # Keep using it even when the EA proto briefly exposes a number.
            mapped = named.unique(stable, title) if named else None
            if mapped is not None and _saved_roster_matches_live_game(mapped):
                result = _SLOT_GUARD.resolve(mapped, stable, household_id)
            else:
                result = _SLOT_GUARD.resolve(real, stable, household_id)
            _CACHED_RECOVERY = False
            identity = (result, str(stable), str(household_id))
            if identity != _LAST_BOUND and _saved_roster_matches_live_game(result):
                if mapped is not None and named is not None:
                    if named.remember(result, stable, title, household_id):
                        _LAST_BOUND = identity
                else:
                    if _slot_cache().remember(result, stable, household_id):
                        _LAST_BOUND = identity
                    if named is not None:
                        named.remember(result, stable, title, household_id)
            if title is not None:
                _LAST_SAVE_TITLE = title
            _LAST_ZONE_TOKEN = zone_token
            return result

        previous_slot = None
        if (title is not None and _LAST_SAVE_TITLE is not None and
                title != _LAST_SAVE_TITLE and _SLOT_GUARD.slot is not None):
            # Save As while EA still reports scratch: the old writable
            # anchor must NOT be reused for the newly named game save.
            # A Save As does NOT reload the zone. Loading a different save
            # normally does; never clone from that unrelated former session.
            if zone_token is not None and zone_token == _LAST_ZONE_TOKEN:
                previous_slot = _SLOT_GUARD.slot
            _SLOT_GUARD.reset()
            _CACHED_RECOVERY = False
            _LAST_BOUND = None

        if _SLOT_GUARD.slot is None:
            binding = _slot_cache()
            candidate = named.unique(stable, title) if named else None
            # A named binding exists but belongs to another set of Sims:
            # do not fallback to an older unrelated registry.
            if candidate is not None and not _saved_roster_matches_live_game(candidate):
                raise BridgeError('Registro del salvataggio non corrispondente')
            if candidate is None and not title:
                candidate = binding.unique(stable, household_id)
            if candidate is not None and _saved_roster_matches_live_game(candidate):
                _SLOT_GUARD.resolve(candidate, stable, household_id)
                _CACHED_RECOVERY = True
            elif _is_at_home():
                if title is not None:
                    # Even an old M165 cache with slots 10 AND 16 can be
                    # recovered when their rosters are exactly equivalent.
                    candidate = _adopt_legacy_school_registry(
                        stable, household_id, title, previous_slot)
                elif not binding.has_identity(stable, household_id):
                    candidate = _adopt_legacy_school_registry(stable,
                                                                household_id)
                if candidate is not None:
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
        result = _SLOT_GUARD.resolve(
            slot, stable, household_id, allow_travel=allow_travel,
            verified_home_write=verified_home_write)
        if (_CACHED_RECOVERY and verified_home_write and
                _saved_roster_matches_live_game(result)):
            if named is None:
                _slot_cache().remember(result, stable, household_id)
            else:
                named.remember(result, stable, title, household_id)
        if title is not None:
            _LAST_SAVE_TITLE = title
        _LAST_ZONE_TOKEN = zone_token
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
