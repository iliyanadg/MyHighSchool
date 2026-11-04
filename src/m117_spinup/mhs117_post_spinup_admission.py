"""M117: one original EA post-spinup callback -> exact M116 guest job audit.

This is an OFFLINE integration adapter. No Sims imports, no auto-hooks.
The original SituationManager callback executes EXACTLY ONCE, before
the readback. Only the same live manager instance, school zone/save/day,
and a session containing the nine original EA creation receipts can be
audited. A M116 success is a zone-spinup job snapshot, NOT a verified
late-lesson Bouncer event, full day or seated classroom.

Do not bundle in an installable controller until an independently
verified live context provider supplies the immutable origin and
preflight. Installation gates are synthetic ONLY in unit tests.
"""
from mhs108_native_invitation import SchoolNativeGuestSession
from mhs116_native_guest_job_readback import inspect_created_native_guest_jobs

OWNER = 'situations.situation_manager.SituationManager'
CALLBACK = 'on_all_sims_spawned_during_zone_spin_up'
PROOF_KEYS = (
    'original_ea_situation_manager_callback_verified',
    'callback_owner_and_zone_provenance_verified',
    'save_day_school_manifest_from_live_registry_verified',
    'nine_original_ea_guest_receipts_source_verified',
    'no_other_school_controller_hooks_verified',
)


def _school_context(context, manifest, manager):
    if type(context) is not dict:
        return False
    return (
        context.get('source') == 'EA_RUNTIME_OBSERVATION'
        and context.get('original_ea_school_spinup_callback') is True
        and context.get('active_school_lot_verified') is True
        and context.get('manager_identity') is manager
        and str(context.get('save_slot')) == manifest['save_slot']
        and type(context.get('sim_day')) is int
        and context.get('sim_day') == manifest['sim_day']
        and str(context.get('zone_id')) == manifest['school_zone']
        and context.get('schedule_guid') in (277657, 279958)
    )


class M117PostSpinupAdmission(object):
    def __init__(self, session, context_provider):
        self.session = session
        self.context_provider = context_provider
        self._owner = None
        self._original = None
        self._wrapper = None
        self._manager_ids = set()
        self.observations = []
        self.state = 'NOT_INSTALLED'

    def install(self, owner, proof):
        if (self.state != 'NOT_INSTALLED'
                or not isinstance(self.session, SchoolNativeGuestSession)
                or not callable(self.context_provider)
                or not isinstance(owner, type)
                or owner.__module__ + '.' + owner.__name__ != OWNER
                or type(proof) is not dict
                or any(proof.get(key) is not True for key in PROOF_KEYS)):
            return False
        raw = owner.__dict__.get(CALLBACK)
        if (not callable(raw) or getattr(raw, '_mhs108_post_bouncer', False)
                or getattr(raw, '_mhs117_post_spinup', False)):
            return False
        self._owner = owner
        self._original = raw

        def observed(manager, *args, **kwargs):
            # Preserve original EA behaviour, result and exceptions.
            result = raw(manager, *args, **kwargs)
            if self.state != 'OBSERVING':
                return result
            try:
                # Do NOT trust an earlier state flag in another manager.
                context = self.context_provider(manager)
                if not _school_context(context, self.session.manifest, manager):
                    return result
                if getattr(manager, '_sim_assignment_complete', None) is not True:
                    self.observations.append({
                        'status': 'ORIGINAL_EA_SPINUP_FLAG_NOT_SET',
                        'native_guest_jobs_13_verified_in_snapshot': False,
                        'post_bouncer_callback_provenance_verified': False,
                    })
                    return result
                # One school spinup snapshot per manager instance.
                identity = id(manager)
                if identity in self._manager_ids:
                    return result
                self._manager_ids.add(identity)
                report = inspect_created_native_guest_jobs(self.session, manager)
                # This flag describes the original callback invocation
                # provenance only, not a late classroom job barrier.
                report['post_bouncer_callback_provenance_verified'] = True
                report['post_bouncer_provenance_scope'] = (
                    'ORIGINAL_EA_ZONE_SPINUP_ONLY')
                report['native_ea_callback_return_preserved'] = True
                self.observations.append(report)
            except Exception as exc:
                self.observations.append({
                    'status': 'READ_ONLY_POST_SPINUP_AUDIT_EXCEPTION',
                    'error_type': type(exc).__name__,
                    'native_guest_jobs_13_verified_in_snapshot': False,
                    'post_bouncer_callback_provenance_verified': False,
                })
            return result

        observed._mhs108_post_bouncer = True
        observed._mhs117_post_spinup = True
        self._wrapper = observed
        owner.on_all_sims_spawned_during_zone_spin_up = observed
        self.state = 'OBSERVING'
        return True

    def restore(self):
        if self.state == 'NOT_INSTALLED':
            return True
        if self.state != 'OBSERVING':
            return False
        if self._owner.__dict__.get(CALLBACK) is not self._wrapper:
            self.state = 'RESTORE_CONFLICT'
            return False
        self._owner.on_all_sims_spawned_during_zone_spin_up = self._original
        self.state = 'RESTORED'
        return True

    def stage(self, owner, proof):
        """Provide stage compatible with M109/M113 rollback ordering."""
        return {
            'install': lambda manifest, context: (
                manifest == self.session.manifest and self.install(owner, proof)),
            'restore': self.restore,
        }

    def snapshot(self):
        return {
            'kind': 'M117_POST_SPINUP_13_NATIVE_NPC_AUDIT_OFFLINE',
            'status': self.state,
            'reports': len(self.observations),
            'native_original_ea_spinup_callback_invoked': (
                bool(self.observations)),
            'late_lessons_verified': False,
            'three_playable_attendance_verified': False,
            'full_school_day_verified': False,
            'two_classroom_seating_verified': False,
        }
