"""Offline M29 regression tests: undo safety, attendance eligibility audit and UI package."""
import ast
import json
import sys
import tempfile
import unittest
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'/'m2_registry'))
from mhs_m2_roster import SchoolRoster, RosterError
from mhs_m2_store import RosterStore, StoreError
from tooling.build_m29_bundle import package_bytes, IDS, STBL_KEYS
from tooling.build_m28_bundle import package_bytes as build_m28
from tooling.simdata_release_gate import resources
from tooling.m1_links_and_strings import parse_stbl


class UndoTests(unittest.TestCase):
    def setUp(self):
        self.directory=tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.store=RosterStore(self.directory.name)

    def test_first_enrollment_can_be_undone(self):
        self.store.save('22',SchoolRoster('22',{'101':1}))
        self.assertEqual(self.store.load('22').class_members(1),['101'])
        result=self.store.undo_last('22')
        self.assertEqual(result.class_members(1),[])
        self.assertEqual(self.store.load('22').class_members(1),[])
        with self.assertRaises(StoreError):
            self.store.undo_last('22')

    def test_second_edit_undoes_only_second(self):
        self.store.save('22',SchoolRoster('22',{'101':1}))
        self.store.save('22',SchoolRoster('22',{'101':2,'201':3}))
        self.store.undo_last('22')
        self.assertEqual(self.store.load('22').assignments,{'101':1})

    def test_journal_slot_isolation(self):
        self.store.save('22',SchoolRoster('22',{'101':1}))
        with self.assertRaises(StoreError):
            self.store.undo_last('23')
        self.assertEqual(self.store.load('22').assignments,{'101':1})

    def test_stale_undo_must_not_overwrite_external_changes(self):
        self.store.save('22',SchoolRoster('22',{'101':1}))
        name=Path(self.store.path('22'))
        name.write_text(SchoolRoster('22',{'201':2}).to_json(),encoding='utf-8')
        with self.assertRaises(StoreError):
            self.store.undo_last('22')
        self.assertEqual(self.store.load('22').assignments,{'201':2})

    def test_invalid_journal_fails_closed(self):
        self.store.save('22',SchoolRoster('22',{'101':1}))
        Path(self.store.journal_path('22')).write_text(
            json.dumps({'schema':1,'slot':'23','before':'{}','after_sha256':'bad'}),
            encoding='utf-8')
        with self.assertRaises(StoreError):
            self.store.undo_last('22')
        self.assertEqual(self.store.load('22').class_members(1),['101'])

    def test_no_rewrite_on_identical_save(self):
        r=SchoolRoster('22',{'101':1})
        self.store.save('22',r)
        before=Path(self.store.journal_path('22')).read_bytes()
        self.store.save('22',r)
        self.assertEqual(before,Path(self.store.journal_path('22')).read_bytes())


class AuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        source=(ROOT/'src'/'m29_registry'/'mhs29_controls.py').read_text(encoding='utf-8')
        tree=ast.parse(source)
        func=next(x for x in tree.body if isinstance(x,ast.FunctionDef) and
                  x.name=='inspect_roster')
        module=ast.Module(body=[func],type_ignores=[])
        context={'SchoolRoster':SchoolRoster,'RosterError':RosterError}
        exec(compile(module,'mhs29_audit','exec'),context)
        cls.inspect=staticmethod(context['inspect_roster'])

    def test_audit_distinguishes_aged_and_missing(self):
        r=SchoolRoster('4',{'1':1,'2':2,'3':3})
        infos={'1':object(),'2':object()}
        result=self.inspect(r,lambda sid:infos.get(sid),lambda sid:sid=='1')
        self.assertEqual(result['enrolled'],3)
        self.assertEqual(result['invalid'],(
            ('2',2,'Non piu adolescente'),('3',3,'Sim non trovato')))

    def test_checker_failure_fails_closed(self):
        r=SchoolRoster('4',{'1':1})
        def broken(sid):
            raise RuntimeError('unknown')
        with self.assertRaises(RosterError):
            self.inspect(r,lambda sid:object(),broken)


class PackageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows=resources(package_bytes())
        cls.baseline=resources(build_m28())

    def test_three_new_view_interactions_and_original_preserved(self):
        self.assertEqual(len(self.rows),17)
        for old,new in zip(self.baseline,self.rows):
            self.assertEqual(old[:3],new[:3])
            if old[0]==0xE882D22F:
                self.assertEqual(old,new)
        roots={i:ET.fromstring(blob) for t,g,i,blob in self.rows if t==0xE882D22F}
        for idx,iid in enumerate(IDS):
            self.assertEqual(roots[iid].get('c'),'MHS29ViewClass{}'.format(idx+1))
            self.assertEqual(roots[iid].get('m'),'mhs29_controls')

    def test_mailbox_and_localization(self):
        root=next(ET.fromstring(raw) for typ,g,i,raw in self.rows if typ==0x7DF2169C)
        registered={int(x.text) for x in root.findall('.//L[@n="_super_affordances"]/T')}
        self.assertTrue(set(IDS).issubset(registered))
        for typ,g,i,payload in self.rows:
            if typ==0x220557DA:
                strings=parse_stbl(payload)
                self.assertEqual(len(strings),18)
                self.assertTrue(all(k in strings for k in STBL_KEYS))
                self.assertIn('M29',strings[0x3FCE8D06])


if __name__=='__main__':
    unittest.main()
