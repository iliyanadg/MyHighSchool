"""M28 three-class and package invariant tests (offline only)."""
import sys
import unittest
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'/'m2_registry'))
from mhs_m2_roster import SchoolRoster, RosterError
from tooling.build_m28_bundle import package_bytes, PICKER_3, CONFIRM_3, REMOVE_3
from tooling.build_m27_removal import package_bytes as previous_package
from tooling.simdata_release_gate import resources
from tooling.m1_links_and_strings import parse_stbl


class ThreeClassTests(unittest.TestCase):
    def test_third_class_loads_in_old_schema(self):
        r=SchoolRoster('3',{'10':1,'20':2})
        x,_=r.assign_many(3,['30','31'],lambda s:True)
        self.assertEqual(x.class_members(3),['30','31'])
        self.assertEqual(SchoolRoster.from_json(x.to_json()).assignments,x.assignments)

    def test_capacity_three_classes(self):
        r=SchoolRoster('3')
        for klass,start in ((1,1),(2,11),(3,21)):
            r,_=r.assign_many(klass,list(range(start,start+8)),lambda s:True)
        self.assertEqual(len(r.assignments),24)
        for klass in (1,2,3):
            with self.assertRaises(RosterError):
                r.assign_many(klass,[99],lambda s:True)

    def test_full_class_exchange(self):
        r=SchoolRoster('3',{str(i):1 for i in range(1,9)})
        r,_=r.assign_many(2,list(range(11,19)),lambda s:True)
        new,_=r.swap_students('1','11',lambda s:True)
        self.assertEqual(len(new.class_members(1)),8)
        self.assertEqual(len(new.class_members(2)),8)
        self.assertEqual(new.assignments['1'],2)
        self.assertEqual(new.assignments['11'],1)
        self.assertEqual(r.assignments['1'],1)

    def test_invalid_exchange_does_not_mutate(self):
        r=SchoolRoster('3',{'1':1,'2':1,'3':2})
        old=r.to_json()
        for a,b in ((1,2),(1,9),(1,1)):
            with self.assertRaises(RosterError):
                r.swap_students(a,b,lambda s:True)
        self.assertEqual(r.to_json(),old)


class PackageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows=resources(package_bytes())
        cls.old=resources(previous_package())

    def test_new_tunings_and_originals(self):
        self.assertEqual(len(self.rows),14)
        for before,now in zip(self.old,self.rows):
            self.assertEqual(before[:3],now[:3])
            if before[0]==0xE882D22F:
                self.assertEqual(before,now)

    def test_third_class_picker_and_confirmation(self):
        roots={key:ET.fromstring(raw) for t,g,key,raw in self.rows
               if t==0xE882D22F}
        self.assertEqual(roots[PICKER_3].get('c'),'SimPickerInteraction')
        self.assertEqual(roots[CONFIRM_3].get('c'),'MHS28StageConfirmClass3')
        self.assertEqual(roots[REMOVE_3].get('c'),'MHS28RemoveClass3')
        ref=roots[PICKER_3].find('./L[@n="actor_continuation"]/U/T[@n="affordance"]')
        self.assertEqual(ref.text,str(CONFIRM_3))

    def test_class3_menu_and_languages(self):
        root=next(ET.fromstring(raw) for t,g,i,raw in self.rows if t==0x7DF2169C)
        ids={int(n.text) for n in root.findall('.//L[@n="_super_affordances"]/T')}
        self.assertIn(PICKER_3,ids)
        self.assertIn(REMOVE_3,ids)
        self.assertNotIn(CONFIRM_3,ids)
        for t,g,i,raw in self.rows:
            if t==0x220557DA:
                strings=parse_stbl(raw)
                self.assertEqual(len(strings),15)
                self.assertIn('M28',strings[0x3FCE8D06])


if __name__=='__main__':
    unittest.main()
