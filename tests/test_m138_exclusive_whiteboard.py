"""M138 player class-only whiteboard tests; offline structure validation."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'/'m138_zerbu_exclusive'))
from mhs138_exclusive_whiteboard import install_exclusive_playable_whiteboard_rules

class SimInfoTest:
    def __init__(self,npc):self.npc=npc
class StateTest:pass
class Trait:
    def __repr__(self):return '<Trait:trait_HighSchool_Active_Class1Student>'
class TraitTest:
    def __init__(self,positive):
        self.whitelist_traits=(Trait(),) if positive else ()
        self.blacklist_traits=() if positive else (Trait(),)
    def __repr__(self):return 'TraitTest Class1Student'
class SituationJobTest:pass
class CompoundTestList(list):pass
class Zerbu_GTS5_WhiteboardStudentTestSnippet:
    guid64=279071
class Affordance:
    test_globals=[Zerbu_GTS5_WhiteboardStudentTestSnippet]

def original():
    return CompoundTestList([
        (SimInfoTest(False),StateTest()),
        (TraitTest(True),StateTest()),
        (SimInfoTest(True),TraitTest(False),StateTest()),
        (SituationJobTest(),)])

class Tests(unittest.TestCase):
    def setUp(self):
        Zerbu_GTS5_WhiteboardStudentTestSnippet.test=original()

    def test_class1_player_must_now_hold_class1_trait(self):
        old=Zerbu_GTS5_WhiteboardStudentTestSnippet.test
        result,undo=install_exclusive_playable_whiteboard_rules(Affordance)
        self.assertTrue(result['applied'])
        new=Zerbu_GTS5_WhiteboardStudentTestSnippet.test
        self.assertEqual(len(new),5)
        self.assertIs(new[0][0],old[0][0])
        self.assertIs(new[0][1],old[1][0])
        self.assertIs(new[0][2],old[0][1])
        self.assertIs(new[3][1],old[2][1])
        self.assertIs(new[3][2],old[2][2])
        self.assertIs(new[1],old[1])
        self.assertIs(new[2],old[2])
        self.assertIs(new[4],old[3])
        self.assertTrue(undo())
        self.assertIs(Zerbu_GTS5_WhiteboardStudentTestSnippet.test,old)

    def test_reject_unrecognized_game_test_layout(self):
        old=Zerbu_GTS5_WhiteboardStudentTestSnippet.test
        old[0]=(SimInfoTest(True),StateTest())
        result,undo=install_exclusive_playable_whiteboard_rules(Affordance)
        self.assertFalse(result['applied'])
        self.assertIsNone(undo)
        self.assertIs(Zerbu_GTS5_WhiteboardStudentTestSnippet.test,old)

    def test_reject_wrong_trait_polarity(self):
        old=Zerbu_GTS5_WhiteboardStudentTestSnippet.test
        old[1]=(TraitTest(False),StateTest())
        result,undo=install_exclusive_playable_whiteboard_rules(Affordance)
        self.assertFalse(result['applied'])
        self.assertIsNone(undo)

    def test_never_auto_add_or_remove_students(self):
        old=Zerbu_GTS5_WhiteboardStudentTestSnippet.test
        result,undo=install_exclusive_playable_whiteboard_rules(Affordance)
        self.assertNotIn('students_changed',result)
        self.assertTrue(result['npc_class2_preserved'])
        self.assertTrue(result['zerbu_elementary_preserved'])
        self.assertTrue(undo())

if __name__=='__main__':unittest.main()
