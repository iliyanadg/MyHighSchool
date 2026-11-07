"""M168: track the EA *save operation*, not an inferred save title.

PersistenceService.save_game_gen receives save_game_data.slot_id for the
actual destination. After the original EA generator successfully finishes,
a changed real slot indicates Save As. Copy and rebind the four existing
MHS registries before the player can open the next pie menu.

The generator wrapper preserves the original result, send and exceptions.
No import-time EA hooks; install() is called by the existing bootstrap.

Based on independent public research of Llamafone's save hook (MIT/LICENSE
status must be checked before copying implementation; this is original code).
"""
import os

_INSTALLED = False
_LAST_STATUS = 'NOT_SEEN'
_HOOK = None


def last_status():
    return _LAST_STATUS


def _real_slot(data):
    from mhs56_slot_identity import positive_slot
    slot = positive_slot(getattr(data, 'slot_id', None))
    if slot is None:
        return None
    try:
        from services.persistence_service import AUTO_SAVE_SLOT_ID
        if str(AUTO_SAVE_SLOT_ID) == slot:
            return None
    except (ImportError, AttributeError, TypeError, ValueError):
        pass
    return slot


def _snapshot_source():
    """Capture source before EA changes the current save to the destination.

    Read only. Never infer from the save's name or the household alone.
    """
    try:
        import services
        import mhs_m2_game_bridge as bridge
        import mhs145_classroom_controller as controller
        zone = services.current_zone()
        if zone is None:
            return None
        live_runtime = controller._RUNTIME
        candidates = []
        # The last completed EA save is more authoritative than the
        # classroom controller, which may still reference the previous
        # Save As source until its optional home refresh has completed.
        committed = bridge._COMMITTED_SAVE_ANCHOR
        if committed is not None and committed[1] == id(zone):
            candidates.append(str(committed[0]))
        if bridge._SLOT_GUARD.slot is not None:
            candidates.append(str(bridge._SLOT_GUARD.slot))
        if live_runtime is not None and live_runtime.active:
            candidates.append(str(live_runtime.slot))
        # If an existing session was loaded without an armed controller,
        # try its verified save identity. This never creates a new registry.
        try:
            candidates.append(str(bridge.current_slot(allow_travel=True)))
        except Exception:
            pass
        for candidate in candidates:
            if bridge._saved_roster_matches_live_game(candidate):
                return (candidate, id(zone))
    except Exception:
        pass
    return None


def _copy_selected_school(source, destination):
    """Copy four validated registries, preserving already-configured saves."""
    import services
    from sims.sim_info_types import Age, Species
    from mhs_save_as_copy import import_copy
    import mhs145_classroom_controller as controller
    household = services.active_household()
    manager = services.sim_info_manager()
    if household is None or manager is None:
        raise ValueError('HOUSEHOLD_OR_SIM_MANAGER_MISSING')
    played = tuple(str(info.sim_id) for info in household.sim_info_gen()
                   if getattr(info, 'age', None) == Age.TEEN and
                      getattr(info, 'species', None) == Species.HUMAN)
    # import_copy validates the complete roster, all five Core roles,
    # 16 actual EA teen SimInfos and every staff SimInfo, then uses
    # exclusive file creation. Different existing destination data
    # is NEVER silently replaced or destroyed.
    return import_copy(
        controller.FOLDER, source, destination, manager, Age.TEEN,
        Species.HUMAN, (Age.YOUNGADULT, Age.ADULT, Age.ELDER), played)


