"""M88 single-slot EA situation guest replacement safety checks."""
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for path in ('src/m88_selection','src/m58_selection'):
    sys.path.insert(0,str(ROOT/path))
from mhs88_replace_guest import replace_unassigned_guest

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
    def test_ea_existing_explicit_guest_never_overwritten(self):
        self.assertIsNone(run(List([Guest(44)])))
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
