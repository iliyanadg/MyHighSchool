"""M89 integration seam: prove EA gets modified list on same request."""
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for p in ('src/m89_selection','src/m88_selection','src/m58_selection'):
    sys.path.insert(0,str(ROOT/p))
from mhs89_precreate_hook import install
from tests.test_m88_replace_guest import Job,Guest,List,GuestInfo
class Situation:
    guid64=277733
class Other:
    guid64=298052

def manager():
    class Manager:
        def __init__(self):
            self.requests=[]
        def create_situation(self,kind,guest_list=None,user_facing=True):
            self.requests.append((kind,guest_list,user_facing))
            return 42
    return Manager

class M89Tests(unittest.TestCase):
    def test_same_call_receives_enrolled_id_without_extra_situation(self):
        Manager=manager()
        self.assertTrue(install(Manager,lambda *args:(555,True,True),Job(),GuestInfo,1))
        instance=Manager()
        original=List([Guest(0)])
        self.assertEqual(instance.create_situation(Situation(),guest_list=original,user_facing=False),42)
        self.assertEqual(len(instance.requests),1)
        self.assertEqual([x.sim_id for x in instance.requests[0][1].items],[555])
        self.assertEqual([x.sim_id for x in original.items],[0])
        self.assertFalse(instance.requests[0][2])
    def test_outside_school_never_changes(self):
        Manager=manager()
        self.assertTrue(install(Manager,lambda *args:(555,True,True),Job(),GuestInfo,1))
        instance=Manager()
        initial=List([Guest(0)])
        instance.create_situation(Other(),guest_list=initial)
        self.assertIs(instance.requests[0][1],initial)
    def test_explicit_ea_guest_preserved(self):
        Manager=manager()
        self.assertTrue(install(Manager,lambda *args:(555,True,True),Job(),GuestInfo,1))
        instance=Manager()
        instance.create_situation(Situation(),guest_list=List([Guest(77)]))
        self.assertEqual(instance.requests[0][1].items[0].sim_id,77)
    def test_fail_closed_resolver(self):
        Manager=manager()
        def broken(*args):raise RuntimeError('unavailable')
        self.assertTrue(install(Manager,broken,Job(),GuestInfo,1))
        instance=Manager()
        instance.create_situation(Situation(),guest_list=List([Guest(0)]))
        self.assertEqual(instance.requests[0][1].items[0].sim_id,0)
if __name__=='__main__':
    unittest.main()
