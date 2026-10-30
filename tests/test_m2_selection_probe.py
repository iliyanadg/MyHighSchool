"""Fail-closed test harness for M1 -> M2 participant transfer."""
import sys
import tempfile
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "m2_registry"))
from mhs_m2_selection_probe import (SelectionProbeError, collect_picked_ids,
                                    require_complete_selection, enroll_confirmed_batch)
from mhs_m2_store import RosterStore
from mhs_m2_roster import SchoolRoster


PICKED = object()
OTHER = object()


class Info(object):
    def __init__(self, sid):
        self.sim_id = sid


class Sim(object):
    def __init__(self, sid):
        self.sim_info = Info(sid)


class Interaction(object):
    def __init__(self, selected):
        self.selected = selected
        self.calls = []

    def get_participants(self, which):
        self.calls.append(which)
        if which is not PICKED:
            raise RuntimeError("No non-picked participants permitted")
        return self.selected


class ProbeTests(unittest.TestCase):
    def test_one_picked_sim(self):
        self.assertEqual(collect_picked_ids(Interaction((Sim(11),)), PICKED), ("11",))

    def test_multiple_picked_sim_sorted(self):
        self.assertEqual(collect_picked_ids(Interaction((Sim(39), Info(3), Sim(12))), PICKED),
                         ("3", "12", "39"))

    def test_set_participants_supported(self):
        s = {Info(5), Info(4)}
        self.assertEqual(collect_picked_ids(Interaction(s), PICKED), ("4","5"))

    def test_never_fall_back_to_actor_or_target(self):
        interaction = Interaction((Sim(12),))
        collect_picked_ids(interaction, PICKED)
        self.assertEqual(interaction.calls, [PICKED])

    def test_null_context_rejected(self):
        for value, which in ((None,PICKED),(Interaction((Sim(1),)),None)):
            with self.assertRaises(SelectionProbeError):
                collect_picked_ids(value, which)

    def test_empty_picker_rejected(self):
        with self.assertRaises(SelectionProbeError):
            collect_picked_ids(Interaction(()), PICKED)

    def test_too_many_rejected(self):
        with self.assertRaises(SelectionProbeError):
            collect_picked_ids(Interaction([Sim(i) for i in range(1,10)]),PICKED)

    def test_text_not_a_sim_rejected(self):
        with self.assertRaises(SelectionProbeError):
            collect_picked_ids(Interaction(('500',)), PICKED)

    def test_duplicate_picked_ids_rejected(self):
        with self.assertRaises(SelectionProbeError):
            collect_picked_ids(Interaction((Sim(50),Info(50))), PICKED)

    def test_invalid_sim_id_rejected(self):
        with self.assertRaises(SelectionProbeError):
            collect_picked_ids(Interaction((Sim(0),)), PICKED)

    def test_malformed_participants_rejected(self):
        for value in (None,'not a sim',123,{'a':Sim(1)}):
            with self.assertRaises(SelectionProbeError):
                collect_picked_ids(Interaction(value), PICKED)

    def test_no_getter_rejected(self):
        with self.assertRaises(SelectionProbeError):
            collect_picked_ids(object(), PICKED)

    def test_getter_failure_rejected(self):
        with self.assertRaises(SelectionProbeError):
            collect_picked_ids(Interaction((Sim(1),)), OTHER)

    def test_uncorroborated_selection_must_fail(self):
        with self.assertRaises(SelectionProbeError):
            require_complete_selection(Interaction((Sim(1),)), PICKED, 1)

    def test_expected_count_does_not_match(self):
        with self.assertRaises(SelectionProbeError):
            require_complete_selection(Interaction((Sim(1),)), PICKED, 3, True)

    def test_validated_batch_returns_exact_ids(self):
        v=require_complete_selection(Interaction((Sim(2),Sim(1))),PICKED,2,True)
        self.assertEqual(v, ('1','2'))

    def test_false_flag_even_with_valid_count_rejected(self):
        with self.assertRaises(SelectionProbeError):
            require_complete_selection(Interaction((Sim(1),)),PICKED,1,False)

    def test_invalid_count_rejected(self):
        for count in (None, True, 0, 9, '2'):
            with self.assertRaises(SelectionProbeError):
                require_complete_selection(Interaction((Sim(1),)),PICKED,count,True)


class SaveGuardTests(unittest.TestCase):
    def setUp(self):
        self.folder=tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.store=RosterStore(self.folder.name + '/registry')
        self.slot=lambda: "31"
        self.teen=lambda sid: int(sid) in (11,12,13,14)

    def attempt(self, ids, expected, certified):
        return enroll_confirmed_batch(1,Interaction(tuple(Sim(x) for x in ids)),
                                      PICKED, expected, certified,self.store,self.slot,self.teen)

    def test_no_files_when_batch_not_certified(self):
        with self.assertRaises(SelectionProbeError):
            self.attempt((11,12),2,False)
        self.assertFalse(Path(self.store.path(31)).exists())

    def test_partial_batch_never_committed(self):
        with self.assertRaises(SelectionProbeError):
            self.attempt((11,),2,True)
        self.assertFalse(Path(self.store.path(31)).exists())

    def test_valid_certified_batch_writes_once(self):
        r=self.attempt((11,12),2,True)
        self.assertEqual(r['changed'],2)
        self.assertEqual(self.store.load(31).class_members(1),['11','12'])

    def test_second_batch_adds_students_only_when_certified(self):
        self.attempt((11,12),2,True)
        before=Path(self.store.path(31)).read_bytes()
        with self.assertRaises(SelectionProbeError):
            self.attempt((13,),2,True)
        self.assertEqual(Path(self.store.path(31)).read_bytes(),before)
        self.attempt((13,),1,True)
        self.assertEqual(self.store.load(31).class_members(1),['11','12','13'])

    def test_adult_or_nonexisting_not_written(self):
        with self.assertRaises(Exception):
            self.attempt((11,99),2,True)
        self.assertFalse(Path(self.store.path(31)).exists())

    def test_slot_not_available_blocks_without_writes(self):
        self.slot=lambda:0
        with self.assertRaises(Exception):
            self.attempt((11,),1,True)
        self.assertFalse(Path(self.store.path(31)).exists())


if __name__ == '__main__':
    unittest.main()
