"""M105: school-wide roster solution, no Sims runtime or game mutations."""
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for sub in ('m105_day_controller','m97_core_reservations','m93_core','m92_full_roster','m96_scheduler'):
    sys.path.insert(0,str(ROOT/'src'/sub))
from mhs105_atomic_school_roster import (
    plan_school_day,BASE_JOB,CORE_JOBS,ALL_JOBS)
from mhs97_early_role_plan import early_role_plan
from mhs92_atomic_16 import full_cohort_plan
from mhs96_exact_school_count import approved_base_count
from types import SimpleNamespace

CLASSES=(tuple(str(n) for n in range(1,9)),
         tuple(str(n) for n in range(9,17)))
PLAYED=('1','9','10')
NPCS=tuple(s for group in CLASSES for s in group if s not in PLAYED)
PINS=dict(zip(CORE_JOBS,('2','3','4','11','12')))

def live_filters():
    filters={job:tuple(NPCS) for job in ALL_JOBS}
    # One enrolled NPC failed EA's ordinary Base filter in the user's
    # recent Mac pilot. This example models that case; it does NOT
    # claim the actual excluded Sim ID was known.
    filters[BASE_JOB]=tuple(s for s in NPCS if s!='2')
    return filters

class FullDayEAAllocationTests(unittest.TestCase):
    def test_manual_five_core_plus_three_playable_plus_eight_base(self):
        result=plan_school_day(CLASSES,PLAYED,live_filters(),PINS)
        self.assertEqual(result['status'],'PREPARED_NOT_EA_BOUND')
        self.assertEqual(result['base_invites_needed'],8)
        self.assertEqual(result['playable_count'],3)
        self.assertEqual(result['core_count'],5)
        self.assertEqual(dict(result['core_role_assignments']),PINS)
        self.assertEqual(set(result['normal_base_ids']),
                         set(NPCS)-set(PINS.values()))
        self.assertEqual(result['base_ineligible_in_core'],1)
        self.assertFalse(result['core_roles_reserved_before_ea'])
        self.assertFalse(result['actual_ea_role_bindings_verified'])
        self.assertFalse(result['attendance_verified'])
        self.assertFalse(result['changes_to_ea'])

    def test_without_five_manual_appointments_normal_operation_blocks(self):
        result=plan_school_day(CLASSES,PLAYED,live_filters(),{})
        self.assertEqual(result['status'],'BLOCKED')
        self.assertEqual(result['assigned_core_roles'],0)
        self.assertIn('manual',result['reason'])

    def test_opt_in_suggestion_is_never_mistaken_for_actual_ea_assignment(self):
        result=plan_school_day(CLASSES,PLAYED,live_filters(),
                               propose_missing_roles=True)
        self.assertEqual(result['status'],'PROPOSAL_NEEDS_MANUAL_CONFIRMATION')
        self.assertEqual(result['base_invites_needed'],8)
        self.assertIn('2',dict(result['core_role_assignments']).values())
        self.assertNotIn('2',result['normal_base_ids'])
        self.assertFalse(result['all_core_appointments_confirmed'])
        self.assertFalse(result['core_roles_reserved_before_ea'])

    def test_suggestions_deterministic_under_filter_result_order(self):
        a=live_filters()
        b={key:tuple(reversed(items)) for key,items in a.items()}
        first=plan_school_day(CLASSES,PLAYED,a,propose_missing_roles=True)
        second=plan_school_day(CLASSES,PLAYED,b,propose_missing_roles=True)
        self.assertEqual(first['core_role_assignments'],
                         second['core_role_assignments'])
        self.assertEqual(first['normal_base_ids'],
                         second['normal_base_ids'])

    def test_pin_requires_actual_role_eligibility(self):
        filt=live_filters()
        filt[CORE_JOBS[0]]=tuple(s for s in NPCS if s!='2')
        result=plan_school_day(CLASSES,PLAYED,filt,PINS)
        self.assertEqual(result['status'],'BLOCKED')
        self.assertIn('not eligible',result['reason'])

    def test_pins_must_be_unique_nonplayable_and_enrolled(self):
        duplicate=dict(PINS);duplicate[CORE_JOBS[1]]='2'
        self.assertEqual(plan_school_day(
            CLASSES,PLAYED,live_filters(),duplicate)['status'],'BLOCKED')
        playable=dict(PINS);playable[CORE_JOBS[0]]='1'
        self.assertEqual(plan_school_day(
            CLASSES,PLAYED,live_filters(),playable)['status'],'BLOCKED')
        outsider=dict(PINS);outsider[CORE_JOBS[0]]='99'
        self.assertEqual(plan_school_day(
            CLASSES,PLAYED,live_filters(),outsider)['status'],'BLOCKED')

    def test_block_if_fewer_than_eight_base_eligible(self):
        filt=live_filters()
        filt[BASE_JOB]=tuple(NPCS[:7])
        result=plan_school_day(CLASSES,PLAYED,filt,PINS)
        self.assertEqual(result['status'],'BLOCKED')
        self.assertEqual(result['base_ineligible_count'],6)

    def test_no_five_role_matching_when_repeated_only_candidate(self):
        filt=live_filters()
        for job in CORE_JOBS:
            filt[job]=('2',)
        result=plan_school_day(CLASSES,PLAYED,filt,
                               propose_missing_roles=True)
        self.assertEqual(result['status'],'BLOCKED')
        self.assertIn('collision-free',result['reason'])

    def test_all_six_filter_results_are_mandatory(self):
        filt=live_filters()
        del filt[CORE_JOBS[-1]]
        self.assertEqual(plan_school_day(
            CLASSES,PLAYED,filt,PINS)['status'],'BLOCKED')
        filt=live_filters()
        filt[BASE_JOB]=None
        self.assertEqual(plan_school_day(
            CLASSES,PLAYED,filt,PINS)['status'],'BLOCKED')

    def test_invalid_exact_enrollment_or_playable_is_blocked(self):
        filt=live_filters()
        cases=(
            (CLASSES[0],CLASSES[1][:-1]),
            (CLASSES[0],CLASSES[0]),
        )
        for classes in cases:
            self.assertEqual(plan_school_day(
                classes,PLAYED,filt,PINS)['status'],'BLOCKED')
        self.assertEqual(plan_school_day(
            CLASSES,('1','9','99'),filt,PINS)['status'],'BLOCKED')
        self.assertEqual(plan_school_day(
            CLASSES,('1','9','9'),filt,PINS)['status'],'BLOCKED')

    def test_handoff_to_existing_m97_m92_m96_gates(self):
        plan=plan_school_day(CLASSES,PLAYED,live_filters(),PINS)
        self.assertEqual(plan['status'],'PREPARED_NOT_EA_BOUND')
        core=dict(plan['core_role_assignments'])
        # M97 also validates all five real job-specific eligibility sets
        # and documents that the result has NOT been applied to EA yet.
        role_plan=early_role_plan(
            CLASSES,PLAYED,core,
            {job:live_filters()[job] for job in CORE_JOBS})
        self.assertEqual(role_plan['status'],
                         'EARLY_ROLE_PLAN_VALIDATED_NOT_EA_BOUND')
        self.assertEqual(tuple(role_plan['normal_npcs']),
                         plan['normal_base_ids'])
        manifest=SimpleNamespace(class_ids=CLASSES,
             all_student_ids=frozenset(CLASSES[0]+CLASSES[1]),
             active_household_teens=frozenset(PLAYED))
        full=full_cohort_plan(
            manifest,plan['normal_base_ids'],PLAYED,
            tuple(core.values()),base_job_slots=8,phase1_slots=8,
            phase2_slots=8,zone_cap_free_or_reserved=16,
            ea_filters_verified=True,core_role_jobs=core)
        self.assertEqual(full['status'],'READY_FOR_ADAPTER')
        self.assertEqual(full['base_invites_needed'],8)
        # The count hook REJECTS hypothetical capacity and unbound
        # pre-school reservations. Do not turn it on until truly bound.
        self.assertIsNone(approved_base_count(277657,277733,full))

    def test_does_not_mutate_input_roles_or_filter_lists(self):
        pins=dict(PINS)
        filt=live_filters()
        snapshot=dict(filt)
        result=plan_school_day(CLASSES,PLAYED,filt,pins)
        self.assertEqual(result['status'],'PREPARED_NOT_EA_BOUND')
        self.assertEqual(pins,PINS)
        self.assertEqual(filt,snapshot)

if __name__=='__main__':
    unittest.main()
