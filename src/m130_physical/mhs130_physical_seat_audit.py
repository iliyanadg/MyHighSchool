"""M130: Physical school-seat/room evidence from actual EA runtime objects.

NO WORLD MUTATION. Each Sim stays bound to the saved MHS registration.
Board anchor points require 2 independent students per registered class
pointing to the same EA whiteboard, and different boards for both groups.
Proximity to a board is diagnostic only; never claims literal room topology.
"""
import math

def _distance(a,b):
    if not isinstance(a,dict) or not isinstance(b,dict):
        return None
    try:
        dx=float(a['x'])-float(b['x'])
        dz=float(a['z'])-float(b['z'])
        dy=float(a['y'])-float(b['y'])
        if abs(dy)>2.0:
            return None
        return round(math.sqrt(dx*dx+dz*dz),2)
    except (KeyError,ValueError,TypeError,OverflowError):
        return None


def derive_board_anchors(audit,previous=None):
    """Only accept distinct boards with >=2 own-class observations."""
    counts={1:{},2:{}}
    positions={}
    for row in audit['students']:
        klass=int(row['registered_class'])
        board=row.get('target_whiteboard_id')
        detail=row.get('interaction',{})
        if board is None:
            continue
        position=detail.get('interaction_target_position')
        if not isinstance(position,dict):
            continue
        counts[klass][board]=counts[klass].get(board,0)+1
        positions[board]=position

    found={}
    for klass in (1,2):
        ranked=sorted(counts[klass].items(),key=lambda p:(-p[1],p[0]))
        if ranked and ranked[0][1]>=2:
            if len(ranked)==1 or ranked[0][1]>ranked[1][1]:
                found[klass]={'id':ranked[0][0],
                              'position':positions[ranked[0][0]],
                              'observations':ranked[0][1]}
    if (len(found)==2 and found[1]['id']!=found[2]['id']
            and _distance(found[1]['position'],found[2]['position']) is not None
            and _distance(found[1]['position'],found[2]['position'])>=18.0):
        return found,'OBSERVED_SEPARATE_CLASS_BOARDS'

    if isinstance(previous,dict) and set(previous)=={1,2}:
        a,b=previous[1],previous[2]
        if (a.get('id')!=b.get('id')
                and _distance(a.get('position'),b.get('position')) is not None
                and _distance(a['position'],b['position'])>=18.0):
            return previous,'PRIOR_OBSERVED_ANCHORS_NOT_RECONFIRMED'
    return {},'INSUFFICIENT_DISTINCT_BOARD_EVIDENCE'


def evaluate_physical_seats(audit,anchors,source):
    """Conservative; only reports a wrong zone when clearly closer to other board."""
    out=[]
    counts={'seat_near_registered_board':0,
            'seat_near_other_class_board':0,
            'seat_ambiguous':0,
            'not_seated':0,
            'not_instanced_or_unknown':0,
            'known_wrong_live_board':0}
    for row in audit['students']:
        klass=int(row['registered_class'])
        detail=row.get('interaction',{})
        posture=detail.get('posture_type') or ''
        seat=detail.get('posture_target_position')
        seatid=detail.get('posture_target_id')
        is_sitting=('posture_Sit' in posture and
                    'Toilet' not in posture and seatid is not None)
        target_board=row.get('target_whiteboard_id')
        other=3-klass
        expected=anchors.get(klass)
        another=anchors.get(other)
        current=(target_board is not None and expected is not None
                 and another is not None and
                 target_board==another['id'])
        if current:
            counts['known_wrong_live_board']+=1
        dx=_distance(seat,expected['position']) if expected else None
        dy=_distance(seat,another['position']) if another else None
        if detail.get('instance')!='PRESENT':
            category='NOT_INSTANCED_OR_UNKNOWN'
            counts['not_instanced_or_unknown']+=1
        elif not is_sitting:
            category='NOT_SEATED_IN_CHAIR'
            counts['not_seated']+=1
        elif dx is None or dy is None:
            category='SEAT_LOCATION_UNDETERMINED'
            counts['seat_ambiguous']+=1
        elif (dy<=16.0 and dx-dy>=8.0):
            category='SEAT_NEAR_OTHER_CLASS_BOARD'
            counts['seat_near_other_class_board']+=1
        elif (dx<=16.0 and dy-dx>=8.0):
            category='SEAT_NEAR_REGISTERED_CLASS_BOARD'
            counts['seat_near_registered_board']+=1
        else:
            category='SEAT_LOCATION_AMBIGUOUS'
            counts['seat_ambiguous']+=1
        out.append({
            'sim_id':row['sim_id'],
            'registered_class':klass,
            'is_selectable':row.get('is_selectable'),
            'class1_trait_matches':row.get('trait_matches'),
            'live_wrong_board':bool(current),
            'posture':posture,'posture_target_type':detail.get('posture_target_type'),
            'seat_object_id':seatid,
            'distance_to_registered_board':dx,
            'distance_to_other_board':dy,
            'classification':category,
            'game_actions_changed':False
        })
    return {'kind':'M130_PHYSICAL_BOARD_AND_SEAT_PROXIMITY',
            'anchor_source':source,
            'board_anchors':{str(k):v for k,v in anchors.items()},
            'counts':counts,'students':out,
            'does_not_certify_desk_in_classroom':True,
            'does_not_control_seating_or_player_actions':True,
            'game_mutations':0}
