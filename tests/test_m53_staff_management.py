"""M53 school staff: registry, class caps, category binary and action wiring."""
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
import struct

ROOT=Path(__file__).resolve().parents[1]
REG=ROOT/'src'/'m2_registry'
STAFF=ROOT/'src'/'m53_staff'
for path in (REG,STAFF):
    if str(path) not in sys.path:
        sys.path.insert(0,str(path))

from mhs53_staff_store import StaffError,StaffRoster,StaffStore,plan_staff,CAP
from tooling.build_m53_staff_management import (
    package_bytes,transformed_resources,CAT_IDS,NAMES,CAT_LABELS,
    ACTIONS,ACTION_IDS,ACTION_KEYS,SCRIPTS,_fnv1_lower32,MATCHED_ROOT)
from tooling.build_m52_removal_and_settings import package_bytes as m52_package
from tooling.simdata_release_gate import resources,inspect_bytes
from tooling.build_m41_complete_menu import CATEGORY_TYPE,SIMDATA_TYPE,SIMDATA_GROUP
from tooling.build_m27_removal import TYPE_INTERACTION,TYPE_STBL,TYPE_SNIPPET
from tooling.m1_links_and_strings import parse_stbl


class RegistryTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store=StaffStore(self.tmp.name)
        self.adult=lambda sid:True

    def test_defaults_and_one_principal_teacher_per_class(self):
        roster=self.store.load(11)
        self.assertEqual(roster.to_dict()['schema'],1)
        self.assertEqual(roster.members('principal'),())
        updated,p=plan_staff(roster,'principal','assign',['101'],self.adult)
        self.assertEqual(updated.members('principal'),('101',))
        self.assertEqual(roster.members('principal'),())
        updated,_=plan_staff(updated,'teacher1','assign',['201'],self.adult)
        updated,_=plan_staff(updated,'teacher2','assign',['202'],self.adult)
        updated,_=plan_staff(updated,'teacher3','assign',['203'],self.adult)
        self.assertEqual(updated.members('teacher1'),('201',))
        self.assertEqual(updated.members('teacher3'),('203',))
        self.store.save('11',updated)
        self.assertEqual(self.store.load('11').members('principal'),('101',))
        self.assertEqual(self.store.load('11').members('teacher3'),('203',))
        self.assertEqual(self.store.load('12').members('teacher3'),())

    def test_replacement_is_manual_and_old_sim_freed(self):
        roster=StaffRoster('11')
        a,_=plan_staff(roster,'principal','assign',['101'],self.adult)
        b,_=plan_staff(a,'principal','assign',['102'],self.adult)
        self.assertEqual(b.members('principal'),('102',))
        self.assertNotIn('101',b.all_ids())
        c,_=plan_staff(b,'teacher1','assign',['101'],self.adult)
        self.assertEqual(c.members('teacher1'),('101',))

    def test_no_double_role_and_only_eligible_adults(self):
        roster=StaffRoster('11')
        a,_=plan_staff(roster,'teacher1','assign',['101'],self.adult)
        with self.assertRaises(StaffError):
            plan_staff(a,'principal','assign',['101'],self.adult)
        with self.assertRaises(StaffError):
            plan_staff(a,'teacher2','assign',['202'],lambda sid:False)
        self.assertEqual(a.members('teacher2'),())

    def test_cafeteria_three_and_custodians_two(self):
        roster=StaffRoster('11')
        a,result=plan_staff(roster,'cafeteria','assign',
                            ('101','102','103'),self.adult)
        self.assertEqual(result['count'],3)
        self.assertEqual(result['limit'],3)
        with self.assertRaises(StaffError):
            plan_staff(a,'cafeteria','assign',['104'],self.adult)
        b,p=plan_staff(a,'custodians','assign',('201','202'),self.adult)
        self.assertEqual(p['count'],2)
        with self.assertRaises(StaffError):
            plan_staff(b,'custodians','assign',['203'],self.adult)
        self.assertEqual(b.members('cafeteria'),('101','102','103'))
        self.assertEqual(b.members('custodians'),('201','202'))

    def test_multiple_remove_and_reenroll_existing_sim(self):
        roster=StaffRoster('11')
        a,_=plan_staff(roster,'cafeteria','assign',
                       ('101','102','103'),self.adult)
        b,p=plan_staff(a,'cafeteria','remove',('101','103'),self.adult)
        self.assertEqual(p['changed'],2)
        self.assertEqual(b.members('cafeteria'),('102',))
        c,_=plan_staff(b,'custodians','assign',['101'],self.adult)
        self.assertEqual(c.members('custodians'),('101',))

    def test_one_click_multi_persist_and_atomic_stale_rejection(self):
        old=self.store.load('11')
        a,_=plan_staff(old,'cafeteria','assign',('101','102'),self.adult)
        self.store.apply('11','cafeteria','assign',('101','102'),self.adult,
                         old.fingerprint())
        after=self.store.load('11')
        self.assertEqual(after.members('cafeteria'),('101','102'))
        with self.assertRaises(StaffError):
            self.store.apply('11','custodians','assign',('201',),self.adult,
                             old.fingerprint())
        self.assertEqual(self.store.load('11').members('custodians'),())
        with self.assertRaises(StaffError):
            self.store.apply('12','custodians','assign',('201',),self.adult,
                             after.fingerprint())

    def test_corrupt_json_is_never_overwritten(self):
        path=Path(self.store.path('11'))
        path.write_text('{"incomplete":true}')
        with self.assertRaises(StaffError):
            self.store.load('11')
        with self.assertRaises(StaffError):
            self.store.save('11',StaffRoster('11'))
        self.assertEqual(path.read_text(),'{"incomplete":true}')


class StaffPackageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.before=resources(m52_package())
        cls.after=resources(package_bytes())
        cls.lookup={(typ,group,iid):raw for typ,group,iid,raw in cls.after}

    def test_m52_resources_never_changed_except_injector_and_stbl(self):
        self.assertEqual(len(self.before),35)
        self.assertEqual(len(self.after),62)
        for old,new in zip(self.before,self.after):
            self.assertEqual(old[:3],new[:3])
            if old[0] not in (TYPE_SNIPPET,TYPE_STBL):
                self.assertEqual(old,new)

    def test_all_five_new_categories_use_correct_lot51_headers_and_parents(self):
        self.assertEqual(len(CAT_IDS),5)
        self.assertEqual(len(set(CAT_IDS)),5)
        for idx,(iid,name) in enumerate(zip(CAT_IDS,NAMES)):
            self.assertEqual(len(name),20)
            xml=ET.fromstring(self.lookup[(CATEGORY_TYPE,0,iid)])
            self.assertEqual(xml.get('n'),name)
            parent=MATCHED_ROOT if idx==0 else CAT_IDS[0]
            self.assertEqual(xml.find('./T[@n="_parent"]').text,str(parent))
            data=self.lookup[(SIMDATA_TYPE,SIMDATA_GROUP,iid)]
            self.assertEqual(len(data),475)
            self.assertEqual(data[0x24:0x28],struct.pack(
                '<I',_fnv1_lower32(name)))
            self.assertEqual(struct.unpack_from('<I',data,0x44)[0],
                             CAT_LABELS[idx])
            self.assertEqual(struct.unpack_from('<Q',data,0x5c)[0],
                             parent<<32)
            self.assertIn(name.encode(),data)
        self.assertEqual(_fnv1_lower32('Iliyana:MHS_Settings'),0x1e597b9e)

    def test_17_staff_actions_wired_to_correct_child_and_dynamic_mixins(self):
        self.assertEqual(len(ACTIONS),17)
        self.assertEqual(len(set(ACTION_IDS)),17)
        for i,(token,cat,it,en,klass) in enumerate(ACTIONS):
            row=self.lookup[(TYPE_INTERACTION,0,ACTION_IDS[i])]
            root=ET.fromstring(row)
            self.assertEqual(root.get('m'),'mhs39_visibility_ui')
            self.assertEqual(root.get('c'),'MHS39_MHS53'+token)
            self.assertEqual(root.find('./T[@n="category"]').text,
                             str(CAT_IDS[cat]))
            self.assertEqual(root.find('./T[@n="display_name"]').text,
                             '0x{:08X}'.format(ACTION_KEYS[i]))

    def test_one_injector_refs_every_staff_action(self):
        injector=next(ET.fromstring(row) for typ,g,iid,row in self.after
                      if typ==TYPE_SNIPPET)
        ids={int(x.text) for x in injector.findall(
            './L[@n="add_interactions_to_objects"]/U/L[@n="_super_affordances"]/T')}
        self.assertTrue(set(ACTION_IDS).issubset(ids))

    def test_all_labels_italian_english(self):
        table={}
        for typ,g,iid,raw in self.after:
            if typ==TYPE_STBL:
                table[iid>>56]=parse_stbl(raw)
        self.assertEqual(set(table),{0,11})
        self.assertEqual(table[11][CAT_LABELS[0]],'Personale scolastico')
        self.assertEqual(table[0][CAT_LABELS[0]],'School staff')
        self.assertIn('max 2',table[11][ACTION_KEYS[13]])
        for label in CAT_LABELS+ACTION_KEYS:
            self.assertIn(label,table[0])
            self.assertIn(label,table[11])

    def test_script_archive_has_backend_and_UI_with_M52_dependencies(self):
        self.assertEqual(len(SCRIPTS),19)
        self.assertEqual(len({p.name for p in SCRIPTS}),19)
        self.assertIn('mhs53_staff_store.py',{p.name for p in SCRIPTS})
        self.assertIn('mhs53_staff_ui.py',{p.name for p in SCRIPTS})
        self.assertIn('mhs27_remove_ui.py',{p.name for p in SCRIPTS})
        report=inspect_bytes(package_bytes())
        self.assertEqual(report['status'],'STATIC_GATE_PASSED')
        self.assertEqual(report['category_count'],10)
        self.assertEqual(report['simdata_count'],10)


if __name__=='__main__':
    unittest.main()
