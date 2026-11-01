"""M93: four proven EA filters; two truly missing tunings."""
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'/'m93_core'))
from mhs93_verified_jobs import (
    VERIFIED_SPECS, PENDING_TUNING, CORE_STUDENT_JOBS, TEACHER_JOBS,
    classify_job, core_filter_specs_ready, verify_complete_core_jobs)

class VerifiedSchoolJobTuningTests(unittest.TestCase):
    def test_original_tuning_filters_and_auto_invites(self):
        self.assertEqual(VERIFIED_SPECS[277894],(280516,1,1,True))
        self.assertEqual(VERIFIED_SPECS[278965],(276592,1,1,True))
        self.assertEqual(VERIFIED_SPECS[278968],(276595,1,1,True))
        self.assertEqual(VERIFIED_SPECS[303765],(303766,1,1,True))

    def test_chess_and_football_are_not_guessed(self):
        self.assertEqual(PENDING_TUNING,frozenset((278966,278967)))
        self.assertFalse(core_filter_specs_ready())
        self.assertNotIn(278966,VERIFIED_SPECS)
        self.assertNotIn(278967,VERIFIED_SPECS)

    def test_teachers_never_count_as_students(self):
        for job in TEACHER_JOBS:
            self.assertEqual(classify_job(job),'staff')
        for job in CORE_STUDENT_JOBS:
            self.assertEqual(classify_job(job),'core')
        self.assertEqual(classify_job(277894),'base')

    def test_full_spec_must_not_rewrite_original_filter(self):
        full=dict(VERIFIED_SPECS)
        full[278966]=(333333,1,1,True)
        full[278967]=(444444,1,1,True)
        self.assertTrue(verify_complete_core_jobs(full))
        full[278965]=(999999,1,1,True)
        self.assertFalse(verify_complete_core_jobs(full))

    def test_partial_or_unknown_auto_invite_is_blocked(self):
        self.assertFalse(verify_complete_core_jobs(VERIFIED_SPECS))
        full=dict(VERIFIED_SPECS)
        full[278966]=(333333,1,1,True)
        full[278967]=(444444,1,0,True)
        self.assertFalse(verify_complete_core_jobs(full))

if __name__=='__main__':
    unittest.main()
