"""Offline checks for six class-scoped transfer actions and safe engine."""
import ast
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'/'m2_registry'))
from mhs_m2_roster import SchoolRoster, RosterError
from mhs_m2_store import RosterStore
from tooling.build_m32_transfer import (
    package_bytes, IDS, ROUTES, KEYS, TYPE_INTERACTION, TYPE_STBL)
from tooling.build_m30_nested_menu import CATEGORY_IDS, package_bytes as old_build
from tooling.m1_links_and_strings import parse_stbl
from tooling.simdata_release_gate import resources, inspect_bytes


class TransferPlanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        content=(ROOT/'src'/'m32_transfer'/'mhs32_transfer_ui.py').read_text(encoding='utf-8')
        tree=ast.parse(content)
        function=next(node for node in tree.body if isinstance(node,ast.FunctionDef)
                      and node.name=='plan_transfer')
        module=ast.Module(body=[function],type_ignores=[])
        scope={'SchoolRoster':SchoolRoster,'RosterError':RosterError}
        exec(compile(module,'transfer_test','exec'),scope)
        cls.plan=staticmethod(scope['plan_transfer'])

    def test_move_multiple_to_class_three_without_modifying_original(self):
        original=SchoolRoster('11',{'101':1,'102':1,'201':2})
        updated,result=self.plan(original,1,3,['101','102'],lambda s:True)
        self.assertEqual(result['moved'],2)
        self.assertEqual(updated.class_members(3),['101','102'])
        self.assertEqual(updated.class_members(1),[])
        self.assertEqual(original.class_members(1),['101','102'])

    def test_full_destination_rejected_even_for_one_student(self):
        original=SchoolRoster('11',{'1':1})
        full,_=original.assign_many(2,list(range(20,28)),lambda s:True)
        before=full.to_json()
        with self.assertRaises(RosterError):
            self.plan(full,1,2,['1'],lambda s:True)
        self.assertEqual(full.to_json(),before)

    def test_reject_wrong_class_and_non_enrolled(self):
        original=SchoolRoster('11',{'1':1,'2':2,'3':3})
        for ids in (['2'],['1','2'],['999'],[],['1','1']):
            with self.assertRaises(RosterError):
                self.plan(original,1,3,ids,lambda s:True)

    def test_reject_invalid_destination_or_adult(self):
        original=SchoolRoster('11',{'1':1,'2':2})
        with self.assertRaises(RosterError):
            self.plan(original,1,1,['1'],lambda s:True)
        with self.assertRaises(RosterError):
            self.plan(original,1,4,['1'],lambda s:True)
        with self.assertRaises(RosterError):
            self.plan(original,1,3,['1'],lambda s:False)

    def test_service_persists_only_after_explicit_save(self):
        with tempfile.TemporaryDirectory() as tmp:
            store=RosterStore(tmp)
            store.save('11',SchoolRoster('11',{'1':1,'2':2}))
            before=Path(store.path('11')).read_bytes()
            updated,_=self.plan(store.load('11'),1,3,['1'],lambda s:True)
            self.assertEqual(Path(store.path('11')).read_bytes(),before)
            store.save('11',updated)
            self.assertEqual(store.load('11').class_members(3),['1'])
            store.undo_last('11')
            self.assertEqual(store.load('11').class_members(1),['1'])


class PackageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows=resources(package_bytes())
        cls.old=resources(old_build())

    def test_all_categories_still_linked_and_structural_gate(self):
        check=inspect_bytes(package_bytes())
        self.assertEqual(check['status'],'STATIC_GATE_PASSED')
        self.assertEqual(check['category_count'],4)
        self.assertEqual(check['simdata_count'],4)
        self.assertEqual(len(self.rows),29)

    def test_each_new_transfer_belongs_to_own_source_class(self):
        mapping={iid:ET.fromstring(blob) for typ,group,iid,blob in self.rows
                 if typ==TYPE_INTERACTION}
        for number,(source,dest) in enumerate(ROUTES):
            root=mapping[IDS[number]]
            self.assertEqual(root.get('m'),'mhs32_transfer_ui')
            self.assertEqual(root.get('c'),'MHS32Transfer{}To{}'.format(source,dest))
            self.assertEqual(root.find('./T[@n="category"]').text,
                             str(CATEGORY_IDS[source-1]))
            self.assertEqual(root.find('./T[@n="display_name"]').text,
                             '0x{:08X}'.format(KEYS[number]))

    def test_injector_registers_all_six(self):
        root=next(ET.fromstring(blob) for typ,group,iid,blob in self.rows
                  if typ==0x7DF2169C)
        ids={int(node.text) for node in root.findall('.//L[@n="_super_affordances"]/T')}
        self.assertTrue(set(IDS).issubset(ids))
        self.assertEqual(len(set(IDS)),6)

    def test_existing_interactions_are_unchanged(self):
        for old,new in zip(self.old,self.rows):
            self.assertEqual(old[:3],new[:3])
            if old[0] in (TYPE_INTERACTION,0x03E9D964,0x545AC67A):
                self.assertEqual(old,new)

    def test_localizations_in_both_languages(self):
        for typ,group,iid,blob in self.rows:
            if typ==TYPE_STBL:
                values=parse_stbl(blob)
                self.assertEqual(len(values),27)
                self.assertIn('M32',values[0x3FCE8D06])
                self.assertTrue(all(key in values for key in KEYS))

    def test_transfer_classes_available_for_tuning_loader(self):
        content=(ROOT/'src'/'m32_transfer'/'mhs32_transfer_ui.py').read_text(encoding='utf-8')
        tree=ast.parse(content)
        declared={node.name for node in tree.body if isinstance(node,ast.ClassDef)}
        for s,d in ROUTES:
            self.assertIn('MHS32Transfer{}To{}'.format(s,d),declared)


if __name__=='__main__':
    unittest.main()
