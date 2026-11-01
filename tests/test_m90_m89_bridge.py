"""M90/M89 integration: same EA calls, distinct enrolled students."""
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for p in ('src/m90_selection','src/m89_selection','src/m88_selection','src/m58_selection'):
    sys.path.insert(0,str(ROOT/p))
from mhs90_session import SelectionSession
from mhs90_m89_bridge import connect
from tests.test_m88_replace_guest import Job,Guest,List,GuestInfo
from tests.test_m89_precreate_hook import Situation,manager

class BridgeTests(unittest.TestCase):
    def test_two_ea_requests_choose_two_distinct_registered(self):
        Manager=manager()
        session=SelectionSession((('10','20'),('30','40')))
        self.assertTrue(connect(Manager,session,lambda:(('10','20','30','40'),()),
                                lambda:True,Job(),GuestInfo,1))
        instance=Manager()
        instance.create_situation(Situation(),guest_list=List([Guest(0)]))
        instance.create_situation(Situation(),guest_list=List([Guest(0)]))
        self.assertEqual([g.items[0].sim_id for _,g,_ in instance.requests],[10,20])
        self.assertEqual(session.issued,2)
    def test_no_verified_school_preserves_ea(self):
        Manager=manager()
        session=SelectionSession((('10',),))
        connect(Manager,session,lambda:(('10',),()),lambda:False,Job(),GuestInfo,1)
        instance=Manager()
        instance.create_situation(Situation(),guest_list=List([Guest(0)]))
        self.assertEqual(instance.requests[0][1].items[0].sim_id,0)
        self.assertEqual(session.issued,0)
if __name__=='__main__':
    unittest.main()
