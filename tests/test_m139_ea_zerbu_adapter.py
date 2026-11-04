"""M139 original EA and Zerbu GTS5 whiteboard compatibility regression."""
import unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'/'m139_general_whiteboards'))
from mhs139_ea_zerbu_adapter import install_known_whiteboard_adapter

class SimInfoTest:
    def __init__(self,npc):self.npc=npc
class StateTest:pass
class Trait:
    def __repr__(self):return '<Trait:(trait_HighSchool_Active_Class1Student)>'
class TraitTest:
    def __init__(self,is_positive):
        self.whitelist_traits=(Trait(),) if is_positive else ()
        self.blacklist_traits=() if is_positive else (Trait(),)
class SituationJobTest:
    situation_jobs=frozenset(('Zerbu_GTS5_ElementaryStudentBase',))
class CompoundTestList(list):pass
class testSet_HighSchool_Active_PickWhiteboard_Student:
    guid64=279071
class Zerbu_GTS5_WhiteboardStudentTestSnippet:
    guid64=279071

def setup(groups=3):
    base=[
      (SimInfoTest(False),StateTest()),
      (TraitTest(True),StateTest()),
      (SimInfoTest(True),TraitTest(False),StateTest())
    ]
    return CompoundTestList(base+[(SituationJobTest(),)] if groups==4 else base)

class TestM139(unittest.TestCase):
    def test_native_ea_exclusive_class_boards(self):
        testSet_HighSchool_Active_PickWhiteboard_Student.test=setup()
        class Affordance:
            test_globals=[testSet_HighSchool_Active_PickWhiteboard_Student]
        old=testSet_HighSchool_Active_PickWhiteboard_Student.test
        data,undo=install_known_whiteboard_adapter(Affordance)
        self.assertTrue(data['applied'])
        self.assertEqual(data['variant'],'EA_ORIGINAL')
        new=testSet_HighSchool_Active_PickWhiteboard_Student.test
        self.assertEqual(len(new),4)
        self.assertIs(new[0][1],old[1][0])
        self.assertIs(new[3][1],old[2][1])
        self.assertIs(new[1],old[1])
        self.assertIs(new[2],old[2])
        self.assertTrue(undo())
        self.assertIs(testSet_HighSchool_Active_PickWhiteboard_Student.test,old)

    def test_zerbu_elementary_is_untouched(self):
        Zerbu_GTS5_WhiteboardStudentTestSnippet.test=setup(4)
        class Affordance:
            test_globals=[Zerbu_GTS5_WhiteboardStudentTestSnippet]
        old=Zerbu_GTS5_WhiteboardStudentTestSnippet.test
        data,undo=install_known_whiteboard_adapter(Affordance)
        self.assertTrue(data['applied'])
        self.assertEqual(data['variant'],'ZERBU')
        new=Zerbu_GTS5_WhiteboardStudentTestSnippet.test
        self.assertEqual(len(new),5)
        self.assertIs(new[-1],old[-1])
        self.assertIs(new[2],old[2])
        self.assertTrue(undo())

    def test_unrecognized_mod_test_fails_closed(self):
        class Other:
            __name__='Other'
            guid64=279071
            test=setup()
        class Affordance:
            test_globals=[Other]
        before=Other.test
        data,undo=install_known_whiteboard_adapter(Affordance)
        self.assertFalse(data['applied'])
        self.assertIsNone(undo)
        self.assertIs(Other.test,before)

    def test_invalid_class_trait_fails_closed(self):
        testSet_HighSchool_Active_PickWhiteboard_Student.test=setup()
        old=testSet_HighSchool_Active_PickWhiteboard_Student.test
        old[1]=(TraitTest(False),StateTest())
        class Affordance:
            test_globals=[testSet_HighSchool_Active_PickWhiteboard_Student]
        data,undo=install_known_whiteboard_adapter(Affordance)
        self.assertFalse(data['applied'])
        self.assertIsNone(undo)
        self.assertIs(testSet_HighSchool_Active_PickWhiteboard_Student.test,old)

if __name__=='__main__':unittest.main()
