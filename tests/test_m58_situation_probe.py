import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'/'m58_selection'))
import mhs58_situation_probe as probe


class FakeTuning:
    def __init__(self,guid):
        self.guid64=guid


class FakeGuest:
    def __init__(self,job,sid):
        self.job_type=FakeTuning(job)
        self.sim_id=sid


class FakeList:
    def __init__(self,guests):
        self.guests=guests
    def guest_info_gen(self):
        return iter(self.guests)


class M58SituationProbeTests(unittest.TestCase):
    def setUp(self):
        probe.COUNTS.clear()
        probe.INSTALLED=False
        probe.LAST_ERROR='none'

    def test_only_known_situations_observed(self):
        self.assertIsNone(probe.describe_request(FakeTuning(12)))
        self.assertEqual(probe.describe_request(FakeTuning(277733))['kind'],'students')

    def test_counts_jobs_no_identifying_sim_ids(self):
        class Manager:
            def create_situation(self,kind,guest_list=None):
                return ('EA',kind.guid64)
        m=Manager()
        original=Manager.create_situation
        self.assertTrue(probe.install_probe(Manager))
        self.assertTrue(probe.install_probe(Manager))
        guests=FakeList([FakeGuest(277894,34567),FakeGuest(277894,0)])
        self.assertEqual(m.create_situation(FakeTuning(277733),guests),('EA',277733))
        self.assertEqual(m.create_situation(FakeTuning(12),guests),('EA',12))
        report=probe.status()['counts'][277733]
        self.assertEqual(report['calls'],1)
        self.assertEqual(report['explicit'],1)
        self.assertEqual(report['unassigned'],1)
        self.assertEqual(report['jobs'],{277894:2})
        self.assertNotIn('34567',str(probe.status()))
        self.assertNotEqual(original,Manager.create_situation)

    def test_kwargs_and_empty_guest_list(self):
        class Manager:
            def create_situation(self,kind,guest_list=None):
                return guest_list
        probe.install_probe(Manager)
        x=FakeList([FakeGuest(278223,0)])
        self.assertIs(Manager().create_situation(FakeTuning(298096),guest_list=x),x)
        self.assertEqual(probe.status()['counts'][298096]['jobs'],{278223:1})

    def test_probe_does_not_break_ea_on_bad_guest(self):
        class Broken:
            def guest_info_gen(self):
                raise RuntimeError('bad guest list')
        class Manager:
            def create_situation(self,kind,guest_list=None):
                return 'retained'
        probe.install_probe(Manager)
        self.assertEqual(Manager().create_situation(FakeTuning(277733),Broken()),'retained')
        self.assertEqual(probe.LAST_ERROR,'RuntimeError')

    def test_no_autoinstall(self):
        source=(Path(__file__).resolve().parents[1]/'src'/'m58_selection'/'mhs58_situation_probe.py').read_text()
        self.assertNotIn('install_probe(SituationManager)',source)


if __name__=='__main__':
    unittest.main()
