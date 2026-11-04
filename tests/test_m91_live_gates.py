import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'/'m91_runtime'))
from mhs91_live_gates import verified_candidates,can_use_school_roster

class Sim:
    def __init__(self,sid,age='teen',species='human',present=False):
        self.sim_id=sid
        self.age=age
        self.species=species
        self.present=present
    def get_sim_instance(self):
        return object() if self.present else None

class Manifest:
    class_ids=(tuple(str(i) for i in range(1,9)),
               tuple(str(i) for i in range(9,17)))
    all_student_ids=frozenset(str(i) for i in range(1,17))
    active_household_teens=frozenset(('1','9'))

class M91Tests(unittest.TestCase):
    def test_roster_only_excludes_playable_and_finds_present(self):
        r=verified_candidates(Manifest(),[Sim(i,present=i==3) for i in range(1,19)],'teen','human')
        self.assertEqual(len(r[0]),14)
        self.assertEqual(r[1],('3',))
    def test_fail_closed_ea_filter_and_capacity(self):
        args=[Manifest(),True,True,True,True]
        self.assertTrue(can_use_school_roster(*args))
        for k in range(1,5):
            modified=list(args)
            modified[k]=False
            self.assertFalse(can_use_school_roster(*modified))
if __name__=='__main__':
    unittest.main()
