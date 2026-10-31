"""M55: automatic 2/3-class roster attendance safety and package regression tests."""
import ast
import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'/'m55_attendance'))

from mhs55_attendance_core import (
    AttendanceError, valid_student, roster_plan, school_running,
    already_in_base_student, DailyAttendance, create_student_request,
    BASE_STUDENT_SITUATION, BASE_STUDENT_JOB)
from tooling.build_m55_attendance_trial import (
    package_bytes, transformed_resources, ACTION_ID, SCRIPTS, LABEL_ID)
from tooling.build_m53_staff_management import package_bytes as m54_package
from tooling.build_m27_removal import TYPE_INTERACTION, TYPE_SNIPPET, TYPE_STBL
from tooling.m1_links_and_strings import parse_stbl
from tooling.simdata_release_gate import resources, inspect_bytes


def make_roster(assignments):
    class Roster(object):
        def class_members(self, klass):
            return [sid for sid, room in assignments.items() if room == klass]
    return Roster()


class M55Tests(unittest.TestCase):
    def test_human_teen_only(self):
        teenager, adult, human, dog = 1, 2, 10, 20
        self.assertTrue(valid_student(SimpleNamespace(age=teenager,species=human),
                                      teenager,human))
        for bad in (None,SimpleNamespace(age=adult,species=human),
                    SimpleNamespace(age=teenager,species=dog),
                    SimpleNamespace(age=teenager)):
            self.assertFalse(valid_student(bad,teenager,human))

    def test_full_roster_three_classes_and_stable_ids(self):
        ids={str(i):(1 if i <= 8 else 2 if i <= 16 else 3)
             for i in range(1,25)}
        roster=make_roster(ids)
        infos={i:SimpleNamespace(age=1,species=10) for i in range(1,25)}
        planned,bad=roster_plan(roster,3,infos.get,1,10)
        self.assertEqual(len(planned),24)
        self.assertEqual([p[0] for p in planned].count(1),8)
        self.assertEqual([p[0] for p in planned].count(2),8)
        self.assertEqual([p[0] for p in planned].count(3),8)
        self.assertEqual(bad,())
        self.assertEqual(planned[0],(1,'1'))
        self.assertEqual(planned[-1],(3,'24'))
        two,bad2=roster_plan(roster,2,infos.get,1,10)
        self.assertEqual(len(two),16)
        self.assertEqual(bad2,())

    def test_aged_up_missing_animal_not_invited_or_replaced(self):
        roster=make_roster({'1':1,'2':1,'3':2,'4':3})
        infos={1:SimpleNamespace(age=1,species=10),
               2:SimpleNamespace(age=2,species=10),
               3:SimpleNamespace(age=1,species=20)}
        planned,bad=roster_plan(roster,3,infos.get,1,10)
        self.assertEqual(planned,((1,'1'),))
        self.assertEqual(bad,((1,'2'),(2,'3'),(3,'4')))

    def test_full_class_limit_prevents_oversubscription(self):
        roster=make_roster({str(i):1 for i in range(1,10)})
        with self.assertRaises(AttendanceError):
            roster_plan(roster,2,lambda sid:SimpleNamespace(age=1,species=10),1,10)

    def test_school_gate_and_duplicates(self):
        present=SimpleNamespace(guid64=BASE_STUDENT_SITUATION)
        sim=object()
        info=SimpleNamespace(age=1,get_sim_instance=lambda:sim)
        manager=SimpleNamespace(get_situations_sim_is_in=lambda s:[present])
        self.assertTrue(school_running(manager,[info],1))
        self.assertTrue(already_in_base_student(manager,info))
        self.assertFalse(school_running(manager,[info],2))
        with self.assertRaises(AttendanceError):
            already_in_base_student(SimpleNamespace(),info)

    def test_full_batch_plan_no_duplicate_or_retry(self):
        plan=tuple((i//8+1,str(i)) for i in range(1,25))
        day=DailyAttendance('3',99,7,plan)
        collected=[]
        while not day.done:
            batch=day.next_batch(3)
            self.assertLessEqual(len(batch),3)
            for klass,sid in batch:
                day.record(sid,'requested')
                collected.append(sid)
        self.assertEqual(len(collected),24)
        self.assertEqual(len(set(collected)),24)
        self.assertEqual(day.next_batch(3),())
        self.assertEqual(day.summary()['requested'],24)
        self.assertTrue(day.same_session(3,99,7))
        self.assertFalse(day.same_session(3,99,8))
        self.assertFalse(day.same_session(5,99,7))

    def test_single_ea_call_for_each_batch_item(self):
        calls=[]
        guest=SimpleNamespace(added=[])
        guest.add_guest_info=guest.added.append
        guest_list=lambda **kwargs:guest
        guest_info=SimpleNamespace(construct_from_purpose=lambda sid,job,purpose:
                                   (sid,job.guid64,purpose))
        situation=SimpleNamespace(guid64=BASE_STUDENT_SITUATION)
        job=SimpleNamespace(guid64=BASE_STUDENT_JOB)
        manager=SimpleNamespace(create_situation=lambda *args,**kwargs:
                                calls.append((args,kwargs)) or len(calls))
        for sid in (1,2,3):
            response=create_student_request(manager,SimpleNamespace(sim_id=sid),
                                            situation,job,guest_list,guest_info,9)
            self.assertEqual(response,sid)
        self.assertEqual(len(calls),3)
        self.assertEqual(len(guest.added),3)
        self.assertTrue(all(not row[1]['user_facing'] for row in calls))

    def test_invalid_tuning_no_call(self):
        calls=[]
        manager=SimpleNamespace(create_situation=lambda *args,**kwargs:calls.append(1))
        with self.assertRaises(AttendanceError):
            create_student_request(
                manager,SimpleNamespace(sim_id=1),
                SimpleNamespace(guid64=1),
                SimpleNamespace(guid64=BASE_STUDENT_JOB),
                lambda **kwargs:None,None,None)
        self.assertEqual(calls,[])

    def test_m54_resources_preserved_except_stbl_and_injector(self):
        old=resources(m54_package())
        new=transformed_resources()
        self.assertEqual(len(old),62)
        self.assertEqual(len(new),63)
        changes=0
        for old_row,new_row in zip(old,new[:62]):
            self.assertEqual(old_row[:3],new_row[:3])
            if old_row!=new_row:
                changes+=1
                self.assertIn(old_row[0],(TYPE_SNIPPET,TYPE_STBL))
        self.assertEqual(changes,3)
        added=new[-1]
        self.assertEqual(added[:3],(TYPE_INTERACTION,0,ACTION_ID))
        tuning=ET.fromstring(added[3])
        self.assertEqual(tuning.get('m'),'mhs55_attendance_ui')
        self.assertEqual(tuning.find('./T[@n="display_name"]').text,
                         '0x{:08X}'.format(LABEL_ID))

    def test_package_and_22_script_modules(self):
        r=inspect_bytes(package_bytes())
        self.assertEqual(r['status'],'STATIC_GATE_PASSED')
        self.assertEqual(r['resource_count'],63)
        self.assertEqual(r['category_count'],10)
        self.assertEqual(r['simdata_count'],10)
        names=[f.name for f in SCRIPTS]
        self.assertEqual(len(names),22)
        self.assertEqual(len(set(names)),22)
        self.assertIn('mhs55_attendance_auto.py',names)
        self.assertIn('mhs55_attendance_core.py',names)
        self.assertIn('mhs55_attendance_ui.py',names)

    def test_auto_invites_without_picker_or_roster_write(self):
        auto=(ROOT/'src'/'m55_attendance'/'mhs55_attendance_auto.py').read_text()
        ui=(ROOT/'src'/'m55_attendance'/'mhs55_attendance_ui.py').read_text()
        ast.parse(auto)
        ast.parse(ui)
        self.assertIn('on_loading_screen_animation_finished',auto)
        self.assertIn('alarms.add_alarm(',auto)
        self.assertIn('settings.active',auto)
        self.assertIn('roster_plan(',auto)
        self.assertIn('current_slot()',auto)
        self.assertIn('school_running(',auto)
        self.assertIn('already_in_base_student(',auto)
        self.assertIn('session.next_batch(_BATCH)',auto)
        self.assertIn('session.record(sid, \'requested\')',auto)
        self.assertNotIn('_ROSTERS.save(',auto)
        self.assertNotIn('UiSimPicker',ui)
        self.assertIn('status_lines()',ui)

    def test_stbl_has_new_readonly_status_action(self):
        tables=[parse_stbl(x[3]) for x in transformed_resources()
                if x[0]==TYPE_STBL]
        self.assertEqual(len(tables),2)
        self.assertTrue(all(LABEL_ID in t for t in tables))
        self.assertTrue(any('presenze automatiche' in t[LABEL_ID]
                            for t in tables))


if __name__=='__main__':
    unittest.main()
