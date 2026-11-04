import unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'/'m132_player_diagnosis'))
from mhs132_native_player_test_audit import inspect_native_player_tests


class FakeResult:
    def __init__(self,passed,reason):
        self.passed=passed
        self.reason=reason
    def __bool__(self):
        return self.passed
    def __str__(self):
        return 'EA_TEST_'+self.reason


class Affordance:
    def test(self,target,context):
        return FakeResult(context.sim.accepted,
                          'OK' if context.sim.accepted else 'ROLE_MISSING')


class Sim:
    def __init__(self,accepted):
        self.accepted=accepted
        self.queue=type('Queue',(),{'running':None})()
    def has_buff(self,buff): return self.accepted


class Info:
    def __init__(self,sim):self.sim=sim
    def get_sim_instance(self):return self.sim


class Context:
    def __init__(self,sim):self.sim=sim


class Tests(unittest.TestCase):
    def test_reports_distinct_ea_test_failures_without_mutation(self):
        played=[
            {'sim_id':'1','registered_class':1,'sim_info':Info(Sim(True))},
            {'sim_id':'9','registered_class':2,'sim_info':Info(Sim(False))},
        ]
        report=inspect_native_player_tests(
            played,{1:[object()],2:[object()]},Affordance(),
            object(),Context)
        self.assertEqual(report['game_mutations'],0)
        self.assertEqual(report['students'][0]['test_passed'],True)
        self.assertEqual(report['students'][1]['test_passed'],False)
        self.assertEqual(report['students'][1]['reason'],'ROLE_MISSING')
        self.assertEqual(report['students'][1]['player_role_buff'],False)

    def test_missing_affordance_does_not_push(self):
        played=[{'sim_id':'1','registered_class':1,
                 'sim_info':Info(Sim(True))}]
        report=inspect_native_player_tests(
            played,{1:[object()],2:[object()]},None,None,Context)
        self.assertEqual(report['students'][0]['status'],
                         'MISSING_SIM_BOARD_OR_AFFORDANCE')

    def test_unavailable_ea_test_is_reported_without_guessing(self):
        played=[{'sim_id':'1','registered_class':1,
                 'sim_info':Info(Sim(True))}]
        report=inspect_native_player_tests(
            played,{1:[object()]},object(),None,Context)
        self.assertEqual(report['students'][0]['status'],
                         'AFFORDANCE_TEST_UNAVAILABLE')


if __name__=='__main__':
    unittest.main()
