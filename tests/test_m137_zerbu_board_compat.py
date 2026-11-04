"""M137 preserves all original Zerbu test branches and allows new Class2-player case only on exact known shape."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'/'m137_zerbu'))
from mhs137_zerbu_board_compat import install_class2_playable_alternative

class SimInfoTest:
    def __init__(self,npc):self.npc=npc
class StateTest:pass
class TraitTest:pass
class SituationJobTest:pass
class CompoundTestList(list):pass
class Zerbu_GTS5_WhiteboardStudentTestSnippet:
    guid64=279071
    test=CompoundTestList([
        (SimInfoTest(False),StateTest()),
        (TraitTest(),StateTest()),
        (SimInfoTest(True),TraitTest(),StateTest()),
        (SituationJobTest(),)])
class Affordance:
    test_globals=[Zerbu_GTS5_WhiteboardStudentTestSnippet]

class Tests(unittest.TestCase):
    def setUp(self):
        Zerbu_GTS5_WhiteboardStudentTestSnippet.test=CompoundTestList([
            (SimInfoTest(False),StateTest()),
            (TraitTest(),StateTest()),
            (SimInfoTest(True),TraitTest(),StateTest()),
            (SituationJobTest(),)])

    def test_new_class2_player_only_uses_existing_ea_native_tests(self):
        original=Zerbu_GTS5_WhiteboardStudentTestSnippet.test
        result,undo=install_class2_playable_alternative(Affordance)
        self.assertTrue(result['applied'])
        patched=Zerbu_GTS5_WhiteboardStudentTestSnippet.test
        self.assertEqual(len(patched),5)
        self.assertIs(patched[0],original[0])
        self.assertIs(patched[2],original[2])
        self.assertIs(patched[-1],original[-1])
        self.assertIs(patched[3][0],original[0][0])
        self.assertIs(patched[3][1],original[2][1])
        self.assertIs(patched[3][2],original[2][2])
        self.assertTrue(undo())
        self.assertIs(Zerbu_GTS5_WhiteboardStudentTestSnippet.test,original)

    def test_rejects_unknown_modified_test_hierarchy_without_mutation(self):
        original=Zerbu_GTS5_WhiteboardStudentTestSnippet.test
        original.append((TraitTest(),))
        result,undo=install_class2_playable_alternative(Affordance)
        self.assertFalse(result['applied'])
        self.assertIsNone(undo)
        self.assertIs(Zerbu_GTS5_WhiteboardStudentTestSnippet.test,original)

if __name__=='__main__':unittest.main()
