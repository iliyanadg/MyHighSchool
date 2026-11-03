"""M128 offline tests; no game installation needed."""
import unittest
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'/'m128_alignment'))
from mhs128_ea_class_trait_alignment import (
    planned_changes,public_rows,align_roster_trait)


class Tracker:
    def __init__(self,present=False,broken=False):
        self.present=present
        self.broken=broken
    def has_trait(self,t):return self.present
    def add_trait(self,t):
        if self.broken:raise ValueError('SIMULATED_FAILURE')
        self.present=True
    def remove_trait(self,t):
        if self.broken:raise ValueError('SIMULATED_FAILURE')
        self.present=False


class Info:
    age='TEEN'
    species='HUMAN'
    def __init__(self,present=False,broken=False):
        self.trait_tracker=Tracker(present,broken)


class Manager:
    def __init__(self,items):self.items=items
    def get(self,key):return self.items.get(key)


def inputs():
    groups=(tuple(str(i) for i in range(1,9)),
            tuple(str(i) for i in range(9,17)))
    infos={i:Info(i%2==0) for i in range(1,17)}
    return groups,infos


class TestRosterTrait(unittest.TestCase):
    def test_only_enrolled_correct_16(self):
        groups,infos=inputs()
        rows=planned_changes(groups,Manager(infos),object(),'TEEN','HUMAN')
        self.assertEqual(len(rows),16)
        self.assertEqual(sum(r['requires_change'] for r in rows),8)
        self.assertEqual([r['registered_class'] for r in rows],[1]*8+[2]*8)
        self.assertNotIn('trait_tracker',public_rows(rows)[0])

    def test_successful_alignment_is_idempotent(self):
        groups,infos=inputs()
        trait=object()
        rows=planned_changes(groups,Manager(infos),trait,'TEEN','HUMAN')
        result=align_roster_trait(rows,trait)
        self.assertEqual(result['changed'],8)
        self.assertTrue(result['success'])
        updated=planned_changes(groups,Manager(infos),trait,'TEEN','HUMAN')
        self.assertFalse(any(r['requires_change'] for r in updated))
        self.assertEqual(align_roster_trait(updated,trait)['changed'],0)

    def test_invalid_and_duplicate_roster_rejected(self):
        groups,infos=inputs()
        with self.assertRaises(ValueError):
            planned_changes((groups[0],groups[0]),
                            Manager(infos),object(),'TEEN','HUMAN')
        with self.assertRaises(ValueError):
            planned_changes((groups[0],groups[1][:-1]),
                            Manager(infos),object(),'TEEN','HUMAN')
        with self.assertRaises(ValueError):
            planned_changes(groups,Manager(infos),None,'TEEN','HUMAN')

    def test_missing_sim_blocks_any_mutation(self):
        groups,infos=inputs()
        del infos[16]
        with self.assertRaises(ValueError):
            planned_changes(groups,Manager(infos),object(),'TEEN','HUMAN')
        self.assertEqual(infos[1].trait_tracker.present,False)

    def test_failed_change_rolls_back_previous(self):
        groups,infos=inputs()
        infos[3].trait_tracker.broken=True
        trait=object()
        rows=planned_changes(groups,Manager(infos),trait,'TEEN','HUMAN')
        result=align_roster_trait(rows,trait)
        self.assertFalse(result['success'])
        self.assertTrue(result['rollback_verified'])
        self.assertFalse(infos[1].trait_tracker.present)


if __name__=='__main__':
    unittest.main()
