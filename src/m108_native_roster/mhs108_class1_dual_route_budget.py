"""M108 — class-one exact NPC capacity across BOTH original EA routes.

NOT a game hook. The REAL EA WeeklyScheduleSituationData.try_start method
reduces each job upper bound using previously assigned jobs:
  Class1 WithTrait: player phase NPC job 278117
  Class1 NoTrait:  player phase + earlier Class1 WithTrait job 277919.

The player-phase modifier counts players across EA school phases; it is NOT
guaranteed to count just the playable Sims in MHS Class 1. Therefore blindly
changing tuned upper_bound 6 -> 8 can still cause a shortfall. Compute a
separate per-branch proposal against *observed* native job counts, and the
MHS fixed 8-person classroom allocation.

Both routes remain unmodified EA eligibility tests. No trait assignment.
No changes to shared EA tuning or situation sets, no Sim spawning.
"""

from mhs108_native_invitation import prepare_fixed_manifest, InvitationPlanError

STUDENT_JOB = 277919
EA_PLAYER_JOB = 278117
EA_ORIGINAL_CLASS1_UPPER = 6
SCHEDULES = frozenset((277657, 279958))
PHASES = {
    'prepare': {
        'with_trait_data': 293642,
        'no_trait_data': 293644,
        'with_trait_situation': 293815,
        'no_trait_situation': 304701,
        'player_situation': 284555,
        'clocks': ('09:30', '13:30'),
    },
    'lesson': {
        'with_trait_data': 304563,
        'no_trait_data': 304561,
        'with_trait_situation': 304565,
        'no_trait_situation': 304703,
        'player_situation': 276681,
        'clocks': ('10:00', '14:00'),
    },
}


def _ids(values):
    if type(values) not in (tuple, list, set, frozenset):
        return None
    result = []
    for raw in values:
        if type(raw) not in (str, int) or not str(raw).isdigit():
            return None
        val = str(int(raw))
        if val != str(raw) or int(raw) <= 0:
            return None
        result.append(val)
    return frozenset(result) if len(result) == len(set(result)) else None


def _canonical(manifest):
    if not isinstance(manifest, dict):
        return None
    try:
        canonical = prepare_fixed_manifest(
            manifest['classes'], manifest['playable'],
            dict(manifest['core_assignments']),
            manifest['save_slot'], manifest['sim_day'],
            manifest['school_zone'])
        if any(manifest.get(key) != canonical[key]
               for key in ('classes', 'playable', 'all_16', 'base_ids',
                           'core_assignments', 'save_slot', 'sim_day',
                           'school_zone')):
            return None
        return canonical
    except (KeyError, ValueError, TypeError, InvitationPlanError):
        return None


