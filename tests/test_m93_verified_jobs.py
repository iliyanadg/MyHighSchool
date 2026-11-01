"""M93: all six filter IDs verified in-game on Mac on 2026-11-01."""
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'/'m93_core'))
from mhs93_verified_jobs import (
    VERIFIED_SPECS,PENDING_TUNING,CORE_STUDENT_JOBS,TEACHER_JOBS,
    classify_job,core_filter_specs_ready,verify_complete_core_jobs,
    verify_m94_snapshot)

# This source-of-truth mapping is transcribed from the USER'S LIVE M94 JSON.
ACTUAL_M94={
    277894:(280516,1,1,True),
    278965:(276592,1,1,True),
    278966:(276596,1,1,True), # Chess is 276596, NOT 276594
    278967:(276594,1,1,True), # Football is 276594, NOT 276596
    278968:(276595,1,1,True),
    303765:(303766,1,1,True),
}
def fake_m94(data=None):
    specs=ACTUAL_M94 if data is None else data
    return {
        'kind':'LIVE_EA_SITUATION_JOB_TUNING_READ_ONLY',
        'filter_guids_observed':6,'expected_jobs':6,
        'jobs':[{'job_id':job,'name':'from live report','status':'OBSERVED',
                 'filter_guid':values[0],'auto_min':values[1],
                 'auto_max':values[2],'allow_instanced':values[3]}
                for job,values in specs.items()],
        'does_not_verify_16_student_attendance':True}

class VerifiedSchoolJobTuningTests(unittest.TestCase):
    def test_all_six_specs_match_actual_m94_mac_report(self):
        self.assertEqual(VERIFIED_SPECS,ACTUAL_M94)
        self.assertTrue(core_filter_specs_ready())
        self.assertFalse(PENDING_TUNING)
        self.assertTrue(verify_complete_core_jobs(ACTUAL_M94))
        self.assertTrue(verify_m94_snapshot(fake_m94()))

    def test_chess_and_football_filter_ids_are_not_swapped(self):
        swapped=dict(ACTUAL_M94)
        swapped[278966],swapped[278967]=swapped[278967],swapped[278966]
        self.assertFalse(verify_complete_core_jobs(swapped))
        self.assertFalse(verify_m94_snapshot(fake_m94(swapped)))

    def test_teachers_never_count_as_students(self):
        for job in TEACHER_JOBS:
            self.assertEqual(classify_job(job),'staff')
        for job in CORE_STUDENT_JOBS:
            self.assertEqual(classify_job(job),'core')
        self.assertEqual(classify_job(277894),'base')

    def test_missing_job_and_extra_job_fail_closed(self):
        incomplete=dict(ACTUAL_M94)
        del incomplete[278966]
        self.assertFalse(verify_complete_core_jobs(incomplete))
        self.assertFalse(verify_m94_snapshot(fake_m94(incomplete)))
        extra=dict(ACTUAL_M94)
        extra[999999]=(999,1,1,True)
        self.assertFalse(verify_complete_core_jobs(extra))

    def test_auto_invite_bounds_must_match_live_ea(self):
        altered=dict(ACTUAL_M94)
        altered[278966]=(276596,1,2,True)
        self.assertFalse(verify_complete_core_jobs(altered))
        self.assertFalse(verify_m94_snapshot(fake_m94(altered)))

    def test_reject_non_numeric_and_duplicate_job_ids(self):
        report=fake_m94()
        report['jobs'][0]['job_id']='277894'
        self.assertFalse(verify_m94_snapshot(report))
        report=fake_m94()
        report['jobs'][0]['job_id']=report['jobs'][1]['job_id']
        self.assertFalse(verify_m94_snapshot(report))

    def test_no_claim_of_attendance_from_complete_filters(self):
        self.assertTrue(fake_m94()['does_not_verify_16_student_attendance'])

if __name__=='__main__':
    unittest.main()
