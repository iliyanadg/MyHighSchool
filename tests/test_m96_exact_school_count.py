"""M96: deterministic Base situation scheduler count, verified 8+8 only."""
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'/'m96_scheduler'))
from mhs96_exact_school_count import approved_base_count,install

A=tuple(str(i) for i in range(1,9))
B=tuple(str(i) for i in range(9,17))
def plan(playable=(),core=()):
    played=set(playable)
    special=set(core)
    normal=tuple(x for x in A+B if x not in played|special)
    return dict(status='READY_FOR_ADAPTER',core_jobs_verified=True,
                classes=(A,B),all_16=A+B,
                playable=tuple(playable),core=tuple(core),
                normal_npcs=normal,
                base_invites_needed=len(normal))

def fake_schedule():
    class WeeklyDay:
        calls=0
        @classmethod
        def get_long_term_situation_count(cls,data,resolver):
            cls.calls+=1
            return (6,6)
    class Main(WeeklyDay):
        guid64=277657
    class Venue(WeeklyDay):
        guid64=279958
    class Other(WeeklyDay):
        guid64=999999
    class Situation:
        guid64=277733
    class StaffSituation:
        guid64=298096
    class Data:
        def __init__(self,situation):
            self.situation=situation
    return WeeklyDay,Main,Venue,Other,Data(Situation()),Data(StaffSituation())

class SchoolCountTests(unittest.TestCase):
    def test_plain_roster_16_uses_exact_sixteen_not_vanilla_random_six(self):
        self.assertEqual(approved_base_count(277657,277733,plan()),(16,16))

    def test_playable_and_core_are_not_double_counted(self):
        self.assertEqual(approved_base_count(277657,277733,
                         plan(('1','9'),('2','3','4','10','11'))),(9,9))

    def test_unverified_five_core_roles_are_never_assumed(self):
        data=plan(('1','9'),('2','10'))
        data['core_jobs_verified']=False
        self.assertIsNone(approved_base_count(277657,277733,data))

    def test_partial_roster_or_invalid_base_count_blocked(self):
        for change in ({'base_invites_needed':11},
                       {'classes':(A,B[:7])},
                       {'all_16':A+A},
                       {'normal_npcs':A[:3]},
                       {'status':'BLOCKED'}):
            self.assertIsNone(approved_base_count(277657,277733,
                                                  dict(plan(),**change)))

    def test_wrong_zone_schedule_and_staff_situation_never_modified(self):
        self.assertIsNone(approved_base_count(444444,277733,plan()))
        self.assertIsNone(approved_base_count(277657,298096,plan()))

    def test_main_and_venue_schedule_receive_exact_count(self):
        Day,Main,Venue,Other,data,staff=fake_schedule()
        self.assertTrue(install(Day,lambda c,d,r:plan(('1','9'),('2','10'))))
        self.assertEqual(Main.get_long_term_situation_count(data,None),(12,12))
        self.assertEqual(Venue.get_long_term_situation_count(data,None),(12,12))
        self.assertEqual(Other.get_long_term_situation_count(data,None),(6,6))
        self.assertEqual(Main.get_long_term_situation_count(staff,None),(6,6))
        self.assertFalse(install(Day,lambda c,d,r:plan()))
        self.assertEqual(Main.calls,2)
        self.assertEqual(Venue.calls,1)
        self.assertEqual(Other.calls,1)

    def test_provider_error_preserves_vanilla_count(self):
        Day,Main,Venue,Other,data,staff=fake_schedule()
        def exploding(*args):
            raise RuntimeError('EA not ready')
        self.assertTrue(install(Day,exploding))
        self.assertEqual(Main.get_long_term_situation_count(data,None),(6,6))

    def test_gate_blocks_unregistered_extra_core_students(self):
        p=plan(('1','9'),('2','10'))
        p['core']=('2','99')
        self.assertIsNone(approved_base_count(277657,277733,p))

    def test_no_hook_on_unverified_class(self):
        class Other:
            def get_long_term_situation_count(self,data,resolver):
                return (6,6)
        self.assertFalse(install(Other,lambda *a:plan()))

if __name__=='__main__':
    unittest.main()
