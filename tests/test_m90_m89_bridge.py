"""M90/M89 full-cohort gating and original-request integration."""
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for p in ('src/m90_selection','src/m89_selection','src/m88_selection','src/m58_selection'):
    sys.path.insert(0,str(ROOT/p))
from mhs90_session import SelectionSession
from mhs90_m89_bridge import connect
from tests.test_m88_replace_guest import Job,Guest,List,GuestInfo,EmptyEAList
from tests.test_m89_precreate_hook import Situation,manager

A=tuple(str(i) for i in range(1,9))
B=tuple(str(i) for i in range(9,17))
PLAN={'status':'READY_FOR_ADAPTER','all_16':A+B}

class BridgeTests(unittest.TestCase):
    def test_sixteen_exact_students_in_one_school_day(self):
        Manager=manager()
        session=SelectionSession((A,B))
        self.assertTrue(connect(Manager,session,lambda:(A+B,()),lambda:True,
                                Job(),GuestInfo,1,full_plan=PLAN))
        instance=Manager()
        for _ in range(16):
            instance.create_situation(Situation(),guest_list=List([Guest(0)]))
        chosen=[g.items[0].sim_id for _,g,_ in instance.requests]
        self.assertEqual(chosen,list(range(1,17)))
        self.assertEqual(session.issued,16)
        instance.create_situation(Situation(),guest_list=List([Guest(0)]))
        self.assertEqual(instance.requests[-1][1].items[0].sim_id,0)

    def test_ea_real_empty_guest_lists_fill_all_sixteen_distinct(self):
        Manager=manager()
        session=SelectionSession((A,B))
        self.assertTrue(connect(Manager,session,lambda:(A+B,()),lambda:True,
                                Job(),GuestInfo,1,full_plan=PLAN))
        instance=Manager()
        original_lists=[]
        for _ in range(16):
            old=EmptyEAList()
            original_lists.append(old)
            instance.create_situation(Situation(),guest_list=old)
        self.assertEqual(len(instance.requests),16)
        selected=[g.items[0].sim_id for _,g,_ in instance.requests]
        self.assertEqual(selected,list(range(1,17)))
        self.assertTrue(all(g.invite_only for _,g,_ in instance.requests))
        self.assertTrue(all(len(original.items)==0 for original in original_lists))
        self.assertEqual(session.issued,16)
        # If EA still requests another base student, do not duplicate an ID.
        instance.create_situation(Situation(),guest_list=EmptyEAList())
        self.assertEqual(len(instance.requests[-1][1].items),0)

    def test_missing_full_plan_blocks_hook(self):
        Manager=manager()
        session=SelectionSession((A,B))
        self.assertFalse(connect(Manager,session,lambda:(A+B,()),
                                 lambda:True,Job(),GuestInfo,1))
        self.assertEqual(Manager().create_situation(Situation(),guest_list=List([Guest(0)])),42)

    def test_partial_manifest_blocks_hook(self):
        Manager=manager()
        session=SelectionSession((A,B))
        self.assertFalse(connect(Manager,session,lambda:(A+B,()),
                                 lambda:True,Job(),GuestInfo,1,
                                 full_plan={'status':'READY_FOR_ADAPTER','all_16':A}))

    def test_blocked_capacity_plan_never_installs(self):
        Manager=manager()
        session=SelectionSession((A,B))
        self.assertFalse(connect(Manager,session,lambda:(A+B,()),
                                 lambda:True,Job(),GuestInfo,1,
                                 full_plan={'status':'BLOCKED','all_16':A+B}))

    def test_non_school_zone_preserves_ea(self):
        Manager=manager()
        session=SelectionSession((A,B))
        self.assertTrue(connect(Manager,session,lambda:(A+B,()),
                                lambda:False,Job(),GuestInfo,1,full_plan=PLAN))
        instance=Manager()
        instance.create_situation(Situation(),guest_list=List([Guest(0)]))
        self.assertEqual(instance.requests[0][1].items[0].sim_id,0)
        self.assertEqual(session.issued,0)

if __name__=='__main__':
    unittest.main()
