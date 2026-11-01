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
PLAN={'status':'READY_FOR_ADAPTER','all_16':A+B,
      'classes':(A,B),'playable':(),'core':(),
      'base_invites_needed':16,'core_jobs_verified':True}

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
        # No seventeenth random situation may enter the school.
        self.assertEqual(len(instance.requests),16)
        self.assertEqual(session.issued,16)

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
        # If EA asks for a seventeenth Base pupil, refuse it rather than
        # silently spawning a random unregistered classmate.
        self.assertIsNone(instance.create_situation(
            Situation(),guest_list=EmptyEAList()))
        self.assertEqual(len(instance.requests),16)

    def test_ineligible_remaining_registered_students_never_fall_back_random(self):
        Manager=manager()
        session=SelectionSession((A,B))
        self.assertTrue(connect(Manager,session,lambda:(A[:2],()),
                                lambda:True,Job(),GuestInfo,1,full_plan=PLAN))
        instance=Manager()
        for _ in range(4):
            instance.create_situation(Situation(),guest_list=EmptyEAList())
        self.assertEqual(len(instance.requests),2)
        self.assertEqual(session.issued,2)
        self.assertEqual([guests.items[0].sim_id
                          for _,guests,_ in instance.requests],[1,2])

    def test_core_not_live_verified_blocks_hook(self):
        Manager=manager()
        session=SelectionSession((A,B))
        plan=dict(PLAN,core_jobs_verified=False)
        self.assertFalse(connect(Manager,session,lambda:(A+B,()),
                                 lambda:True,Job(),GuestInfo,1,full_plan=plan))

    def test_core_students_counted_but_never_invited_as_base(self):
        Manager=manager()
        session=SelectionSession((A,B),playable_ids=('1','9'),excluded_ids=('2','10'))
        plan=dict(PLAN,playable=('1','9'),core=('2','10'),
                  base_invites_needed=12)
        self.assertTrue(connect(Manager,session,lambda:(A+B,()),
                                lambda:True,Job(),GuestInfo,1,full_plan=plan))
        instance=Manager()
        for _ in range(12):
            instance.create_situation(Situation(),guest_list=EmptyEAList())
        selected=[guests.items[0].sim_id for _,guests,_ in instance.requests]
        self.assertEqual(len(selected),12)
        self.assertTrue(set((1,2,9,10)).isdisjoint(set(selected)))
        self.assertEqual(session.issued,12)

    def test_missing_core_exclusion_blocks_hook(self):
        Manager=manager()
        session=SelectionSession((A,B))
        plan=dict(PLAN,playable=('1','9'),core=('2','10'),
                  base_invites_needed=12)
        self.assertFalse(connect(Manager,session,lambda:(A+B,()),
                                 lambda:True,Job(),GuestInfo,1,full_plan=plan))

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
