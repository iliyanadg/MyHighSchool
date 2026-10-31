"""Regression tests for player's actual M41 Better Exceptions crash and menus."""
import ast
import struct
import unittest
from pathlib import Path
import xml.etree.ElementTree as ET

from tooling.build_m42_safe_menu import (
    package_bytes,NEW_ROOT,CATEGORY_TYPE,SIMDATA_TYPE,TYPE_STBL)
from tooling.build_m41_complete_menu import package_bytes as build_m41
from tooling.build_m34_settings import KEYS
from tooling.m1_links_and_strings import parse_stbl
from tooling.simdata_release_gate import resources,inspect_bytes
from src.m39_visibility.mhs39_visibility_rules import allowed


class FakeResult(object):
    # Intentionally has NO attribute FALSE, replicating live TS4 API.
    def __init__(self,ok,reason=''):
        self.result=ok
        self.reason=reason


class FakeConfig(object):
    def __init__(self,settings=None,fails=False):
        self.settings=settings
        self.fails=fails
    def load(self,slot):
        if self.fails:
            raise OSError('mock unable to load slot')
        return self.settings


class TestM42(unittest.TestCase):

    def test_no_m41_attribute_error_with_hidden_actions(self):
        path=Path(__file__).resolve().parents[1]/'src'/'m39_visibility'/'mhs39_visibility_ui.py'
        source=path.read_text(encoding='utf-8')
        # Check executable mixin body; documentation may mention the bad M41 constant.
        check_start=source.index('class _MHS39VisibilityMixin(object):')
        check_end=source.index('\\n\\nfor _module',check_start)
        self.assertNotIn('TestResult.FALSE',source[check_start:check_end])
        # Import just the real mixin class with stubs in place of Sims 4
        # unavailable modules, to execute the exact code in a unit test.
        start=source.index('class _MHS39VisibilityMixin(object):')
        end=source.index('\n\nfor _module',start)
        class_source=source[start:end]
        from types import SimpleNamespace
        config=FakeConfig(SimpleNamespace(active=True,class_count=2))
        namespace={
            'TestResult':FakeResult,
            '_CONFIG':config,
            'current_slot':lambda:11,
            'available_from_settings':lambda state,action,num: allowed(
                state.active,state.class_count,action,num),
        }
        exec(class_source,namespace)
        mixin=namespace['_MHS39VisibilityMixin']

        class Base(object):
            @classmethod
            def _test(cls,*args,**kwargs):
                return FakeResult(True)

        def make(action,klass):
            return type('MockMHS',(mixin,Base),{
                '_mhs39_action':action,
                '_mhs39_class':klass,
            })

        self.assertFalse(make('class',3)._test().result)
        self.assertFalse(make('transfer',(1,3))._test().result)
        self.assertFalse(make('enable',0)._test().result)
        self.assertTrue(make('class',1)._test().result)
        self.assertTrue(make('transfer',(1,2))._test().result)
        self.assertTrue(make('disable',0)._test().result)
        config.fails=True
        self.assertFalse(make('class',1)._test().result)

    def test_optional_third_class_and_transfer_gating(self):
        self.assertFalse(allowed(True,2,'class',3))
        self.assertFalse(allowed(True,2,'transfer',(1,3)))
        self.assertFalse(allowed(True,2,'transfer',(3,2)))
        self.assertTrue(allowed(True,2,'transfer',(1,2)))
        self.assertTrue(allowed(True,3,'transfer',(1,3)))
        self.assertTrue(allowed(True,3,'transfer',(3,2)))
        self.assertFalse(allowed(False,3,'class',1))
        self.assertTrue(allowed(False,3,'enable',0))
        self.assertTrue(allowed(True,2,'activate_third',0))
        self.assertFalse(allowed(True,2,'deactivate_third',0))

    def test_parent_graph_preserved_and_root_priority(self):
        old=resources(build_m41())
        new=resources(package_bytes())
        self.assertEqual(len(old),len(new))
        for a,b in zip(old,new):
            self.assertEqual(a[:3],b[:3])
            if a[0] not in (TYPE_STBL,CATEGORY_TYPE,SIMDATA_TYPE):
                self.assertEqual(a,b)
            if a[2]!=NEW_ROOT and a[0] in (CATEGORY_TYPE,SIMDATA_TYPE):
                self.assertEqual(a,b)
            if b[2]==NEW_ROOT and b[0]==CATEGORY_TYPE:
                node=ET.fromstring(b[3])
                self.assertEqual(node.find('./T[@n="_display_priority"]').text,'9')
                self.assertIsNone(node.find('./T[@n="_parent"]'))
            if b[2]==NEW_ROOT and b[0]==SIMDATA_TYPE:
                self.assertEqual(struct.unpack_from('<i',b[3],0x48)[0],9)

    def test_clean_settings_labels_and_zip_structure(self):
        rows=resources(package_bytes())
        self.assertEqual(inspect_bytes(package_bytes())['status'],'STATIC_GATE_PASSED')
        for typ,group,iid,blob in rows:
            if typ!=TYPE_STBL:
                continue
            values=parse_stbl(blob)
            self.assertEqual(values[KEYS[0]],'Attiva MY HIGH SCHOOL' if iid>>56==11 else 'Enable MY HIGH SCHOOL')
            self.assertEqual(values[KEYS[1]],'Disattiva MY HIGH SCHOOL' if iid>>56==11 else 'Disable MY HIGH SCHOOL')
            self.assertEqual(values[KEYS[2]],'Disabilita Classe 3' if iid>>56==11 else 'Disable Class 3')
            self.assertEqual(values[KEYS[3]],'Abilita Classe 3' if iid>>56==11 else 'Enable Class 3')


if __name__=='__main__':
    unittest.main()
