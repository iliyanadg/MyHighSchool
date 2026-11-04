"""M134 no mutation: actual EA jobs of Class1 and Class2 players."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'/'m134_jobs'))
from mhs134_native_player_job_audit import inspect_player_jobs

class Job:
    def __init__(self,guid):self.guid64=guid
class Situation:
    def __init__(self,guid,job):self.guid64=guid;self.job=Job(job)
    def get_current_job_for_sim(self,sim):return self.job
class Sim:pass
class Info:
    def get_sim_instance(self):return Sim()
class Manager:
    def get_situations_sim_is_in(self,sim):
        return [Situation(304567,280777),
                Situation(297774,277919),
                Situation(999001,10001)]

class Tests(unittest.TestCase):
    def test_reports_actual_job_guids_not_assumptions(self):
        played=[{'sim_id':'123','registered_class':2,'sim_info':Info()}]
        r=inspect_player_jobs(played,Manager(),None)
        self.assertEqual(r['game_mutations'],0)
        self.assertEqual(
            [(x['situation_guid'],x['job_guid'])
             for x in r['students'][0]['situation_jobs']],
            [(304567,280777),(297774,277919)])
        self.assertTrue(r['job_requirement_not_inferred'])

    def test_unsupported_membership_reader_is_explicit(self):
        played=[{'sim_id':'124','registered_class':1,'sim_info':Info()}]
        r=inspect_player_jobs(played,object(),None)
        self.assertEqual(r['students'][0]['status'],
                         'NO_SIM_OR_MEMBERSHIP_API')

if __name__=='__main__':unittest.main()
