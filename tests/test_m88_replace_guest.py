"""M88 single-slot EA situation guest replacement safety checks."""
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for path in ('src/m88_selection','src/m58_selection'):
    sys.path.insert(0,str(ROOT/path))
from mhs88_replace_guest import (replace_unassigned_guest,
    build_guest_for_empty_ea_request)

class Job:
    guid64=277894
class Guest:
    def __init__(self,sid,job=None):
        self.sim_id=sid
        self.job_type=job or Job()
class List:
    def __init__(self,items):
        self.items=list(items)
    def guest_info_gen(self):
        return iter(self.items)
    def clone(self):
        return List(self.items)
    def remove_guest_info(self,item):
        self.items.remove(item)
    def add_guest_info(self,item):
        self.items.append(item)
class EmptyEAList:
    def __init__(self,invite_only=False):
        self.items=[]
        self.invite_only=invite_only
    def guest_info_gen(self):
        return iter(self.items)
    def add_guest_info(self,item):
        self.items.append(item)

class GuestInfo:
    @staticmethod
    def construct_from_purpose(sid,job,purpose):
        return Guest(sid,job)

def run(old,**changes):
    kw=dict(situation_guid=277733,guest_list=old,student_id=555,
            job_tuning=Job(),guest_info_cls=GuestInfo,purpose=1,
            verified_school_zone=True,active=True)
    kw.update(changes)
    return replace_unassigned_guest(**kw)

class M88Tests(unittest.TestCase):
    def test_replaces_only_unassigned_guest_in_clone(self):
        original=List([Guest(0)])
        replacement=run(original)
        self.assertIsNotNone(replacement)
        self.assertEqual([x.sim_id for x in original.items],[0])
        self.assertEqual([x.sim_id for x in replacement.items],[555])
    def test_real_ea_schedule_empty_guest_list_fills_one_registered(self):
        original=EmptyEAList()
        replacement=build_guest_for_empty_ea_request(
            277733,original,555,Job(),GuestInfo,1,True,True)
        self.assertIsNotNone(replacement)
        self.assertTrue(replacement.invite_only)
        self.assertEqual([g.sim_id for g in replacement.items],[555])
        self.assertEqual(original.items,[])
    def test_empty_request_never_modified_when_not_school(self):
        original=EmptyEAList()
        self.assertIsNone(build_guest_for_empty_ea_request(
            298052,original,555,Job(),GuestInfo,1,True,True))
        self.assertIsNone(build_guest_for_empty_ea_request(
            277733,original,555,Job(),GuestInfo,1,False,True))
        self.assertIsNone(build_guest_for_empty_ea_request(
            277733,original,555,Job(),GuestInfo,1,True,False))
        self.assertEqual(original.items,[])
    def test_nonempty_guest_list_is_not_double_invited(self):
        original=EmptyEAList()
        original.add_guest_info(Guest(90))
        self.assertIsNone(build_guest_for_empty_ea_request(
            277733,original,555,Job(),GuestInfo,1,True,True))
    def test_ea_existing_explicit_guest_never_overwritten(self):
        self.assertIsNone(run(List([Guest(44)])))
    def test_verified_ea_random_explicit_can_be_replaced(self):
        original=List([Guest(99)])
        new=run(original,ea_generated_explicit=True,registered_ids=('555','123'))
        self.assertIsNotNone(new)
        self.assertEqual(new.items[0].sim_id,555)
        self.assertEqual(original.items[0].sim_id,99)
    def test_registered_ea_explicit_never_replaced(self):
        self.assertIsNone(run(List([Guest(99)]),
                          ea_generated_explicit=True,registered_ids=('99','555')))
    def test_wrong_job_situation_zone_or_activation_noop(self):
        self.assertIsNone(run(List([Guest(0)]),situation_guid=298052))
        self.assertIsNone(run(List([Guest(0)]),verified_school_zone=False))
        self.assertIsNone(run(List([Guest(0)]),active=False))
    def test_no_extra_guests_or_duplicate_situations(self):
        self.assertIsNone(run(List([Guest(0),Guest(0)])))
        s=(ROOT/'src'/'m88_selection'/'mhs88_replace_guest.py').read_text()
        self.assertNotIn('create_situation(',s)
        self.assertNotIn('import services',s)
if __name__=='__main__':
    unittest.main()
