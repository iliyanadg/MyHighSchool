"""M152: expensive native staff and cafeteria readback cadence regression."""
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'/'classroom_control'))
from mhs152_staff_scan_policy import (
    should_scan_supplemental_staff,STAFF_RESCAN_SIM_MINUTES)


class StaffScanTests(unittest.TestCase):
    def test_first_eligible_school_shift_gets_full_scan(self):
        self.assertTrue(should_scan_supplemental_staff(1500*580,None))
        self.assertEqual(STAFF_RESCAN_SIM_MINUTES,12)

    def test_three_minute_ea_alarm_remains_unmodified(self):
        starts=1500*582
        last=None
        scanned=[]
        skipped=[]
        # EA's same three-minute callback still fires 14 times.
        for n in range(14):
            now=starts+1500*(3*n)
            if should_scan_supplemental_staff(now,last):
                scanned.append(n)
                last=now
            else:
                skipped.append(n)
        self.assertEqual(scanned,[0,4,8,12])
        self.assertEqual(len(scanned)+len(skipped),14)
        self.assertEqual(len(skipped),10)

    def test_changed_day_rewind_can_recheck(self):
        self.assertTrue(should_scan_supplemental_staff(1500*480,1500*1400))
        self.assertTrue(should_scan_supplemental_staff(1500*582,None))

    def test_unreadable_clock_refuses(self):
        for bad in (-1,None,3.1,'abc',True):
            self.assertFalse(should_scan_supplemental_staff(bad,None))
        self.assertFalse(should_scan_supplemental_staff(1500,True))

    def test_never_guess_interval_from_boolean(self):
        self.assertFalse(should_scan_supplemental_staff(18000,0,minutes=True))
        self.assertFalse(should_scan_supplemental_staff(18000,0,minutes=0))


if __name__=='__main__':
    unittest.main()
