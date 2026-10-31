"""M46 enrollment previews never write, confirmed data is atomic and guarded."""
import tempfile
import unittest
import sys
from pathlib import Path

REG=Path(__file__).resolve().parents[1]/'src'/'m2_registry'
if str(REG) not in sys.path:
    sys.path.insert(0,str(REG))

from mhs46_enrollment_transaction import (
    preview_enrollment,confirm_enrollment,EnrollmentTransactionError)
from mhs34_settings import SettingsStore,SettingsError
from mhs_m2_store import RosterStore
from mhs_m2_roster import SchoolRoster,RosterError


class TestM46Enrollment(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        folder=self.temp.name
        self.store=RosterStore(folder)
        self.settings=SettingsStore(folder)
        self.slot='11'
        self.allowed={'11','12','13','14','15','16','17','18','19','20'}
        self.is_teen=lambda sid:sid in self.allowed
        self.settings.set_active(self.slot,True)

    def preview(self,klass,ids):
        return preview_enrollment(
            self.store,self.settings,self.slot,klass,tuple(ids),self.is_teen)

    def confirm(self,plan):
        return confirm_enrollment(
            self.store,self.settings,self.slot,plan,self.is_teen)

    def test_preview_never_creates_student_json(self):
        plan=self.preview(1,('11','12'))
        self.assertEqual(plan['remaining'],6)
        self.assertEqual(plan['changed'],2)
        self.assertFalse(Path(self.store.path(self.slot)).exists())
        self.assertEqual(self.store.load(self.slot).class_members(1),[])

    def test_cancel_is_noop_and_confirm_commits_once(self):
        plan=self.preview(1,('11','12'))
        # Simulate dialog Cancel: confirm_enrollment is not called.
        self.assertEqual(self.store.load(self.slot).class_members(1),[])
        result=self.confirm(plan)
        self.assertTrue(result['written'])
        self.assertEqual(result['class_size'],2)
        self.assertEqual(self.store.load(self.slot).class_members(1),['11','12'])
        self.assertTrue(Path(self.store.journal_path(self.slot)).exists())
        # A second confirmation cannot silently write a stale plan.
        with self.assertRaises(EnrollmentTransactionError):
            self.confirm(plan)

    def test_block_when_registry_changed_during_dialog(self):
        plan=self.preview(2,('11',))
        self.store.save(self.slot,SchoolRoster(self.slot,{'12':1}))
        with self.assertRaisesRegex(EnrollmentTransactionError,'modificato'):
            self.confirm(plan)
        self.assertEqual(self.store.load(self.slot).class_members(2),[])

    def test_block_on_changed_slot(self):
        plan=self.preview(1,('11',))
        self.settings.set_active('12',True)
        with self.assertRaises(EnrollmentTransactionError):
            confirm_enrollment(self.store,self.settings,'12',plan,self.is_teen)
        self.assertFalse(Path(self.store.path(self.slot)).exists())

    def test_disabling_school_during_dialog_blocks_write(self):
        plan=self.preview(1,('11',))
        self.settings.set_active(self.slot,False)
        with self.assertRaises(SettingsError):
            self.confirm(plan)

    def test_disabling_third_class_during_dialog_blocks_write(self):
        self.settings.set_class_count(self.slot,3,self.store.load(self.slot))
        plan=self.preview(3,('11',))
        self.settings.set_class_count(self.slot,2,self.store.load(self.slot))
        with self.assertRaises(SettingsError):
            self.confirm(plan)

    def test_full_class_rejected_without_overwriting(self):
        self.store.save(self.slot,SchoolRoster(
            self.slot,{str(i):1 for i in range(11,19)}))
        with self.assertRaises(RosterError):
            self.preview(1,('19',))
        self.assertEqual(len(self.store.load(self.slot).class_members(1)),8)

    def test_ineligible_selection_rejected(self):
        with self.assertRaises(RosterError):
            self.preview(2,('11','123456'))
        self.assertFalse(Path(self.store.path(self.slot)).exists())

    def test_valid_transfer_updates_only_one_roster(self):
        self.store.save(self.slot,SchoolRoster(self.slot,{'11':1}))
        plan=self.preview(2,('11',))
        self.assertEqual(plan['moved'],1)
        result=self.confirm(plan)
        self.assertEqual(result['moved'],1)
        self.assertEqual(self.store.load(self.slot).class_members(1),[])
        self.assertEqual(self.store.load(self.slot).class_members(2),['11'])

    def test_no_change_is_no_write(self):
        self.store.save(self.slot,SchoolRoster(self.slot,{'11':1}))
        plan=self.preview(1,('11',))
        before=Path(self.store.path(self.slot)).read_bytes()
        result=self.confirm(plan)
        self.assertFalse(result['written'])
        self.assertEqual(Path(self.store.path(self.slot)).read_bytes(),before)


if __name__=='__main__':
    unittest.main()
