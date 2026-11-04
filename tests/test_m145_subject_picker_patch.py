"""M145 exact EA subject follow-through patch offline regressions.

Use source-derived TestList and StateTest fakes. This test proves strict
validation, preservation and rollback but not game runtime seating.
"""
import ast
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'/'m145_class2_playable'))
from mhs145_subject_picker_patch import (
    install_subject_picker,SUBJECT_IDS,CLASS_START_ID,PICKER_ID,
    CLASS1_STATE_ID)

class TestList(tuple):
    def __new__(cls,items=()):
        return tuple.__new__(cls,items)

class Tuning:
    def __init__(self,guid):self.guid64=guid
class SimInfoTest:pass
class StateTest:
    def __init__(self,guid):
        self.value=Tuning(guid)
class TestSetReference:
    def __init__(self,guid):self.test_set_reference=Tuning(guid)
def fixture():
    class ClassStart:
        guid64=CLASS_START_ID
        test_globals=TestList((SimInfoTest(),TestSetReference(PICKER_ID)))
    subject={}
    for n,guid in enumerate(SUBJECT_IDS):
        cls=type('super_HighSchool_Active_Whiteboard_Attend_S{}'.format(n),(),{
            'guid64':guid,
            'test_globals':TestList((SimInfoTest(),StateTest(CLASS1_STATE_ID),
                                     TestSetReference(276240+n)))})
        subject[guid]=cls
    return ClassStart,subject

class Cases(unittest.TestCase):
    def test_replaces_only_class1_state_with_same_real_picker(self):
        start,subs=fixture()
        before={g:sub.test_globals for g,sub in subs.items()}
        data,undo=install_subject_picker(start,subs,True)
        self.assertTrue(data['applied'],data)
        picker=start.test_globals[1]
        for g,sub in subs.items():
            tests=sub.test_globals
            self.assertIs(tests[0],before[g][0])
            self.assertIs(tests[1],picker)
            self.assertIs(tests[2],before[g][2])
        self.assertTrue(undo())
        for g,sub in subs.items():
            self.assertIs(sub.test_globals,before[g])
    def test_does_not_patch_without_m139_adapter(self):
        start,subs=fixture()
        prior={g:x.test_globals for g,x in subs.items()}
        data,undo=install_subject_picker(start,subs,False)
        self.assertFalse(data['applied'])
        self.assertIsNone(undo)
        self.assertTrue(all(prior[k] is v.test_globals for k,v in subs.items()))
    def test_refuse_changed_tuning_and_unknown_subject(self):
        start,subs=fixture()
        subs[SUBJECT_IDS[-1]].test_globals=TestList(
            (SimInfoTest(),StateTest(276077),TestSetReference(276240)))
        data,undo=install_subject_picker(start,subs,True)
        self.assertFalse(data['applied'])
        self.assertEqual(data['reason'],'SUBJECT_CLASS1_STATE_UNVERIFIED')
        self.assertIsNone(undo)
    def test_refuse_incomplete_ea_subjects(self):
        start,subs=fixture()
        subs.pop(SUBJECT_IDS[0])
        d,undo=install_subject_picker(start,subs,True)
        self.assertFalse(d['applied'])
        self.assertIsNone(undo)
    def test_refuse_restore_over_third_party_mod(self):
        start,subs=fixture()
        data,undo=install_subject_picker(start,subs,True)
        self.assertTrue(data['applied'])
        sub=subs[SUBJECT_IDS[0]]
        foreign=TestList((SimInfoTest(),))
        sub.test_globals=foreign
        self.assertFalse(undo())
        self.assertIs(sub.test_globals,foreign)
    def test_subject_day_tests_never_removed(self):
        start,subs=fixture()
        origs={g:sub.test_globals[2] for g,sub in subs.items()}
        d,undo=install_subject_picker(start,subs,True)
        self.assertTrue(d['subject_day_test_preserved'])
        self.assertTrue(d['original_297779_npc_affordance_unchanged'])
        self.assertTrue(all(origs[g] is sub.test_globals[2] for g,sub in subs.items()))
    def test_no_gameplay_bypass_in_adapter(self):
        source=(ROOT/'src'/'m145_class2_playable'/
            'mhs145_subject_picker_patch.py').read_text(encoding='utf-8')
        ast.parse(source)
        self.assertNotIn('push_super_affordance(',source)
        self.assertNotIn('set_state(',source)
        self.assertNotIn('.trait_tracker.add_trait(',source)
        self.assertIn("getattr(obj,'test_globals',None) is new",source)
if __name__=='__main__':unittest.main()
