"""M34 test-save configuration, activation and safe class count checks."""
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
REG=ROOT/'src'/'m2_registry'
if str(REG) not in sys.path:
    sys.path.insert(0,str(REG))

from mhs_m2_roster import SchoolRoster
from mhs34_settings import SettingsStore, SettingsError, SchoolSettings
from tooling.build_m34_settings import (package_bytes,IDS,KEYS,BASE_CATEGORY)
from tooling.build_m33_flat_recovery import package_bytes as build_m33
from tooling.simdata_release_gate import resources,inspect_bytes
from tooling.m1_links_and_strings import parse_stbl


class ConfigTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store=SettingsStore(self.temp.name)

    def test_default_inactive_two_classes(self):
        original=self.store.load('11')
        self.assertEqual(original.slot,'11')
        self.assertFalse(original.active)
        self.assertEqual(original.class_count,2)
        self.assertEqual(list(Path(self.temp.name).iterdir()),[])

    def test_enable_disable_persists_per_slot(self):
        self.store.set_active('11',True)
        self.assertTrue(self.store.load('11').active)
        self.assertFalse(self.store.load('12').active)
        self.store.set_active('11',False)
        self.assertFalse(self.store.load('11').active)

    def test_add_third_class_and_return_to_two(self):
        roster=SchoolRoster('11',{'1':1,'2':2})
        self.store.set_class_count('11',3,roster)
        self.assertEqual(self.store.load('11').class_count,3)
        self.store.set_class_count('11',2,roster)
        self.assertEqual(self.store.load('11').class_count,2)

    def test_cannot_disable_occupied_third_class(self):
        roster=SchoolRoster('11',{'1':1,'3':3})
        self.store.set_class_count('11',3,roster)
        original=self.store.path('11')
        before=Path(original).read_bytes()
        with self.assertRaises(SettingsError):
            self.store.set_class_count('11',2,roster)
        self.assertEqual(Path(original).read_bytes(),before)
        self.assertEqual(self.store.load('11').class_count,3)
        self.assertEqual(roster.class_members(3),['3'])

    def test_two_slots_remain_independent(self):
        self.store.set_active('11',True)
        self.store.set_class_count('11',3,SchoolRoster('11'))
        self.assertEqual(self.store.load('11').class_count,3)
        self.assertEqual(self.store.load('12').class_count,2)
        self.assertFalse(self.store.load('12').active)

    def test_invalid_file_fails_closed_without_overwriting(self):
        filename=Path(self.store.path('11'))
        filename.write_text('{"bad": true}',encoding='utf-8')
        before=filename.read_bytes()
        with self.assertRaises(SettingsError):
            self.store.set_active('11',True)
        self.assertEqual(filename.read_bytes(),before)

    def test_disabled_and_third_class_preflight(self):
        with self.assertRaises(SettingsError):
            self.store.require_management('11',1)
        self.store.set_active('11',True)
        self.store.require_management('11',1)
        with self.assertRaises(SettingsError):
            self.store.require_management('11',3)
        self.store.set_class_count('11',3,SchoolRoster('11'))
        self.store.require_management('11',3)

    def test_runtime_write_gate_blocks_disabled_and_inactive_class(self):
        spec=importlib.util.spec_from_file_location(
            'test_mhs34_gate',(ROOT/'src'/'m34_settings'/'mhs34_runtime_gate.py'))
        module=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        initial=SchoolRoster('11')
        third=SchoolRoster('11',{'3':3})
        with self.assertRaises(SettingsError):
            module.validate_roster_write(self.temp.name,'11',initial,third)
        self.store.set_active('11',True)
        with self.assertRaises(SettingsError):
            module.validate_roster_write(self.temp.name,'11',initial,third)
        self.store.set_class_count('11',3,initial)
        self.assertTrue(module.validate_roster_write(self.temp.name,'11',initial,third))


class M34PackageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=resources(package_bytes())
        cls.before=resources(build_m33())

    def test_preserved_flat_single_category(self):
        info=inspect_bytes(package_bytes())
        self.assertEqual(info['status'],'STATIC_GATE_PASSED')
        self.assertEqual(info['category_count'],1)
        self.assertEqual(info['simdata_count'],1)
        self.assertEqual(len(self.data),27)

    def test_settings_actions_registered_on_main_menu(self):
        actions={iid:ET.fromstring(blob) for typ,g,iid,blob in self.data
                 if typ==0xE882D22F}
        names=('MHS34Enable','MHS34Disable','MHS34TwoClasses','MHS34ThreeClasses')
        for idx,iid in enumerate(IDS):
            self.assertEqual(actions[iid].get('c'),names[idx])
            self.assertEqual(actions[iid].get('m'),'mhs34_settings_ui')
            self.assertEqual(actions[iid].find('./T[@n="category"]').text,
                             str(BASE_CATEGORY))

    def test_original_interactions_unchanged(self):
        for older,new in zip(self.before,self.data):
            self.assertEqual(older[:3],new[:3])
            if older[0] in (0xE882D22F,0x03E9D964,0x545AC67A):
                self.assertEqual(older,new)

    def test_four_localized_actions(self):
        for t,g,i,blob in self.data:
            if t==0x220557DA:
                strings=parse_stbl(blob)
                self.assertIn('M34',strings[0x3FCE8D06])
                for key in KEYS:
                    self.assertIn(key,strings)


if __name__=='__main__':
    unittest.main()
