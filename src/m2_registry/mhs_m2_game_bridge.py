"""M2 engine-facing helpers, NOT yet bound to the M1 picker confirmation.

Imports game modules lazily, so offline Python tests can load this module.
No patching of EA classes or interaction injection here.
"""
import os
from mhs_m2_roster import canonical_sim_id, RosterError
from mhs_m2_store import RosterStore, EnrollmentService


class BridgeError(RuntimeError):
    pass


from mhs56_slot_identity import TravelSlotGuard, IdentityError, positive_slot

_SLOT_GUARD = TravelSlotGuard()


def current_slot(allow_travel=False):
    """Resolve a verified per-save slot; scratch fallback is READ-ONLY.

    EA persistence.get_save_slot_proto_guid() remains stable through scratch
    travel (the same source used by Lot51 Core Context.save_slot_id).
    We bind this stable identifier to the last REAL slot observed in the
    SAME session and household. The stable GUID is NOT treated as a slot
    number. Only read-only menu and transient school attendance may pass
    allow_travel=True. Enrollment/staff/settings writes keep the strict gate.
    """
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
        verified_home_write = False
        # EA can expose its temporary travel slot even after reaching HOME.
        # Only a currently running and previously verified HOME controller
        # may reuse its exact bound identity for a menu write.
        if not allow_travel and positive_slot(slot) is None:
            try:
                import mhs145_classroom_controller as controller
                runtime = controller._RUNTIME
                zone, schedule = controller.zone_schedule()
                verified_home_write = bool(
                    zone is not None and
                    schedule not in controller.SCHOOL_SCHEDULES and
                    runtime is not None and runtime.active and
                    not runtime.in_school() and
                    runtime.slot == _SLOT_GUARD.slot)
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
