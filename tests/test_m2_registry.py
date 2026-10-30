"""M2 roster/slot persistence tests on fake data only; no Sims 4 runtime."""
import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
M2 = ROOT / 'src' / 'm2_registry'
sys.path.insert(0, str(M2))
from mhs_m2_roster import SchoolRoster, RosterError, canonical_save_slot
from mhs_m2_store import RosterStore, StoreError, EnrollmentService
from mhs_m2_game_bridge import receive_selected_ids


class RosterBatchTests(unittest.TestCase):
    def setUp(self):
        self.roster = SchoolRoster('7')
        self.teen = lambda sid: int(sid) <= 100

    def test_new_save_is_empty_not_autofilled(self):
        self.assertEqual(self.roster.assignments, {})
        self.assertEqual(self.roster.class_members(1), [])

    def test_eight_selected_in_one_transaction(self):
        copy, outcome = self.roster.assign_many(1, list(range(1, 9)), self.teen)
        self.assertEqual(len(copy.class_members(1)), 8)
        self.assertEqual(outcome['changed'], 8)
        self.assertEqual(self.roster.assignments, {})

    def test_ninth_is_blocked_without_mutating_existing(self):
        filled, _ = self.roster.assign_many(1, list(range(1, 9)), self.teen)
        with self.assertRaises(RosterError):
            filled.assign_many(1, [9], self.teen)
        self.assertEqual(filled.class_members(1), [str(n) for n in range(1, 9)])

    def test_transfers_not_duplicate(self):
        one, _ = self.roster.assign_many(1, [1], self.teen)
        two, result = one.assign_many(2, [1], self.teen)
        self.assertEqual(result['moved'], 1)
        self.assertEqual(two.class_members(1), [])
        self.assertEqual(two.class_members(2), ['1'])
        self.assertEqual(one.class_members(1), ['1'])

    def test_existing_members_are_not_removed_by_add(self):
        one, _ = self.roster.assign_many(1, [1, 2], self.teen)
        two, _ = one.assign_many(1, [3], self.teen)
        self.assertEqual(two.class_members(1), ['1','2','3'])

    def test_same_selection_is_idempotent(self):
        one, _ = self.roster.assign_many(1, [3], self.teen)
        two, result = one.assign_many(1, [3], self.teen)
        self.assertEqual(result['changed'], 0)
        self.assertEqual(one.to_json(), two.to_json())

    def test_duplicate_id_blocked(self):
        with self.assertRaises(RosterError):
            self.roster.assign_many(1, [1, '1'], self.teen)

    def test_adult_or_nonexistent_id_blocked(self):
        with self.assertRaises(RosterError):
            self.roster.assign_many(1, [1, 101], self.teen)
        self.assertEqual(self.roster.assignments, {})

    def test_invalid_selection_and_id_fail(self):
        for ids in ([], list(range(1, 10)), ['abc'], [0], [True], '1'):
            with self.assertRaises(RosterError):
                self.roster.assign_many(1, ids, self.teen)

    def test_third_class_supported_but_fourth_rejected(self):
        updated, _ = self.roster.assign_many(3, [1], self.teen)
        self.assertEqual(updated.class_members(3), ['1'])
        with self.assertRaises(RosterError):
            self.roster.assign_many(4, [1], self.teen)

    def test_corrupt_overfull_json_refused(self):
        huge = {'schema':1,'slot':'7','assignments':{str(i):1 for i in range(1,10)}}
        with self.assertRaises(RosterError):
            SchoolRoster.from_json(json.dumps(huge))

    def test_roundtrip_preserves_ids_and_class(self):
        one,_ = self.roster.assign_many(2,[12,18],self.teen)
        back=SchoolRoster.from_json(one.to_json())
        self.assertEqual(back.assignments, one.assignments)


class SaveIsolationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'm2'
        self.store = RosterStore(str(self.path))
        self.teen = lambda sid: int(sid) < 1000

    def service(self, slot):
        return EnrollmentService(self.store, lambda:slot, self.teen)

    def test_registry_separated_by_save_slot(self):
        self.service(12).enroll_selection(1, [5, 6])
        self.service(13).enroll_selection(2, [7])
        self.assertEqual(self.store.load(12).class_members(1), ['5','6'])
        self.assertEqual(self.store.load(13).class_members(1), [])
        self.assertEqual(self.store.load(13).class_members(2), ['7'])

    def test_write_and_reload(self):
        self.service(22).enroll_selection(1, [33])
        restarted = RosterStore(str(self.path))
        self.assertEqual(restarted.load(22).assignments, {'33':1})

    def test_unsaved_zero_slot_never_writes(self):
        with self.assertRaises(RosterError):
            self.service(0).enroll_selection(1, [1])
        self.assertFalse(self.path.exists())

    def test_invalid_slot_path_traversal_rejected(self):
        for slot in ('../1', '01', -4, True, '', None):
            with self.assertRaises(RosterError):
                canonical_save_slot(slot)

    def test_corrupt_file_blocks_write_and_is_preserved(self):
        self.path.mkdir(parents=True,exist_ok=True)
        bad=self.path/'Registro_slot_1.json'
        bad.write_text('INVALID RECORD',encoding='utf-8')
        with self.assertRaises(StoreError):
            self.service(1).enroll_selection(1,[9])
        self.assertEqual(bad.read_text(encoding='utf-8'),'INVALID RECORD')

    def test_wrong_embedded_slot_refused(self):
        self.path.mkdir(parents=True,exist_ok=True)
        (self.path/'Registro_slot_1.json').write_text(
            SchoolRoster('2').to_json(),encoding='utf-8')
        with self.assertRaises(StoreError):
            self.store.load(1)

    def test_existing_same_class_does_not_write_again(self):
        self.service(1).enroll_selection(1,[22])
        path=self.store.path(1)
        content=Path(path).read_bytes()
        self.service(1).enroll_selection(1,[22])
        self.assertEqual(Path(path).read_bytes(),content)

    def test_selection_fails_as_one_transaction(self):
        self.service(1).enroll_selection(1, list(range(1,9)))
        before=Path(self.store.path(1)).read_bytes()
        with self.assertRaises(RosterError):
            self.service(1).enroll_selection(1,[900])
        self.assertEqual(Path(self.store.path(1)).read_bytes(),before)

    def test_bridge_accepts_ids_only_from_explicit_callback(self):
        result=receive_selected_ids(2,[20,21],self.store,lambda:'1',self.teen)
        self.assertEqual(result['changed'],2)
        self.assertEqual(self.store.load(1).class_members(2), ['20','21'])


if __name__=='__main__': unittest.main()
