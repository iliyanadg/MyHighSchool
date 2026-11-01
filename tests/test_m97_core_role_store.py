import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'/'m97_core_reservations'))
from mhs97_core_role_store import (
    CoreRoleStore,CoreRoleRoster,CoreRosterError,plan_change,ROLE_TO_JOB)

IDS=tuple(str(i) for i in range(1,17))
def eligible(job,sid):
    return job in ROLE_TO_JOB.values() and sid in range(1,17)

class RoleStoreTests(unittest.TestCase):
    def test_first_use_empty_not_random(self):
        with TemporaryDirectory() as d:
            store=CoreRoleStore(d)
            roster=store.load('91')
            self.assertFalse(roster.complete)
            self.assertEqual(roster.chosen(),{})
            self.assertEqual(len(roster.roles),5)
            self.assertFalse(Path(store.path('91')).exists())

    def test_sequential_manual_role_choices_persist_per_save(self):
        with TemporaryDirectory() as d:
            store=CoreRoleStore(d)
            r=store.load(91)
            chosen=[('cheer','2'),('chess','3'),('football','4'),
                    ('computer','10'),('mean','11')]
            for role,sid in chosen:
                new=plan_change(r,role,sid,IDS,eligible)
                self.assertNotEqual(new.fingerprint(),r.fingerprint())
                self.assertTrue(store.save(91,new,r.fingerprint()))
                r=store.load(91)
            self.assertTrue(r.complete)
            self.assertEqual(r.chosen(),{
                278965:'2',278966:'3',278967:'4',
                278968:'10',303765:'11'})
            self.assertFalse(store.load(92).complete)
            self.assertFalse(Path(store.path(92)).exists())

    def test_refuse_role_for_unenrolled_or_noneligible(self):
        current=CoreRoleRoster(1)
        with self.assertRaises(CoreRosterError):
            plan_change(current,'chess','99',IDS,eligible)
        with self.assertRaises(CoreRosterError):
            plan_change(current,'chess','2',IDS,lambda job,sid:False)
        with self.assertRaises(CoreRosterError):
            plan_change(current,'chess','2',IDS,None)

    def test_one_student_cannot_hold_multiple_roles(self):
        current=CoreRoleRoster(1)
        current=plan_change(current,'chess','2',IDS,eligible)
        with self.assertRaises(CoreRosterError):
            plan_change(current,'cheer','2',IDS,eligible)
        self.assertEqual(current.chosen(),{278966:'2'})

    def test_removal_leaves_vacancy_not_auto_replacement(self):
        current=CoreRoleRoster(1)
        current=plan_change(current,'football','4',IDS,eligible)
        current=plan_change(current,'football',None,IDS,eligible)
        self.assertIsNone(current.roles['football'])
        self.assertFalse(current.complete)

    def test_wrong_save_cannot_overwrite_existing_roles(self):
        with TemporaryDirectory() as d:
            store=CoreRoleStore(d)
            original=store.load(1)
            updated=plan_change(original,'computer','10',IDS,eligible)
            self.assertTrue(store.save(1,updated,original.fingerprint()))
            with self.assertRaises(CoreRosterError):
                store.save(2,updated,store.load(2).fingerprint())
            with self.assertRaises(CoreRosterError):
                store.save(1,original,original.fingerprint())
            self.assertEqual(store.load(1).roles['computer'],'10')

    def test_stale_fingerprint_blocks_old_menu(self):
        with TemporaryDirectory() as d:
            store=CoreRoleStore(d)
            start=store.load(1)
            changed=plan_change(start,'mean','11',IDS,eligible)
            store.save(1,changed,start.fingerprint())
            with self.assertRaises(CoreRosterError):
                store.save(1,plan_change(start,'cheer','2',IDS,eligible),
                           start.fingerprint())

    def test_reject_invalid_json_and_duplicate_roles(self):
        with self.assertRaises(CoreRosterError):
            CoreRoleRoster(1,{'cheer':'2'})
        with self.assertRaises(CoreRosterError):
            roles={r:None for r in ROLE_TO_JOB}
            roles['cheer']='2'
            roles['mean']='2'
            CoreRoleRoster(1,roles)
        with self.assertRaises(CoreRosterError):
            CoreRoleRoster.from_json('{}')

    def test_failure_never_partially_writes(self):
        with TemporaryDirectory() as d:
            store=CoreRoleStore(d)
            with self.assertRaises(CoreRosterError):
                plan_change(store.load(1),'chess',True,IDS,eligible)
            self.assertFalse(Path(store.path(1)).exists())

if __name__=='__main__':
    unittest.main()