def _after_save(save_game_data, source):
    """An EA real save succeeded. Record its exact destination."""
    global _LAST_STATUS
    destination = _real_slot(save_game_data)
    if destination is None:
        _LAST_STATUS = 'SKIPPED_SCRATCH_OR_AUTOSAVE'
        return _LAST_STATUS
    if source is None:
        _LAST_STATUS = 'NO_VERIFIED_SOURCE_NO_DATA_CHANGE'
        return _LAST_STATUS

    origin, before_zone = source
    try:
        import services
        import mhs_m2_game_bridge as bridge
        from mhs56_slot_identity import save_name_token
        zone = services.current_zone()
        if zone is None or id(zone) != before_zone:
            _LAST_STATUS = 'ZONE_CHANGED_NO_COPY'
            return _LAST_STATUS
        persistence = services.get_persistence_service()
        getter = getattr(persistence, 'get_save_slot_proto_guid', None)
        guid = getter() if callable(getter) else None
        household = services.active_household()
        household_id = getattr(household, 'id', None)
        name = save_name_token(getattr(save_game_data, 'slot_name', None))
        if name is None:
            proto = persistence.get_save_slot_proto_buff()
            name = save_name_token(getattr(proto, 'slot_name', None))
        # The source was positively validated in the current zone before
        # EA's generator started. Validate it again after the save event.
        if not bridge._saved_roster_matches_live_game(origin):
            _LAST_STATUS = 'SOURCE_NO_LONGER_MATCHES_EA_SAVE'
            return _LAST_STATUS
        if str(origin) != destination:
            # Every Save As may be repeated. Use the *latest verified*
            # source (Copy 1 on the second Save As) rather than the first
            # original. If destination already has different MHS data,
            # fail closed without any overwrite.
            report = _copy_selected_school(origin, destination)
            if report['target'] != destination:
                raise ValueError('COPY_TARGET_MISMATCH')
            _LAST_STATUS = 'COPIED_{}_TO_{}'.format(origin,destination)
        else:
            _LAST_STATUS = 'SAVED_SAME_SLOT_{}'.format(destination)

        if not bridge._saved_roster_matches_live_game(destination):
            _LAST_STATUS = 'DESTINATION_REGISTRY_NOT_VERIFIED'
            return _LAST_STATUS
        # Anchor only after the exact destination's school is checked.
        # Save-title bindings are supplementary, never the authority.
        if not bridge._slot_cache().remember(destination,guid,household_id):
            _LAST_STATUS = 'SAVE_BINDING_NOT_WRITTEN'
            return _LAST_STATUS
        if name is not None:
            # Existing duplicate names are harmless once EA's real slot
            # is authoritative; the named fallback remains fail-closed.
            bridge._named_slot_cache().remember(
                destination,guid,name,household_id)
        bridge._SLOT_GUARD.resolve(destination,guid,household_id)
        bridge._LAST_BOUND = (
            destination,str(guid),str(household_id))
        bridge._LAST_SAVE_TITLE = name
        bridge._LAST_ZONE_TOKEN = id(zone)
        bridge._CACHED_RECOVERY = False
        bridge._COMMITTED_SAVE_ANCHOR = (
            destination, id(zone), str(guid), str(household_id))
        committed_status = _LAST_STATUS
        try:
            import mhs_classroom_bootstrap as bootstrap
            import mhs145_classroom_controller as controller
            current_zone, schedule = controller.zone_schedule()
            if (current_zone is not None and
                    schedule not in controller.SCHOOL_SCHEDULES):
                status = bootstrap.refresh(reload=True)
                if isinstance(status, str) and (
                        'BLOCKED' in status or 'BLOCCATA' in status):
                    committed_status += '_HOME_REFRESH_PENDING'
        except Exception:
            # Registry has been copied and identity committed; a failed
            # optional UI/controller refresh must never modify EA's save.
            committed_status += '_HOME_REFRESH_PENDING'
        _LAST_STATUS = committed_status
        return _LAST_STATUS
    except Exception as exc:
        _LAST_STATUS = 'SAVE_EVENT_FAILED_' + type(exc).__name__
        # Caller will still return the exact original EA save result.
        return _LAST_STATUS


def install(persistence_class=None):
    """Idempotently preserve EA save_game_gen's generator contract.

    Works in a wrapper chain when MCCC or Llamafone have already wrapped
    save_game_gen. Never wraps twice, never alters EA's save args/result.
    """
    global _INSTALLED, _HOOK, _LAST_STATUS
    try:
        if persistence_class is None:
            if _INSTALLED and _HOOK is not None:
                # A prior exact-class install succeeded. Later home refresh
                # must not replace its status or import the EA module again.
                return True
            from services.persistence_service import PersistenceService
            persistence_class = PersistenceService
        original = getattr(persistence_class,'save_game_gen',None)
        if not callable(original):
            _LAST_STATUS = 'SAVE_GENERATOR_UNAVAILABLE'
            return False
        if (getattr(original,'_mhs168_real_save_hook',False) or
                getattr(persistence_class,'_mhs168_save_hook_installed',False)):
            # Another mod may later chain its own wrapper around this one.
            # Avoid stacking a second MHS callback on the same generator.
            _INSTALLED = True
            return True

        def wrapped(self,timeline,save_game_data,*args,**kwargs):
            # Capture the source while this session's controller is still
            # connected to the *old* save before Save As commits.
            source = _snapshot_source()
            result = yield from original(
                self,timeline,save_game_data,*args,**kwargs)
            # A thrown EA error bypasses all MHS writes automatically.
            if result is not False:
                try:
                    _after_save(save_game_data,source)
                except Exception:
                    pass
            return result

        wrapped._mhs168_real_save_hook=True
        persistence_class.save_game_gen=wrapped
        persistence_class._mhs168_save_hook_installed=True
        _HOOK=(persistence_class,original,wrapped)
        _INSTALLED=True
        _LAST_STATUS='HOOK_INSTALLED'
        return True
    except Exception as exc:
        _LAST_STATUS='HOOK_INSTALL_FAILED_'+type(exc).__name__
        return False
