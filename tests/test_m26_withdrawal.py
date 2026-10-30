"""M26 removal: atomic, class-specific, fail-closed tests."""
import sys
import tempfile
import types
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'/'m2_registry'))
sys.path.insert(0,str(ROOT/'src'/'m26_withdrawal'))
from mhs_m2_roster import SchoolRoster
from mhs_m2_store import RosterStore, EnrollmentService
from mhs26_remove import (RemovalError, RemovalService, plan_removal,
                          class_member_ids, candidate_rows, roster_fingerprint)


class RemovalTests(unittest.TestCase):
    def setUp(self):
        self.roster=SchoolRoster('11',{'101':1,'102':1,'201':2,'202':2})

    def test_class_specific_ids(self):
        self.assertEqual(class_member_ids(self.roster,1),('101','102'))
        self.assertEqual(class_member_ids(self.roster,2),('201','202'))

    def test_remove_one_preserves_other_class_and_original(self):
        proposed, stats=plan_removal(self.roster,1,['101'])
        self.assertEqual(proposed.class_members(1),['102'])
        self.assertEqual(proposed.class_members(2),['201','202'])
        self.assertEqual(self.roster.class_members(1),['101','102'])
        self.assertEqual(stats['removed'],1)
        self.assertEqual(stats['remaining'],1)

    def test_remove_multiple_from_own_class_only(self):
        proposed, stats=plan_removal(self.roster,2,['201','202'])
        self.assertEqual(proposed.class_members(2),[])
        self.assertEqual(proposed.class_members(1),['101','102'])
        self.assertEqual(stats['removed'],2)

    def test_other_class_rejected_atomically(self):
        with self.assertRaises(RemovalError):
            plan_removal(self.roster,1,['101','202'])
        self.assertEqual(len(self.roster.assignments),4)

    def test_unenrolled_rejected(self):
        with self.assertRaises(RemovalError):
            plan_removal(self.roster,2,['999'])

    def test_duplicate_selection_rejected(self):
        with self.assertRaises(RemovalError):
            plan_removal(self.roster,1,['101',101])

    def test_empty_selection_rejected(self):
        with self.assertRaises(RemovalError):
            plan_removal(self.roster,1,[])

    def test_wrong_class_rejected(self):
        with self.assertRaises(Exception):
            plan_removal(self.roster,3,['101'])

    def test_oversized_list_rejected(self):
        with self.assertRaises(RemovalError):
            plan_removal(self.roster,1,list(range(1,10)))

    def test_candidate_rows_only_members_of_correct_class(self):
        candidate={str(i):types.SimpleNamespace(sim_id=i)
                   for i in (101,102,201,202,999)}
        self.assertEqual([x.sim_id for x in candidate_rows(
            self.roster,1,lambda sid:candidate.get(sid))],[101,102])

    def test_candidate_rows_missing_sim_hidden(self):
        out=candidate_rows(self.roster,1,
                           lambda sid:types.SimpleNamespace(sim_id=101) if sid=='101' else None)
        self.assertEqual(len(out),1)

    def test_candidate_rows_wrong_sim_id_skipped(self):
        out=candidate_rows(self.roster,1,lambda sid:types.SimpleNamespace(sim_id=999))
        self.assertEqual(out,())

    def test_hash_changes_with_assignment(self):
        other,_=plan_removal(self.roster,1,['101'])
        self.assertNotEqual(roster_fingerprint(other),roster_fingerprint(self.roster))


class StoreServiceTests(unittest.TestCase):
    def setUp(self):
        self.folder=tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.store=RosterStore(str(Path(self.folder.name)/'M26'))
        self.store.save('11',SchoolRoster('11',{'1':1,'2':1,'3':2}))
        self.service=RemovalService(self.store)

    def test_preview_never_writes(self):
        name=Path(self.store.path(11))
        before=name.read_bytes()
        preview=self.service.preview(11,1,['1'])
        self.assertEqual(preview['removed'],1)
        self.assertEqual(before,name.read_bytes())

    def test_commit_persists_withdrawal(self):
        preview=self.service.preview(11,1,['1'])
        result=self.service.commit(preview,11)
        self.assertEqual(result['removed'],1)
        self.assertEqual(self.store.load(11).class_members(1),['2'])
        self.assertEqual(self.store.load(11).class_members(2),['3'])

    def test_commit_other_slot_does_not_write(self):
        name=Path(self.store.path(11))
        before=name.read_bytes()
        preview=self.service.preview(11,1,['1'])
        with self.assertRaises(RemovalError):
            self.service.commit(preview,12)
        self.assertEqual(before,name.read_bytes())

    def test_stale_snapshot_blocks_commit(self):
        preview=self.service.preview(11,1,['1'])
        self.store.save('11',SchoolRoster('11',{'1':1,'2':1,'3':2,'4':2}))
        before=Path(self.store.path(11)).read_bytes()
        with self.assertRaises(RemovalError):
            self.service.commit(preview,11)
        self.assertEqual(before,Path(self.store.path(11)).read_bytes())

    def test_no_student_deleted_and_reenrollment_possible(self):
        preview=self.service.preview(11,1,['1'])
        self.service.commit(preview,11)
        service=EnrollmentService(self.store,lambda:'11',lambda sid:True)
        service.enroll_selection(2,['1'])
        self.assertEqual(self.store.load(11).class_members(2),['1','3'])

    def test_repeated_commit_fails_closed(self):
        preview=self.service.preview(11,1,['1'])
        self.service.commit(preview,11)
        with self.assertRaises(RemovalError):
            self.service.commit(preview,11)
        self.assertEqual(self.store.load(11).class_members(1),['2'])


if __name__=='__main__':
    unittest.main()