class ClassOneDualRouteBudget(object):
    """One class, one EA phase clock, two native routes.

    A new instance is required for each 09:30, 10:00, 13:30, 14:00
    transition. For a failed/partial native result, permanently block
    this coordinator rather than filling a seat with another Sim.
    """

    def __init__(self, manifest, phase, context):
        self.manifest = _canonical(manifest)
        if self.manifest is None or phase not in PHASES:
            raise ValueError('invalid official M108 roster or EA phase')
        self.phase = phase
        self.tuning = PHASES[phase]
        self.context = dict(context) if isinstance(context, dict) else {}
        m = self.manifest
        if (self.context.get('native_school_phase_origin_verified') is not True
                or self.context.get('school_verified') is not True
                or self.context.get('schedule_guid') not in SCHEDULES
                or str(self.context.get('save_slot')) != m['save_slot']
                or type(self.context.get('sim_day')) is not int
                or self.context['sim_day'] != m['sim_day']
                or str(self.context.get('zone_id')) != m['school_zone']
                or self.context.get('time_window') not in
                self.tuning['clocks']
                or self.context.get('original_ea_player_jobs_verified')
                is not True
                or self.context.get('original_ea_school_members_verified')
                is not True):
            raise ValueError('not a verified original EA school phase')
        observed_school = _ids(self.context.get('observed_ea_school_ids'))
        on_lot = _ids(self.context.get('observed_on_lot_ids'))
        selected_playable = _ids(self.context.get('observed_player_phase_ids'))
        if (observed_school != frozenset(m['all_16'])
                or on_lot is None
                or not set(m['all_16']) <= on_lot
                or selected_playable != frozenset(m['playable'])):
            raise ValueError('all 16 enrolled and 3 active school players required')

        self.expected = frozenset(
            sid for sid in m['classes'][0]
            if sid not in set(m['playable']))
        self.playable_in_class = frozenset(
            sid for sid in m['classes'][0] if sid in set(m['playable']))
        self.player_count = len(selected_playable)
        self.native_remaining = set(self.expected)
        self.assigned = {'with_trait': set(), 'no_trait': set()}
        self.done = set()
        self.pending = None
        self.blocked = False
        self.block_reason = ''
        self._situation_ids = set()

    def _route(self, data_guid):
        if type(data_guid) is not int:
            return None
        if data_guid == self.tuning['with_trait_data']:
            return 'with_trait'
        if data_guid == self.tuning['no_trait_data']:
            return 'no_trait'
        return None

    def prepare(self, data_guid, original_native_job_counts,
                native_eligible_ids, tested_context):
        """Prepare a per-call cap and exact set of eligible student IDs.

        original_native_job_counts must contain the measured EA job counts
        for current player phase and prior WithTrait assignments. Does not
        mutate its argument or promise EA accepted the result.

        A route may validly have ZERO candidates (e.g. no selected Sim
        has Class1 hidden trait). The other route can still seat the
        exact same registered children with no trait modification.
        """
        route = self._route(data_guid)
        if self.blocked or self.pending is not None or route is None:
            return None
        if route in self.done:
            return None
        if not isinstance(tested_context, dict) or (
                tested_context.get('ea_job_counts_verified') is not True
                or tested_context.get('ea_route_test_results_verified')
                is not True
                or tested_context.get('native_school_phase_origin_verified')
                is not True
                or str(tested_context.get('save_slot')) !=
                self.manifest['save_slot']
                or tested_context.get('sim_day') !=
                self.manifest['sim_day']
                or str(tested_context.get('zone_id')) !=
                self.manifest['school_zone']
                or tested_context.get('time_window') !=
                self.context['time_window']):
            return None
        eligible = _ids(native_eligible_ids)
        if eligible is None or not isinstance(original_native_job_counts, dict):
            return None
        counts = original_native_job_counts
        player_key = (self.tuning['player_situation'], EA_PLAYER_JOB)
        with_key = (self.tuning['with_trait_situation'], STUDENT_JOB)
        player_count = counts.get(player_key)
        with_count = counts.get(with_key, 0)
        if (type(player_count) is not int or
                player_count != self.player_count or
                type(with_count) is not int or
                with_count != len(self.assigned['with_trait'])):
            return None
        # IMPORTANT: the native WithTrait eligibility test decides
        # eligibility, not the student's MHS class or a guessed trait.
        available = frozenset(self.native_remaining)
        candidates = tuple(
            sid for sid in self.manifest['classes'][0]
            if sid in available and sid in eligible and
            sid not in self.playable_in_class)
        if (len(candidates) > len(self.expected) or
                len(self.expected) + len(self.playable_in_class) != 8):
            return None
        native_prior_modifiers = (
            player_count + (with_count if route == 'no_trait' else 0))
        proposed_tuning_upper = native_prior_modifiers + len(candidates)
        original_effective_upper = max(
            0, EA_ORIGINAL_CLASS1_UPPER - native_prior_modifiers)
        # The proposed original EA job's effective upper must equal
        # precisely the number of this route's remaining candidates.
        if (proposed_tuning_upper > 11 or
                proposed_tuning_upper - native_prior_modifiers !=
                len(candidates)):
            return None
        ticket = {
            'route': route,
            'phase': self.phase,
            'data_guid': data_guid,
            'native_situation': self.tuning[
                'with_trait_situation' if route == 'with_trait'
                else 'no_trait_situation'],
            'native_student_job': STUDENT_JOB,
            'registered_class1_npcs_remaining_before': len(available),
            'playables_in_class1': len(self.playable_in_class),
            'playables_in_global_ea_phase': player_count,
            'native_already_in_with_trait': with_count,
            'exact_candidate_ids': candidates,
            'native_original_tuned_upper': EA_ORIGINAL_CLASS1_UPPER,
            'native_original_effective_upper': original_effective_upper,
            'proposed_per_call_tuned_upper': proposed_tuning_upper,
            'proposed_effective_upper': len(candidates),
            'changes_to_ea_tuning': False,
            'native_phase_assignments_verified': False,
        }
        self.pending = ticket
        return dict(ticket)

    def confirm(self, ticket, actually_assigned_ids, created_situation_id):
        """Count only exact, verified EA results; never infer from a plan."""
        if self.blocked or self.pending is None or ticket != self.pending:
            return False
        route = self.pending['route']
        expected = frozenset(self.pending['exact_candidate_ids'])
        actual = _ids(actually_assigned_ids)
        if (actual is None or actual != expected or
                actual & (self.assigned['with_trait'] |
                          self.assigned['no_trait'])):
            self.blocked = True
            self.block_reason = 'native result not exact registered students'
            self.pending = None
            return False
        if expected:
            if (type(created_situation_id) is not int or
                    created_situation_id <= 0 or
                    created_situation_id in self._situation_ids):
                self.blocked = True
                self.block_reason = 'missing/duplicate native EA situation receipt'
                self.pending = None
                return False
            self._situation_ids.add(created_situation_id)
        elif created_situation_id is not None:
            self.blocked = True
            self.block_reason = 'native EA created an unrequested empty class phase'
            self.pending = None
            return False
        self.assigned[route].update(actual)
        self.native_remaining.difference_update(actual)
        self.done.add(route)
        self.pending = None
        return True

    def cancel(self, ticket):
        """A failed real EA phase must not trigger another random attempt."""
        if self.pending is None or ticket != self.pending:
            return False
        self.pending = None
        self.blocked = True
        self.block_reason = 'native original did not assign required class1 seats'
        return True

    def snapshot(self):
        assigned = self.assigned['with_trait'] | self.assigned['no_trait']
        complete = (
            not self.blocked and self.pending is None
            and self.done == {'with_trait', 'no_trait'}
            and assigned == self.expected)
        return {
            'kind': 'M108_CLASS_ONE_TWO_EA_ROUTES_OFFLINE',
            'phase': self.phase,
            'school_time': self.context['time_window'],
            'exact_npc_required': len(self.expected),
            'playable_class1_count': len(self.playable_in_class),
            'ea_player_phase_total': self.player_count,
            'with_trait_assigned_ids': tuple(sorted(self.assigned['with_trait'])),
            'no_trait_assigned_ids': tuple(sorted(self.assigned['no_trait'])),
            'missing_registered_npc_ids': tuple(sorted(self.native_remaining)),
            'phase_plan_complete_offline': complete,
            'blocked': self.blocked,
            'reason': self.block_reason,
            'actual_ea_bouncer_acceptance_verified': False,
            'actual_ea_classroom_seating_verified': False,
        }
