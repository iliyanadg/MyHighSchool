"""M55 offline safety tests: strict human teen selection, duplicate and EA call gates."""
import ast
import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'/'m55_attendance'))

from mhs55_attendance_core import (
    AttendanceError, valid_student, select_one, situation_guid,
    school_running, already_in_base_student, create_single_student_situation,
    BASE_STUDENT_JOB, BASE_STUDENT_SITUATION)
from tooling.build_m55_attendance_trial import (
    transformed_resources, package_bytes, ACTION_ID, SCRIPTS, LABEL_ID)
from tooling.build_m53_staff_management import package_bytes as m54_package
from tooling.build_m27_removal import TYPE_INTERACTION, TYPE_SNIPPET, TYPE_STBL
from tooling.m1_links_and_strings import parse_stbl
from tooling.simdata_release_gate import resources, inspect_bytes


class M55Test(unittest.TestCase):
    def test_only_teen_human(self):
        teen, adult, human, dog = 1, 2, 10, 20
        self.assertTrue(valid_student(SimpleNamespace(age=teen,species=human),teen,human))
        for info in (None, SimpleNamespace(age=adult,species=human),
                     SimpleNamespace(age=teen,species=dog),
                     SimpleNamespace(age=teen)):
            self.assertFalse(valid_student(info,teen,human))

    def test_picker_is_exactly_one_rostered_person(self):
        self.assertEqual(select_one(['10','11'],['10','11'],['10']),'10')
        for chosen in ([],['10','11'],['12'],['0'],['010'],[True]):
            with self.assertRaises(AttendanceError):
                select_one(['10','11'],['10','11'],chosen)

    def test_active_school_situation_and_no_duplicate(self):
        current = SimpleNamespace(guid64=BASE_STUDENT_SITUATION)
        instance = object()
        info = SimpleNamespace(age=1, get_sim_instance=lambda:instance)
        manager = SimpleNamespace(get_situations_sim_is_in=lambda sim:[current])
        self.assertTrue(school_running(manager,[info],1))
        self.assertTrue(already_in_base_student(manager,info))
        self.assertFalse(school_running(manager,[info],2))
        empty = SimpleNamespace(get_situations_sim_is_in=lambda sim:[])
        self.assertFalse(school_running(empty,[info],1))
        self.assertFalse(already_in_base_student(empty,info))

    def test_missing_membership_api_fails_closed(self):
        info = SimpleNamespace(get_sim_instance=lambda:object())
        with self.assertRaises(AttendanceError):
            already_in_base_student(SimpleNamespace(),info)

    def test_ea_one_call_only_and_exact_id(self):
        calls = []
        guest = SimpleNamespace(added=[])
        guest.add_guest_info = guest.added.append
        fake_gl = lambda **kwargs:guest
        fake_gi = SimpleNamespace(construct_from_purpose=lambda sid,job,purpose:
                                  (sid,job.guid64,purpose))
        situation = SimpleNamespace(guid64=BASE_STUDENT_SITUATION)
        job = SimpleNamespace(guid64=BASE_STUDENT_JOB)
        manager = SimpleNamespace(create_situation=lambda *args,**kwargs:
                                  calls.append((args,kwargs)) or 33)
        result = create_single_student_situation(
            manager,SimpleNamespace(sim_id=101),situation,job,fake_gl,fake_gi,2)
        self.assertEqual(result,33)
        self.assertEqual(len(calls),1)
        self.assertEqual(guest.added,[(101,BASE_STUDENT_JOB,2)])
        self.assertFalse(calls[0][1]['user_facing'])

    def test_wrong_ea_tuning_never_calls_create(self):
        called = []
        manager = SimpleNamespace(create_situation=lambda *args,**kwargs:called.append(1))
        with self.assertRaises(AttendanceError):
            create_single_student_situation(
                manager,SimpleNamespace(sim_id=101),
                SimpleNamespace(guid64=1),
                SimpleNamespace(guid64=BASE_STUDENT_JOB),
                lambda **k:None,None,None)
        self.assertEqual(called,[])

    def test_existing_m54_resources_preserved_except_injector_and_stbl(self):
        old=resources(m54_package())
        new=transformed_resources()
        self.assertEqual(len(old),62)
        self.assertEqual(len(new),63)
        altered=0
        for o,n in zip(old,new[:62]):
            self.assertEqual(o[:3],n[:3])
            if o!=n:
                altered+=1
                self.assertIn(o[0],(TYPE_SNIPPET,TYPE_STBL))
        self.assertEqual(altered,3)
        added=new[-1]
        self.assertEqual(added[:3],(TYPE_INTERACTION,0,ACTION_ID))
        root=ET.fromstring(added[3])
        self.assertEqual(root.get('m'),'mhs55_attendance_ui')
        self.assertEqual(root.get('c'),'MHS55TryOne')
        self.assertEqual(root.find('./T[@n="display_name"]').text,
                         '0x{:08X}'.format(LABEL_ID))

    def test_package_structure_and_script_modules(self):
        result=inspect_bytes(package_bytes())
        self.assertEqual(result['status'],'STATIC_GATE_PASSED')
        self.assertEqual(result['resource_count'],63)
        self.assertEqual(result['category_count'],10)
        self.assertEqual(result['simdata_count'],10)
        self.assertEqual(len(SCRIPTS),21)
        self.assertEqual(len({p.name for p in SCRIPTS}),21)
        self.assertEqual(set([p.name for p in SCRIPTS][-2:]),
                         {'mhs55_attendance_ui.py','mhs55_attendance_core.py'})

    def test_native_confirm_only_not_automatic_school_invite(self):
        source=(ROOT/'src'/'m55_attendance'/'mhs55_attendance_ui.py').read_text()
        self.assertIn("if not getattr(answer, 'accepted', False):",source)
        self.assertIn('current_slot() != slot',source)
        self.assertIn('_SETTINGS.require_management(slot, 1)',source)
        self.assertIn('_ATTEMPTED.add(key)',source)
        self.assertIn('if already_in_base_student(situations, info):',source)
        self.assertIn('school_running(situations, manager.get_all(), Age.TEEN)',source)
        self.assertIn('create_single_student_situation(',source)
        self.assertNotIn('set_ae_class_trait(',source)
        ast.parse(source)

    def test_locales(self):
        entries=transformed_resources()
        locale_tables=[parse_stbl(x[3]) for x in entries if x[0]==TYPE_STBL]
        self.assertEqual(len(locale_tables),2)
        self.assertTrue(all(LABEL_ID in t for t in locale_tables))


if __name__ == '__main__':
    unittest.main()
