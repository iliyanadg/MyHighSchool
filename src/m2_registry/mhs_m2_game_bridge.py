"""M2 engine-facing helpers, NOT yet bound to the M1 picker confirmation.

Imports game modules lazily, so offline Python tests can load this module.
No patching of EA classes or interaction injection here.
"""
import os
from mhs_m2_roster import canonical_sim_id, RosterError
from mhs_m2_store import RosterStore, EnrollmentService


class BridgeError(RuntimeError):
    pass


def current_slot():
    """Read the active save ID; fail closed for temporary/unsaved games."""
    try:
        import services
        persistence = services.get_persistence_service()
        proto = persistence.get_save_slot_proto_buff() if persistence else None
        slot = getattr(proto, 'slot_id', None)
        from mhs_m2_roster import canonical_save_slot
        return canonical_save_slot(slot)
    except (ImportError, ValueError, TypeError, AttributeError):
        raise BridgeError('Salva prima la nuova partita: slot non identificabile')


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
