"""M94 read-only current-EA job probing and Mac build source invariants."""
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'/'m94_runtime'))
from mhs94_school_job_probe import JOBS,snapshot,summary_line,_guid
from tooling.build_mhs94_probe import script_sources

class _Filter:
    def __init__(self,i):
        self.guid64=i
class _Invites:
    lower_bound=1
    upper_bound=1
class _Job:
    def __init__(self,job_id,filter_guid):
        self.guid64=job_id
        self.filter=_Filter(filter_guid)
        self.sim_auto_invite=_Invites()
        self.sim_auto_invite_allow_instanced_sim=True

class ProbeTests(unittest.TestCase):
    def test_all_original_ea_school_jobs_read_without_mutation(self):
        known={277894:280516,278965:276592,
               278966:276596,278967:276594,
               278968:276595,303765:303766}
        fake={job:_Job(job,filt) for job,filt in known.items()}
        result=snapshot(fake.get)
        self.assertEqual(result['filter_guids_observed'],6)
        self.assertEqual(len(result['jobs']),6)
        self.assertEqual({r['job_id']:r['filter_guid'] for r in result['jobs']},
                         known)
        self.assertTrue(all(row['auto_min']==1 and row['auto_max']==1
                            and row['allow_instanced'] is True for row in result['jobs']))
        self.assertEqual(len(fake),6)
        self.assertIn('6/6',summary_line(result))

    def test_missing_job_does_not_crash_or_guess(self):
        result=snapshot(lambda iid:None)
        self.assertEqual(result['filter_guids_observed'],0)
        self.assertTrue(all(x['status']=='JOB_NOT_FOUND' for x in result['jobs']))
        self.assertTrue(all('filter_guid' not in x for x in result['jobs']))

    def test_tuning_id_mismatch_not_falsely_verified(self):
        result=snapshot(lambda iid:_Job(1,2))
        self.assertEqual(result['filter_guids_observed'],0)
        self.assertTrue(all(x['status']=='JOB_ID_MISMATCH' for x in result['jobs']))

    def test_unknown_filter_is_not_counted(self):
        result=snapshot(lambda iid:_Job(iid,None))
        self.assertEqual(result['filter_guids_observed'],0)
        self.assertTrue(all(x['status']=='OBSERVED' for x in result['jobs']))

    def test_script_isolated_to_m94_and_preserves_m85_modules(self):
        names=[p.name for p in script_sources()]
        self.assertEqual(len(names),33)
        self.assertEqual(len(set(names)),33)
        self.assertIn('mhs94_school_job_probe.py',names)
        self.assertEqual(names.count('mhs55_attendance_ui.py'),1)
        m94=(ROOT/'src'/'m94_runtime'/'mhs55_attendance_ui.py').read_text()
        self.assertIn('mhs94_capture(folder)',m94)
        self.assertIn('capture_status(folder)',m94)

if __name__=='__main__':
    unittest.main()
