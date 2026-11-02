"""M108 original EA SituationManager post-zone-spin-up observer, disabled.

Verified from the user's EA script:
SituationManager.on_all_sims_spawned_during_zone_spin_up(self)
calls self._bouncer.assign_all_sims_during_zone_spin_up() and sets
self._sim_assignment_complete = True.

Only AFTER the ORIGINAL EA callback returns do we inspect already
registered school situation IDs through manager.get(situation_id) and
BaseSituation.all_sims_in_job_gen. No new request, no forced spawn.

This covers ONLY zone spin-up. Later school lesson changes require a
SEPARATE verified post-assignment barrier; do not claim full-day coverage.
No module in an installable Mac beta imports this observer.
"""
from mhs108_post_bouncer_audit import NativeJobAudit

REQUIRED_LIVE_GATES = (
    'original_ea_situation_manager_callback_verified',
    'school_zone_and_save_context_provider_verified',
    'native_bouncer_all_sims_assigned_callback_verified',
    'fixed_school_situations_are_registered_with_audit',
    'no_other_hook_stacking_verified',
)


def install_offline_only(manager_class, audit, context_provider, gates):
    """Patch EA post-spin-up callback ONCE and restore it on uninstall."""
    if (not isinstance(audit, NativeJobAudit)
            or not callable(context_provider)
            or not isinstance(gates, dict)
            or any(gates.get(name) is not True for name in REQUIRED_LIVE_GATES)):
        return None
    original = getattr(manager_class, 'on_all_sims_spawned_during_zone_spin_up',
                       None)
    if (not callable(original)
            or getattr(original, '_mhs108_post_bouncer', False)):
        return None
    observations = []
    barriers_read = set()

    def wrapped(self, *args, **kwargs):
        result = original(self, *args, **kwargs)
        # Preserve all native EA side effects and original return value.
        # The callback might run for non-school worlds or other saves.
        try:
            context = context_provider(self)
            if (not isinstance(context, dict)
                    or context.get('mhs_school_session_active') is not True
                    or context.get('verified_ea_school_origin') is not True
                    or context.get('post_bouncer_source_verified') is not True
                    or getattr(self, '_sim_assignment_complete', None) is not True
                    or str(context.get('save_slot')) != audit.manifest['save_slot']
                    or type(context.get('sim_day')) is not int
                    or context['sim_day'] != audit.manifest['sim_day']
                    or str(context.get('zone_id')) != audit.manifest['school_zone']):
                return result
            for situation_id, phase_key in audit.pending_phase_records():
                if (phase_key[0] != audit.manifest['save_slot']
                        or phase_key[1] != audit.manifest['sim_day']
                        or phase_key[2] != audit.manifest['school_zone']
                        or (situation_id, phase_key) in barriers_read):
                    continue
                # A real school late lesson may not have completed yet;
                # this callback is ONLY the spin-up assignment barrier.
                event = {
                    'ea_bouncer_assignment_completed': True,
                    'post_bouncer_source_verified': True,
                    'phase_key': phase_key,
                    'situation_id': situation_id,
                }
                observed = audit.observe(situation_id, self, event)
                observations.append((situation_id, observed['status']))
                barriers_read.add((situation_id, phase_key))
        except Exception:
            # Observer never changes, re-runs, or prevents EA callback.
            observations.append((None, 'OBSERVER_CONTEXT_READ_FAILED'))
        return result

    wrapped._mhs108_post_bouncer = True
    manager_class.on_all_sims_spawned_during_zone_spin_up = wrapped

    def uninstall():
        if (manager_class.on_all_sims_spawned_during_zone_spin_up
                is not wrapped):
            return False
        manager_class.on_all_sims_spawned_during_zone_spin_up = original
        return True

    uninstall.observations = observations
    return uninstall
