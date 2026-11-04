"""M130 purely numerical and identity classification tests."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'/'m130_physical'))
from mhs130_physical_seat_audit import derive_board_anchors,evaluate_physical_seats

BOARD1={'x':400.63,'y':151.0,'z':516.45}
BOARD2={'x':372.63,'y':151.0,'z':516.45}


def student(sid,cls,board,pos,seat=None,posture='posture_Stand'):
    return {'sim_id':str(sid),'registered_class':cls,
            'target_whiteboard_id':board,'trait_matches':True,
            'is_selectable':False,
            'interaction':{
                'instance':'PRESENT','interaction_target_position':pos,
                'posture_type':posture,
                'posture_target_id':str(sid+300) if seat else None,
                'posture_target_position':seat,
                'posture_target_type':'object_chair_dining' if seat else None}}


def audit():
    students=[]
    for sid in range(1,9):
        students.append(student(sid,1,'A',BOARD1))
    for sid in range(9,17):
        students.append(student(sid,2,'B',BOARD2))
    return {'students':students}


class M130Test(unittest.TestCase):
    def test_reliable_runtime_anchors_require_both_class_observations(self):
        anchors,source=derive_board_anchors(audit())
        self.assertEqual(source,'OBSERVED_SEPARATE_CLASS_BOARDS')
        self.assertEqual(anchors[1]['id'],'A')
        self.assertEqual(anchors[2]['id'],'B')

    def test_class_two_on_class_one_chair_is_detected_even_after_book_started(self):
        a=audit()
        a['students'][8]=student(9,2,None,None,
            {'x':406.83,'y':151.0,'z':514.45},'posture_Sit')
        anchors,source=derive_board_anchors(a)
        result=evaluate_physical_seats(a,anchors,source)
        self.assertEqual(result['counts']['seat_near_other_class_board'],1)
        self.assertEqual(result['counts']['not_seated'],15)
        self.assertFalse(result['students'][8]['game_actions_changed'])

    def test_class_two_correct_chair_is_detected(self):
        a=audit()
        a['students'][8]=student(9,2,None,None,
            {'x':366.43,'y':151.0,'z':514.45},'posture_Sit')
        anchors,source=derive_board_anchors(a)
        result=evaluate_physical_seats(a,anchors,source)
        self.assertEqual(result['counts']['seat_near_registered_board'],1)

    def test_shared_target_not_enough_to_define_both_classes(self):
        a=audit()
        for r in a['students'][8:]:
            r['target_whiteboard_id']='A'
            r['interaction']['interaction_target_position']=BOARD1
        anchors,reason=derive_board_anchors(a)
        self.assertEqual(anchors,{})
        self.assertEqual(reason,'INSUFFICIENT_DISTINCT_BOARD_EVIDENCE')

    def test_old_anchor_is_fallback_when_all_using_books(self):
        a=audit()
        anchors,source=derive_board_anchors(a)
        for r in a['students']:
            r['target_whiteboard_id']=None
        remembered,reason=derive_board_anchors(a,anchors)
        self.assertEqual(remembered,anchors)
        self.assertEqual(reason,'PRIOR_OBSERVED_ANCHORS_NOT_RECONFIRMED')

    def test_toilet_is_not_a_chair_seat(self):
        a=audit()
        a['students'][0]=student(1,1,None,None,BOARD1,
                                  'posture_ToiletSit_Stall')
        anchors,source=derive_board_anchors(a)
        result=evaluate_physical_seats(a,anchors,source)
        self.assertEqual(result['counts']['not_seated'],16)

    def test_other_floor_not_claimed_room(self):
        a=audit()
        a['students'][8]=student(9,2,None,None,
            {'x':400.0,'y':155.0,'z':516.0},'posture_Sit')
        anchors,source=derive_board_anchors(a)
        result=evaluate_physical_seats(a,anchors,source)
        self.assertEqual(result['counts']['seat_ambiguous'],1)


if __name__=='__main__':
    unittest.main()
