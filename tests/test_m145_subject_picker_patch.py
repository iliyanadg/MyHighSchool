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
class CompoundTestList(tuple):
    pass
class Picker:
    def __init__(self,variant='ZERBU',branch_count=None):
        self.guid64=PICKER_ID
        self.__name__=('Zerbu_GTS5_WhiteboardStudentTestSnippet'
                       if variant=='ZERBU' else
                       'testSet_HighSchool_Active_PickWhiteboard_Student')
        self.test=CompoundTestList((
            tuple([object()]),)*(
            branch_count if branch_count is not None else
            (5 if variant=='ZERBU' else 4)))
def fixture(variant='ZERBU',branch_count=None):
    class ClassStart:
        guid64=CLASS_START_ID
        test_globals=TestList((SimInfoTest(),Picker(variant,branch_count)))
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
    def test_real_game_snippet_guid_not_strict_source_shape(self):
        start,subs=fixture()
        # Runtime may expand or reorder class-start test_globals.
        snippet=start.test_globals[1]
        start.test_globals=TestList(
            (TestSetReference(333),snippet,SimInfoTest(),
             TestSetReference(444)))
        d,undo=install_subject_picker(start,subs,True)
        self.assertTrue(d['applied'],d)
        self.assertTrue(all(x.test_globals[1] is snippet
                            for x in subs.values()))
        self.assertTrue(undo())
    def test_real_ea_variant_and_unpatched_snippet_refused(self):
        start,subs=fixture(variant='EA_ORIGINAL')
        d,undo=install_subject_picker(start,subs,True)
        self.assertTrue(d['applied'],d)
        self.assertTrue(undo())
        start,subs=fixture(variant='ZERBU',branch_count=4)
        d,undo=install_subject_picker(start,subs,True)
        self.assertFalse(d['applied'])
        self.assertEqual(d['reason'],'M139_PICKER_BRANCHES_NOT_PATCHED')
        self.assertIsNone(undo)
    def test_extra_runtime_tests_and_reordered_state_are_preserved(self):
        start,subs=fixture()
        marker=object()
        marker2=TestSetReference(555555)
        changed=subs[SUBJECT_IDS[0]]
        prior=changed.test_globals
        # The game variant has one added test; exact tuple length is not 3.
        changed.test_globals=TestList((prior[0],marker,prior[1],
                                       prior[2],marker2))
        old=changed.test_globals
        result,undo=install_subject_picker(start,subs,True)
        self.assertTrue(result['applied'],result)
        now=changed.test_globals
        self.assertEqual(len(now),5)
        self.assertIs(now[0],old[0])
        self.assertIs(now[1],marker)
        self.assertIs(now[2],start.test_globals[1])
        self.assertIs(now[3],old[3])
        self.assertIs(now[4],marker2)
        self.assertTrue(undo())
        self.assertIs(changed.test_globals,old)
    def test_unrecognized_subject_shape_fails_with_runtime_details(self):
        start,subs=fixture()
        subject=subs[SUBJECT_IDS[0]]
        subject.test_globals=TestList((SimInfoTest(),object(),
                                       TestSetReference(276240)))
        result,undo=install_subject_picker(start,subs,True)
        self.assertFalse(result['applied'])
        self.assertEqual(result['subject_guid'],SUBJECT_IDS[0])
        self.assertEqual(result['reason'],'SUBJECT_CLASS1_STATE_NOT_UNIQUE')
        self.assertEqual(len(result['runtime_test_shape']),3)
        self.assertIsNone(undo)
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
        self.assertEqual(data['reason'],'SUBJECT_CLASS1_STATE_NOT_UNIQUE')
        self.assertIsNotNone(data.get('runtime_test_shape'))
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
