"""M98 native Core school roles UI package structural and source tests."""
import sys
import struct
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from tooling.build_mhs98_roles import (package_bytes,script_sources,
    transformed_resources,CAT_ID,CAT_STBL_KEY,MENU_NAME,ACTION_IDS,ACTION_KEYS,
    ACTIONS)
from tooling.build_m55_attendance_trial import package_bytes as m85_package
from tooling.build_m27_removal import TYPE_STBL,TYPE_SNIPPET,TYPE_INTERACTION
from tooling.build_m41_complete_menu import CATEGORY_TYPE,SIMDATA_TYPE
from tooling.build_m43_matched_root import MATCHED_ROOT
from tooling.m1_links_and_strings import parse_stbl
from tooling.simdata_release_gate import resources,inspect_bytes

class TestM98Package(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows=transformed_resources()
    def test_one_new_role_category_and_all_eleven_actions(self):
        self.assertEqual(len(ACTIONS),11)
        self.assertEqual(len(set(ACTION_IDS)),11)
        self.assertEqual(len(self.rows),76)
        cat=next(b for t,g,i,b in self.rows if t==CATEGORY_TYPE and i==CAT_ID)
        root=ET.fromstring(cat)
        self.assertEqual(root.get('n'),MENU_NAME)
        self.assertEqual(root.find('./T[@n="_parent"]').text,str(MATCHED_ROOT))
        self.assertEqual(root.find('./T[@n="_display_name"]').text,
                         '0x{:08X}'.format(CAT_STBL_KEY))
        data=next(b for t,g,i,b in self.rows if t==SIMDATA_TYPE and i==CAT_ID)
        self.assertEqual(len(data),475)
        self.assertEqual(data.count(MENU_NAME.encode('ascii')),1)
        self.assertEqual(struct.unpack_from('<Q',data,0x5c)[0],
                         MATCHED_ROOT<<32)
        for i,(role,mode) in enumerate(ACTIONS):
            action=next(b for t,g,iid,b in self.rows
                        if t==TYPE_INTERACTION and iid==ACTION_IDS[i])
            item=ET.fromstring(action)
            self.assertEqual(item.get('c'),
                'MHS98Role'+mode.capitalize()+role.capitalize())
            self.assertEqual(item.get('m'),'mhs98_core_role_ui')
            self.assertEqual(item.find('./T[@n="category"]').text,str(CAT_ID))

    def test_current_original_m85_resources_untouched_outside_menu_labels(self):
        original=resources(m85_package())
        self.assertEqual(len(original),63)
        for a,b in zip(original,self.rows[:63]):
            self.assertEqual(a[:3],b[:3])
            if a[0] not in (TYPE_STBL,TYPE_SNIPPET):
                self.assertEqual(a,b)

    def test_italian_english_actions_and_injector(self):
        stbls=[(i,b) for t,g,i,b in self.rows if t==TYPE_STBL]
        self.assertEqual(len(stbls),2)
        for i,b in stbls:
            names=parse_stbl(b)
            self.assertIn(CAT_STBL_KEY,names)
            for key in ACTION_KEYS:
                self.assertIn(key,names)
            if i>>56==11:
                self.assertEqual(names[CAT_STBL_KEY],'Ruoli speciali')
            else:
                self.assertEqual(names[CAT_STBL_KEY],'Special school roles')
        snippet=next(b for t,g,i,b in self.rows if t==TYPE_SNIPPET)
        root=ET.fromstring(snippet)
        seen={int(e.text) for e in root.findall(
            './L[@n="add_interactions_to_objects"]/U/'
            'L[@n="_super_affordances"]/T')}
        self.assertTrue(set(ACTION_IDS)<=seen)

    def test_dbpf_gates_and_script_names(self):
        report=inspect_bytes(package_bytes())
        self.assertEqual(report['status'],'STATIC_GATE_PASSED')
        self.assertEqual(report['resource_count'],76)
        self.assertEqual(report['category_count'],11)
        self.assertEqual(report['simdata_count'],11)
        names={p.name for p in script_sources()}
        self.assertEqual(len(names),35)
        self.assertIn('mhs98_core_role_ui.py',names)
        self.assertIn('mhs97_core_role_store.py',names)
        self.assertIn('mhs94_school_job_probe.py',names)
        # No experimental EA student filter or schedule hooks are compiled.
        self.assertNotIn('mhs96_exact_school_count.py',names)
        self.assertNotIn('mhs97_core_filter_policy.py',names)

if __name__=='__main__':
    unittest.main()
