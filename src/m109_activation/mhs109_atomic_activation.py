"""M109 single activation transaction for M108 school-only hooks.

OFFLINE-ONLY integration contract. This file does not import Sims 4, call
a game service, or automatically install anything. In particular, it has
NO provider able to prove EA runtime facts in the current game. Never ship
this orchestrator as a playable M109 beta merely because synthetic tests pass.

An independently implemented live adapter will eventually supply a verified
plan and exactly seven named installers, each returning its own uninstall
callback. A failure rolls back in reverse order; a failed rollback is
reported and locks further attempts. The registry is never modified.
Python 3.7-compatible code, no global state and no auto-hooks on import.
"""
from mhs108_native_invitation import (
    CORE_JOBS, InvitationPlanError, prepare_fixed_manifest,
)

INSTALL_ORDER = (
    'native_base_count',
    'native_precreate',
    'school_filter_scope',
    'no_show_guard',
    'unified_lessons',
    'post_bouncer_observer',
)

REQUIRED_RUNTIME_EVIDENCE = (
    'ea_source_version_verified',
    'native_weekly_school_origin_verified',
    'before_ea_schedule_verified',
    'original_ea_school_count_verified',
    'native_job_tunings_verified',
    'original_bouncer_request_provenance_verified',
    'exact_school_student_and_staff_sim_infos_verified',
    'five_core_holds_prepared_before_schedule',
    'original_ea_guestlist_and_school_filters_verified',
    'no_show_fallback_paths_verified',
    'native_class1_shadow_compatibility_verified',
    'native_both_classroom_routes_verified',
    'post_bouncer_native_job_observer_verified',
    'npc_school_soft_cap_headroom_verified',
    'no_incompatible_school_controller_verified',
)

class ActivationError(RuntimeError):
    pass


def _canonical(manifest):
    if not isinstance(manifest, dict):
        return None
    try:
        plan = prepare_fixed_manifest(
            manifest['classes'], manifest['playable'],
            dict(manifest['core_assignments']),
            manifest['save_slot'], manifest['sim_day'],
            manifest['school_zone'])
        for key in ('classes', 'all_16', 'playable', 'core_assignments',
                    'base_ids', 'save_slot', 'sim_day', 'school_zone'):
            if manifest.get(key) != plan[key]:
                return None
        if (manifest.get('status') !=
                'M108_INVITATIONS_PREPARED_NOT_GAME_AUTHORIZED'
                or len(manifest['all_16']) != 16
                or len(set(manifest['all_16'])) != 16
                or len(manifest['playable']) != 3
                or len(manifest['base_ids']) != 8
                or len(manifest['core_assignments']) != 5
                or tuple(job for job, _ in manifest['core_assignments']) !=
                CORE_JOBS):
            return None
        return plan
    except (KeyError, TypeError, ValueError, InvitationPlanError):
        return None


def _evidence_valid(evidence, manifest):
    if not isinstance(evidence, dict):
        return False
    if (evidence.get('source') != 'EA_RUNTIME_OBSERVATION'
            or evidence.get('activation_authorized_by_game') is not True
            or evidence.get('before_ea_schedule_verified') is not True
            or str(evidence.get('save_slot')) != manifest['save_slot']
            or type(evidence.get('sim_day')) is not int
            or evidence['sim_day'] != manifest['sim_day']
            or str(evidence.get('school_zone')) != manifest['school_zone']
            or evidence.get('native_schedule_guid') not in (277657, 279958)
            or any(evidence.get(key) is not True
                   for key in REQUIRED_RUNTIME_EVIDENCE)):
        return False
    # The proof object is just a contract. The coordinator cannot itself
    # verify if EA *truly* produced it; no live provider exists yet.
    return True


