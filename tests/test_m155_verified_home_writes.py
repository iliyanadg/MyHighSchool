"""M155: verified home-session writes across EA temporary travel slot.

No EA imports: exercises the real pure slot-identity implementation.
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src' / 'm2_registry'))
from mhs56_slot_identity import TravelSlotGuard, IdentityError


class M155VerifiedHomeWrites(unittest.TestCase):
    def setUp(self):
        self.guard = TravelSlotGuard()
        self.assertEqual(self.guard.resolve(15, '0xbeef', 721), '15')

    def test_same_save_home_edit_may_use_verified_anchor(self):
        self.assertEqual(
            self.guard.resolve(0xFFFFFFFF, '0xbeef', 721,
                               verified_home_write=True), '15')
        self.assertEqual(self.guard.last_source, 'verified_home_write')

    def test_unverified_write_remains_blocked(self):
        with self.assertRaisesRegex(IdentityError, 'modifiche bloccate'):
            self.guard.resolve(0xFFFFFFFF, '0xbeef', 721)
        self.assertEqual(self.guard.last_source, 'blocked_write_scratch')

    def test_cold_start_cannot_write_unknown_save(self):
        with self.assertRaises(IdentityError):
            TravelSlotGuard().resolve(
                0xFFFFFFFF, '0xbeef', 721, verified_home_write=True)

    def test_wrong_guid_cannot_write(self):
        with self.assertRaises(IdentityError):
            self.guard.resolve(
                0xFFFFFFFF, '0xdead', 721, verified_home_write=True)
        self.assertIsNone(self.guard.slot)

    def test_wrong_household_cannot_write(self):
        with self.assertRaises(IdentityError):
            self.guard.resolve(
                0xFFFFFFFF, '0xbeef', 722, verified_home_write=True)
        self.assertIsNone(self.guard.slot)

    def test_missing_guid_cannot_write(self):
        with self.assertRaises(IdentityError):
            self.guard.resolve(
                0xFFFFFFFF, None, 721, verified_home_write=True)

    def test_real_slot_retains_priority(self):
        self.assertEqual(
            self.guard.resolve(16, '0xcafe', 721,
                               verified_home_write=True), '16')
        self.assertEqual(self.guard.last_source, 'live_proto')


if __name__ == '__main__':
    unittest.main()
