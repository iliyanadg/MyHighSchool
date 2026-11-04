import unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'/'m136_player_tests'))
from mhs136_player_test_hierarchy import inspect_test_hierarchy

class SituationJobTest:
    def __init__(self):
        self.situation_jobs=[280777]
class TestList(list): pass
class Affordance:
    def __init__(self):
        self.test_globals=TestList([SituationJobTest()])
class Board:
    id=10
class TestM136(unittest.TestCase):
    def test_reports_actual_job_test_without_world_mutations(self):
        played=[{'sim_id':'1','registered_class':2},
                {'sim_id':'2','registered_class':1}]
        result=inspect_test_hierarchy(Affordance(),played,{1:[Board()],2:[Board()]})
        self.assertEqual(result['game_mutations'],0)
        self.assertTrue(result['no_test_bypassed'])
        self.assertTrue(result['no_ea_push'])
        matches=[x for x in result['nodes'] if 'SituationJobTest' in x['type']]
        self.assertEqual(len(matches),1)
        self.assertIn('280777',matches[0]['fields']['situation_jobs'])
    def test_bounded_scan_cyclic_data(self):
        obj=[]
        obj.append(obj)
        result=inspect_test_hierarchy(obj,[],{1:[],2:[]})
        self.assertFalse(result['truncated'])
        self.assertEqual(len(result['nodes']),1)
if __name__=='__main__':unittest.main()
