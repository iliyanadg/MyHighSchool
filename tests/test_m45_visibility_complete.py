"""M45 guards all 22 visible menu actions, preserving the exact M44 categories."""
import struct
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from types import SimpleNamespace

from tooling.build_m45_visibility_complete import (
    package_bytes,LOT51_HEADERS,ENROLL_IDS,CATEGORY_IDS,PACK_NAME,
    MATCHED_ROOT,SETTINGS_CATEGORY,CATEGORY_TYPE,SIMDATA_TYPE,
    TYPE_INTERACTION)
from tooling.build_m43_matched_root import package_bytes as build_m43
from tooling.simdata_release_gate import resources,inspect_bytes
from src.m39_visibility.mhs39_visibility_rules import allowed


class FakeResult(object):
    def __init__(self,success,reason=''):
        self.result=success


class FakeStore(object):
    def __init__(self,active,count):
        self.value=SimpleNamespace(active=active,class_count=count)

    def load(self,slot):
        return self.value


class M45VisibilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old=resources(build_m43())
        cls.new=resources(package_bytes())

    def test_3_gated_pickers_preserve_ids_categories(self):
        pickers={inst:num for num,inst in enumerate(ENROLL_IDS,1)}
        encountered=set()
        for typ,group,iid,raw in self.new:
            if typ!=TYPE_INTERACTION or iid not in pickers:
                continue
            node=ET.fromstring(raw)
            self.assertEqual(node.get('m'),'mhs39_visibility_ui')
            self.assertEqual(node.get('c'),'MHS45ChooseClass'+str(pickers[iid]))
            self.assertEqual(int(node.find('./T[@n="category"]').text),
                             CATEGORY_IDS[pickers[iid]-1])
            encountered.add(iid)
        self.assertEqual(encountered,set(pickers))

    def test_all_22_user_clickable_actions_are_guarded(self):
        check_ids=set(CATEGORY_IDS)|{MATCHED_ROOT,SETTINGS_CATEGORY}
        users=[]
        for typ,group,iid,raw in self.new:
            if typ!=TYPE_INTERACTION:
                continue
            node=ET.fromstring(raw)
            category=node.find('./T[@n="category"]')
            if category is not None and int(category.text) in check_ids:
                users.append(node.get('n'))
                self.assertEqual(node.get('m'),'mhs39_visibility_ui')
        self.assertEqual(len(users),19)

    def test_per_class_picker_subclasses_execute_actual_mixin(self):
        source=(Path(__file__).resolve().parents[1]/
                'src/m39_visibility/mhs39_visibility_ui.py').read_text()
        start=source.index('class _MHS39VisibilityMixin(object):')
        end=source.index('\n\nfor _module',start)
        wrappers_start=source.index('for _class_number in (1, 2, 3):')
        wrappers_end=source.index('\n\n# M53:',wrappers_start)
        wrappers=source[wrappers_start:wrappers_end]
        # The experimental M47 extension has been retired; M45 remains intact.
        self.assertNotIn('TestResult.FALSE',source[start:end])

        class Picker(object):
            @classmethod
            def _test(cls,*args,**kwargs):
                return FakeResult(True)

        fake=FakeStore(True,2)
        ns={
            'TestResult':FakeResult,
            'SimPickerInteraction':Picker,
            '_CONFIG':fake,
            'current_slot':lambda **kwargs:11,
            'available_from_settings':lambda settings,action,n:
                allowed(settings.active,settings.class_count,action,n),
        }
        exec(source[start:end],ns)
        exec(wrappers,ns)
        self.assertTrue(ns['MHS45ChooseClass1']._test().result)
        self.assertTrue(ns['MHS45ChooseClass2']._test().result)
        self.assertFalse(ns['MHS45ChooseClass3']._test().result)
        fake.value.active=False
        for n in (1,2,3):
            self.assertFalse(ns['MHS45ChooseClass'+str(n)]._test().result)
        fake.value=SimpleNamespace(active=True,class_count=3)
        for n in (1,2,3):
            self.assertTrue(ns['MHS45ChooseClass'+str(n)]._test().result)

    def test_preserve_categories_strings_and_other_interactions(self):
        self.assertEqual(len(self.new),len(self.old))
        for a,b in zip(self.old,self.new):
            self.assertEqual(a[:3],b[:3])
            typ,group,iid,_=a
            if typ==SIMDATA_TYPE and iid in LOT51_HEADERS:
                self.assertEqual(b[3][0x24:0x28],LOT51_HEADERS[iid])
                self.assertEqual(struct.unpack_from('<Q',b[3],0x5c)[0],
                                 MATCHED_ROOT<<32)
                self.assertEqual(b[3][:0x24],a[3][:0x24])
                self.assertEqual(b[3][0x28:0x5c],a[3][0x28:0x5c])
                self.assertEqual(b[3][0x64:],a[3][0x64:])
            elif typ==TYPE_INTERACTION and iid in ENROLL_IDS:
                a_node,b_node=ET.fromstring(a[3]),ET.fromstring(b[3])
                a_node.attrib['m']=b_node.attrib['m']
                a_node.attrib['c']=b_node.attrib['c']
                self.assertEqual(ET.tostring(a_node),ET.tostring(b_node))
            else:
                self.assertEqual(a,b)

    def test_package_has_five_valid_category_pairs(self):
        gate=inspect_bytes(package_bytes())
        self.assertEqual(gate['status'],'STATIC_GATE_PASSED')
        self.assertEqual(gate['category_count'],5)
        self.assertEqual(gate['simdata_count'],5)
        self.assertEqual(gate['resource_count'],35)


if __name__=='__main__':
    unittest.main()
