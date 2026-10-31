import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'/'m58_selection'))
from mhs61_guest_adapter import build_guest_list,create_one_existing_student

class Guest:
    def __init__(self,invite_only=False):
        self.invite_only=invite_only
        self.items=[]
    def add_guest_info(self,info):
        self.items.append(info)
class GuestInfo:
    @staticmethod
    def construct_from_purpose(sid,job,purpose):
        return (sid,job.guid64,purpose)
class Manager:
    def __init__(self):
        self.calls=[]
    def create_situation(self,*a,**kw):
        self.calls.append((a,kw))
        return 71
class M61GuestAdapterTests(unittest.TestCase):
    def test_single_verified_guest_invitation(self):
        m=Manager()
        s=SimpleNamespace(guid64=277733)
        j=SimpleNamespace(guid64=277894)
        result=create_one_existing_student(m,s,j,10001,Guest,GuestInfo,1)
        self.assertEqual(result,71)
        self.assertEqual(len(m.calls),1)
        self.assertEqual(m.calls[0][1]['guest_list'].items,[(10001,277894,1)])
        self.assertTrue(m.calls[0][1]['guest_list'].invite_only)
        self.assertFalse(m.calls[0][1]['user_facing'])
    def test_invalid_guid_and_sim_id_cannot_call_ea(self):
        for situation,job,sid in ((1,277894,100),(277733,1,100),(277733,277894,0),(277733,277894,True)):
            m=Manager()
            with self.assertRaises(ValueError):
                create_one_existing_student(m,SimpleNamespace(guid64=situation),SimpleNamespace(guid64=job),sid,Guest,GuestInfo,1)
            self.assertEqual(m.calls,[])
if __name__=='__main__':
    unittest.main()
