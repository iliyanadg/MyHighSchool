"""M106 pure roster-first school planning tests (Python 3.7, no Sims runtime)."""
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'/'m105_day_controller'))
sys.path.insert(0,str(ROOT/'src'/'m106_roster_first'))

from mhs106_roster_first_policy import propose_roster_first,CORE_ORDER
from mhs105_atomic_school_roster import BASE_JOB

CLASSES=(tuple(str(x) for x in range(1,9)),
         tuple(str(x) for x in range(9,17)))
PLAYABLE=('1','9','10')
ALL=CLASSES[0]+CLASSES[1]
NPC=tuple(sid for sid in ALL if sid not in PLAYABLE)


def real_ea_results(cheer=('2','16')):
    # Twelve of thirteen are genuinely Base-eligible (as in the live report).
    # The other must occupy a genuine Core role or the roster cannot fit.
    return {
        BASE_JOB:tuple(sid for sid in NPC if sid!='16'),
        278965:cheer,
        278966:('3',),
        278967:('4',),
        278968:('11',),
        303765:(),   # Live M105 reported NO registered Mean-Sim candidate.
    }


class RosterFirstPolicyTests(unittest.TestCase):
    def test_fixed_sixteen_survive_absent_original_mean_candidate(self):
        proposed=propose_roster_first(
            CLASSES,PLAYABLE,real_ea_results(),
            {278965:'2',278966:'3',278967:'4',
             278968:'11',303765:'12'})
        self.assertEqual(proposed['status'],
                         'BRIDGE_CANDIDATE_ONLY_NOT_EA_BOUND')
        self.assertEqual(proposed['all_16'],ALL)
        self.assertEqual(proposed['classes'],CLASSES)
        self.assertEqual(tuple(len(c) for c in CLASSES),(8,8))
        self.assertEqual(proposed['playable_count'],3)
        self.assertEqual(proposed['core_count'],5)
        self.assertEqual(proposed['base_count'],8)
        assigned=dict(proposed['core_role_assignments'])
        self.assertEqual(assigned[278965],'16') # non-Base teen must take Core
        self.assertEqual(assigned[303765],'12') # no outsider is introduced
        self.assertEqual(proposed['school_only_bridge_candidates'],
                         ((303765,'12'),))
        self.assertEqual(len(set(assigned.values())),5)
        self.assertEqual(
            set(PLAYABLE)|set(assigned.values())|set(proposed['normal_base_ids']),
            set(ALL))
        for flag in ('roster_mutated','traits_mutated',
                     'ea_school_filter_changed','ea_job_binding_verified',
                     'school_capacity_verified','classroom_routing_verified',
                     'attendance_verified','adapter_authorized'):
            self.assertFalse(proposed[flag])

    def test_no_external_wolfgang_even_if_mean_filter_empty(self):
        plan=propose_roster_first(CLASSES,PLAYABLE,real_ea_results())
        self.assertEqual(plan['status'],'BRIDGE_CANDIDATE_ONLY_NOT_EA_BOUND')
        self.assertTrue(set(dict(plan['core_role_assignments']).values())<=set(ALL))
        self.assertFalse(set(plan['normal_base_ids'])-set(ALL))

    def test_preserves_valid_manual_pins_before_optimizing_bridges(self):
        pins={278965:'16',278966:'3',278967:'4',278968:'11',303765:'12'}
        p=propose_roster_first(CLASSES,PLAYABLE,real_ea_results(),pins)
        self.assertEqual(dict(p['core_role_assignments']),pins)
        self.assertEqual(p['preferred_role_assignments_preserved'],5)
        self.assertEqual(p['school_only_bridge_count'],1)

    def test_non_base_student_must_qualify_for_genuine_core(self):
        invalid=real_ea_results(cheer=('2',))
        p=propose_roster_first(CLASSES,PLAYABLE,invalid)
        self.assertEqual(p['status'],'BLOCKED')
        self.assertIn('no 5 Core',p['reason'])
        self.assertFalse(p['roster_mutated'])

    def test_fewer_than_eight_original_base_ids_blocks(self):
        invalid=real_ea_results()
        invalid[BASE_JOB]=tuple(sid for sid in NPC[:7])
        p=propose_roster_first(CLASSES,PLAYABLE,invalid)
        self.assertEqual(p['status'],'BLOCKED')
        self.assertIn('fewer than eight',p['reason'])

    def test_missing_or_fabricated_filter_data_is_rejected(self):
        invalid=real_ea_results()
        invalid.pop(303765)
        self.assertEqual(
            propose_roster_first(CLASSES,PLAYABLE,invalid)['status'],'BLOCKED')
        invalid=real_ea_results()
        invalid[278966]=['not-a-sim']
        self.assertEqual(
            propose_roster_first(CLASSES,PLAYABLE,invalid)['status'],'BLOCKED')

    def test_duplicate_or_out_of_roster_teens_are_rejected(self):
        groups=(('1',)*8,CLASSES[1])
        self.assertEqual(propose_roster_first(
            groups,PLAYABLE,real_ea_results())['status'],'BLOCKED')
        self.assertEqual(propose_roster_first(
            CLASSES,('1','9','99'),real_ea_results())['status'],'BLOCKED')


if __name__=='__main__':
    unittest.main()
