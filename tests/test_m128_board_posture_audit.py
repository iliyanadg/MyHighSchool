"""M128.2 read-only classroom target coverage and conflict tests."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'/'m128_alignment'))
from mhs128_board_posture_audit import audit_classroom_targets


class Whiteboard: pass
Whiteboard.__module__='sims4.tuning.instances'
Whiteboard.__name__='object_HighSchool_Active_Whiteboard'


class SimInfo:
    def __init__(self,has_trait,board):
        self.trait_tracker=self
        self.trait=has_trait
        target=Whiteboard()
        target.id=board
        class Running:pass
        class Queue:pass
        class Posture:pass
        class Sim:pass
        running=Running()
        running.target=target
        queue=Queue()
        queue.running=running
        posture=Posture()
        posture.target=None
        sim=Sim()
        sim.queue=queue
        sim.posture=posture
        self.sim=sim
    def has_trait(self,trait):return self.trait
    def get_sim_instance(self):return self.sim


class Manager:
    def __init__(self,items):self.items=items
    def get(self,key):return self.items.get(key)


class TestBoardAudit(unittest.TestCase):
    def test_conflicting_board_selected_by_two_registered_classes(self):
        groups=(tuple(range(1,9)),tuple(range(9,17)))
        items={sid:SimInfo(sid<=8,100 if sid<=8 else 200)
               for sid in range(1,17)}
        items[9]=SimInfo(False,100)
        report=audit_classroom_targets(groups,Manager(items),object())
        self.assertEqual(report['count'],16)
        self.assertEqual(report['game_mutations'],0)
        self.assertFalse(report['sitting_at_correct_desks_verified'])
        self.assertEqual(report['board_ids_targeted_by_both_classes'],['100'])

    def test_mismatched_trait_read_only(self):
        groups=(tuple(range(1,9)),tuple(range(9,17)))
        items={sid:SimInfo(False,100 if sid<=8 else 200)
               for sid in range(1,17)}
        report=audit_classroom_targets(groups,Manager(items),object())
        self.assertEqual(report['trait_mismatches'],8)

    def test_rejects_duplicate_and_underfilled_class(self):
        items={sid:SimInfo(False,100) for sid in range(1,17)}
        with self.assertRaises(ValueError):
            audit_classroom_targets((tuple(range(1,9)),tuple(range(1,9))),
                                    Manager(items),object())
        with self.assertRaises(ValueError):
            audit_classroom_targets((tuple(range(1,9)),tuple(range(9,16))),
                                    Manager(items),object())


if __name__=='__main__':
    unittest.main()