class M109SchoolActivation(object):
    """Single-shot reversible installation; no automatic fallback to EA hacks.

    Stage installers are callables: installer(canonical_manifest, evidence)
    -> uninstall() callback. Hook owners are the individual M108 modules.
    A rollback failure is a hard stop: never arm a second time.
    """

    def __init__(self, manifest, preflight_provider, installers):
        self.manifest = _canonical(manifest)
        self.preflight_provider = preflight_provider
        self.installers = installers
        self.state = 'OFF'
        self.error = None
        self.active_stages = []
        self.rollback_errors = []
        self.events = []
        self._undos = []
        self._activation_key = None

    def _preflight(self):
        if self.manifest is None:
            return 'INVALID_ROSTER', None
        if not callable(self.preflight_provider):
            return 'NO_LIVE_PREFLIGHT_PROVIDER', None
        if (not isinstance(self.installers, dict)
                or set(self.installers) != set(INSTALL_ORDER)
                or not all(callable(self.installers[k])
                           for k in INSTALL_ORDER)):
            return 'INVALID_HOOK_GRAPH', None
        try:
            evidence = self.preflight_provider(self.manifest)
        except Exception as exc:
            return 'LIVE_PREFLIGHT_RAISED_' + type(exc).__name__, None
        if not _evidence_valid(evidence, self.manifest):
            return 'UNVERIFIED_EA_RUNTIME_EVIDENCE', None
        return None, evidence

    def arm(self):
        if self.state != 'OFF':
            return False
        self.state = 'PREFLIGHT'
        problem, evidence = self._preflight()
        if problem is not None:
            self.state = 'BLOCKED'
            self.error = problem
            self.events.append(('preflight', 'blocked', problem))
            return False

        # No hooks are active before ALL required evidence is checked.
        self.state = 'INSTALLING'
        self._activation_key = (
            self.manifest['save_slot'], self.manifest['sim_day'],
            self.manifest['school_zone'], evidence['native_schedule_guid'])
        for name in INSTALL_ORDER:
            try:
                uninstall = self.installers[name](self.manifest, evidence)
                if not callable(uninstall):
                    raise ActivationError('installer returned no uninstall')
                if any(uninstall is prior for _, prior in self._undos):
                    raise ActivationError('duplicate uninstall callback')
                self._undos.append((name, uninstall))
                self.active_stages.append(name)
                self.events.append((name, 'installed'))
            except Exception as exc:
                self.error = name + ': ' + type(exc).__name__
                self.events.append((name, 'failed', self.error))
                self._rollback()
                self.state = ('ROLLBACK_INCOMPLETE'
                              if self.rollback_errors else 'BLOCKED')
                return False
        self.state = 'ARMED'
        self.events.append(('activation', 'armed'))
        return True

    def _rollback(self):
        # On failure do not silently discard references to hooks whose
        # uninstall raised or returned False. They may still be installed.
        remaining = []
        for name, undo in reversed(self._undos):
            try:
                if undo() is not True:
                    raise ActivationError('uninstall did not confirm restore')
                self.events.append((name, 'restored'))
            except Exception as exc:
                self.rollback_errors.append(
                    name + ': ' + type(exc).__name__)
                self.events.append((name, 'rollback_failed'))
                remaining.append((name, undo))
        self._undos = list(reversed(remaining))
        self.active_stages = [name for name, _ in self._undos]

    def disarm(self):
        if self.state != 'ARMED':
            return False
        self.state = 'DISARMING'
        self._rollback()
        if self.rollback_errors:
            self.state = 'ROLLBACK_INCOMPLETE'
            self.error = 'HOOK_RESTORATION_INCOMPLETE'
            return False
        self.state = 'OFF'
        self.events.append(('activation', 'disarmed'))
        # Deliberately single-shot. Re-arm requires fresh M108 per-day
        # session, fresh EA facts and a NEW M109SchoolActivation instance.
        self.state = 'FINISHED'
        return True

    def snapshot(self):
        return {
            'kind': 'M109_OFFLINE_ATOMIC_HOOK_ACTIVATION',
            'state': self.state,
            'error': self.error,
            'active_stages': tuple(self.active_stages),
            'rollback_errors': tuple(self.rollback_errors),
            'activation_key': self._activation_key,
            'events': tuple(self.events),
            'ea_live_provider_implemented': False,
            'mod_installed_in_game': False,
            'attendance_16_verified': False,
            'classroom_seating_verified': False,
        }
