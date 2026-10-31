"""M57 tests: one source of truth for selected students and school staff."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'/'m57_selection'))
sys.path.insert(0, str(ROOT/'src'/'m2_registry'))
sys.path.insert(0, str(ROOT/'src'/'m53_staff'))

from mhs_m2_roster import SchoolRoster
from mhs53_staff_store import StaffRoster
from mhs57_school_manifest import make_manifest, ManifestError


def configured_staff(slot=11):
    return StaffRoster(slot, {
        'principal':'201',
        'teacher1':'202',
        'teacher2':'203',
        'teacher3':None,
        'cafeteria':['204','205','206'],
        'custodians':['207','208']
    })


class ManifestTests(unittest.TestCase):
    def setUp(self):
        self.roster = SchoolRoster(11,{
            str(i):(1 if i <= 8 else 2) for i in range(1,17)})
        self.staff = configured_staff()

    def test_two_full_classes_and_playable_not_autoclassed(self):
        m=make_manifest(self.roster,self.staff,2,('17','18','19'))
        self.assertEqual(m.capacity,16)
        self.assertEqual(m.selected_count,16)
        self.assertEqual(len(m.to_invite),16)
        self.assertEqual(m.playable_unenrolled,frozenset(('17','18','19')))
        self.assertIsNone(m.class_of('17'))
        self.assertEqual(m.class_of('12'),2)

    def test_three_playables_count_within_class_limit(self):
        r=SchoolRoster(11,{
            '17':1,'18':1,'19':2,
            '1':1,'2':1,'3':1,'4':1,'5':1,'6':1,
            '9':2,'10':2,'11':2,'12':2,'13':2,'14':2,'15':2
        })
        m=make_manifest(r,self.staff,2,('17','18','19'))
        self.assertEqual(m.selected_count,16)
        self.assertEqual(len(m.to_invite),13)
        self.assertEqual(len(m.playable_in_classes),3)
        self.assertEqual(m.playable_unenrolled,frozenset())
        self.assertEqual(tuple(len(c) for c in m.class_ids),(8,8))

    def test_staff_selected_role_matching(self):
        m=make_manifest(self.roster,self.staff,2,())
        self.assertTrue(m.match_staff('principal',201))
        self.assertTrue(m.match_staff('teacher1',202))
        self.assertFalse(m.match_staff('teacher2',202))
        self.assertEqual(m.staff_ids['cafeteria'],('204','205','206'))
        self.assertEqual(m.staff_ids['custodians'],('207','208'))

    def test_observed_ea_students_not_equal_registered(self):
        m=make_manifest(self.roster,self.staff,2,('17','18','19'))
        report=m.compare_live_ids(
            ['3','6','9','11','17','19','90','91'],
            {'principal':['300'],'teacher1':['301'],'teacher2':['302'],
             'custodians':['303'],'cafeteria':['304']})
        self.assertEqual(report['registered_total'],16)
        self.assertEqual(report['physical_registered'],4)
        self.assertEqual(report['missing_registered'][:3],('1','2','4'))
        self.assertEqual(report['physical_unregistered'],('17','19','90','91'))
        self.assertEqual(report['physical_registered_per_class'],(2,2))
        self.assertEqual(report['staff']['principal']['missing_configured'],('201',))
        self.assertEqual(report['staff']['principal']['physical_unassigned'],('300',))

    def test_wrong_save_rejected(self):
        with self.assertRaises(ManifestError):
            make_manifest(self.roster,configured_staff(12),2,())

    def test_does_not_allow_staff_to_be_student(self):
        r=SchoolRoster(11,{'201':1})
        with self.assertRaises(ManifestError):
            make_manifest(r,self.staff,2,())

    def test_three_classes_allowed_not_more(self):
        r=SchoolRoster(11,{str(i):(1 if i<=8 else 2 if i<=16 else 3)
                           for i in range(1,25)})
        m=make_manifest(r,self.staff,3,())
        self.assertEqual(m.capacity,24)
        self.assertEqual(m.selected_count,24)
        with self.assertRaises(ManifestError):
            make_manifest(r,self.staff,4,())

    def test_manifest_never_changes_registry(self):
        roster_before=self.roster.to_json()
        staff_before=self.staff.to_json()
        m=make_manifest(self.roster,self.staff,2,('17',))
        m.compare_live_ids(['3','15','99'])
        self.assertEqual(roster_before,self.roster.to_json())
        self.assertEqual(staff_before,self.staff.to_json())


if __name__=='__main__':
    unittest.main()
