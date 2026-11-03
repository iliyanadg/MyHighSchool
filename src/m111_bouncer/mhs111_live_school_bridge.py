"""M111: runtime handoff from the real M54/M57 registry to EA job readback.

No command, no automatic import into the game, no hooking. The function
obtains a fresh save slot, MHS roster and staff from the EXISTING per-save
stores, and reads the current zone's actual EA high-school schedule.
Only then it calls M111's pure EA membership reader. It cannot certify
a Bouncer post-assignment barrier or classroom seating.
"""
import os
from mhs111_school_job_readback import observe_school_job_memberships

SCHOOL_SCHEDULES = frozenset((277657, 279958))


def _blocked(status, **details):
    data = {
        'kind': 'M111_LIVE_SCHOOL_JOB_BRIDGE_READ_ONLY',
        'status': status,
        'game_modified': False,
        'post_bouncer_barrier_verified': False,
        'exact_16_native_membership_verified': False,
        'two_classroom_seating_verified': False,
        'full_school_day_verified': False,
    }
    data.update(details)
    return data


def inspect_current_school_ea_jobs(phase):
    """Read-only diagnostic callable by a future MHS game command.

    Phase must be explicit: a live read does not infer lesson start from
    the clock. No source with only a planned roster can set a job match.
    """
    if phase not in ('prepare', 'lesson'):
        return _blocked('PHASE_NOT_SPECIFIED')
    try:
        import services
        from sims.sim_info_types import Age, Species
        from mhs_m2_game_bridge import current_slot
        from mhs_m2_store import RosterStore
        from mhs53_staff_store import StaffStore
        from mhs34_settings import SettingsStore
        from mhs57_school_manifest import make_manifest

        # Same directory M57's live filter bridge already uses.
        directory = os.path.join(
            os.path.expanduser('~'), 'Documents', 'Electronic Arts',
            'The Sims 4', 'MY_HIGH_SCHOOL_M25_TEST_DATA')
        slot = str(current_slot(allow_travel=True))
        settings = SettingsStore(directory).load(slot)
        if not settings.active:
            return _blocked('MY_HIGH_SCHOOL_NOT_ACTIVE')
        if settings.class_count != 2:
            return _blocked('EXACTLY_TWO_CLASSES_REQUIRED')
        roster = RosterStore(directory).load(slot)
        staff = StaffStore(directory).load(slot)
        household = services.active_household()
        if household is None:
            return _blocked('NO_ACTIVE_HOUSEHOLD')
        active_teens = []
        for info in tuple(household.sim_info_gen()):
            if (getattr(info, 'age', None) == Age.TEEN
                    and getattr(info, 'species', None) == Species.HUMAN):
                active_teens.append(info.sim_id)
        manifest = make_manifest(roster, staff, 2, tuple(active_teens))
        if (manifest.slot != slot
                or manifest.selected_count != 16
                or any(len(c) != 8 for c in manifest.class_ids)):
            return _blocked('REGISTER_IS_NOT_COMPLETE_TWO_BY_EIGHT')

        zone = services.current_zone()
        zone_id = getattr(zone, 'id', None)
        if type(zone_id) is not int or zone_id <= 0:
            return _blocked('EA_CURRENT_ZONE_UNAVAILABLE')
        venue = services.venue_service()
        if venue is None:
            return _blocked('EA_VENUE_SERVICE_UNAVAILABLE')
        director = venue.get_zone_director()
        schedule = getattr(director, '_schedule', None)
        schedule_guid = getattr(schedule, 'guid64', None)
        if (type(schedule_guid) is not int
                or schedule_guid not in SCHOOL_SCHEDULES):
            return _blocked('NOT_ORIGINAL_EA_HIGH_SCHOOL_SCHEDULE')
        manager = services.get_zone_situation_manager()
        info_manager = services.sim_info_manager()
        if info_manager is None or manager is None:
            return _blocked('EA_SITUATION_OR_SIM_SERVICE_MISSING')
        result = observe_school_job_memberships(
            manifest, manager, info_manager.get_all(),
            Age.TEEN, Species.HUMAN, phase)
        result['source'] = 'EA_CURRENT_ZONE_AND_SAVE_SCOPED_MHS_MANIFEST'
        result['zone_id'] = str(zone_id)
        result['school_schedule_guid'] = schedule_guid
        result['roster_slot_verified'] = True
        result['ea_school_schedule_observed'] = True
        # Native EA writes this flag after its original *zone-spinup*
        # Bouncer assignment. Read only; it is NOT a verified callback
        # receipt for the subsequent 10:00 / 14:00 classroom assignments.
        value = getattr(manager, '_sim_assignment_complete', None)
        result['zone_spinup_assignment_flag_observed'] = value is True
        result['zone_spinup_assignment_flag_known'] = type(value) is bool
        # Sim instance is a live game object; neither this boolean nor
        # a job snapshot attests actual late Bouncer completion.
        result['post_bouncer_barrier_verified'] = False
        result['full_school_day_verified'] = False
        return result
    except Exception as exc:
        return _blocked('LIVE_EA_JOB_READ_FAILED',
                        error_type=type(exc).__name__)
