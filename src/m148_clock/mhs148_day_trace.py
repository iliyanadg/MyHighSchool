"""M148 lightweight read-only school-day event journal (Python 3.7 compatible).

Records observations, never decides whether a Sim attended a class.
A running interaction is a point-in-time observation, not proof of completion.
The journal includes lunch to diagnose ordering queues and crowding.
"""
import json
import os

MAX_SAMPLES = 200
FLUSH_EVERY = 50
OUTPUT = 'MHS_M148_GIORNATA_LEZIONI_MENSA.json'


def _str(value):
    if value is None:
        return None
    return str(value)[:180]


def _type(value):
    if value is None:
        return None
    klass = type(value)
    return str(getattr(klass, '__module__', '')) + '.' + str(
        getattr(klass, '__name__', ''))


def _position(obj):
    if obj is None:
        return None
    try:
        point = getattr(obj, 'position', None)
        if point is None:
            return None
        return {key: round(float(getattr(point, key)), 2)
                for key in ('x', 'y', 'z')}
    except (AttributeError, TypeError, ValueError, OverflowError):
        return None


def observe_student(info, klass):
    """Read-only sample of one registered teen; never touches interactions."""
    sid = _str(getattr(info, 'sim_id', None)) if info else None
    row = {
        'sim_id': sid,
        'registered_class': klass,
        'selectable': getattr(info, 'is_selectable', None) if info else None,
        'sim_present': False,
        'running_action': None,
        'action_target': None,
        'action_target_id': None,
        'action_target_position': None,
        'position': None,
        'posture': None,
        'queue_details_available': False,
        'running_action_completion_unknown': True,
    }
    if info is None:
        row['diagnostic'] = 'SIM_INFO_MISSING'
        return row
    try:
        sim = info.get_sim_instance()
    except Exception as exc:
        row['diagnostic'] = 'SIM_INSTANCE_' + type(exc).__name__
        return row
    if sim is None:
        row['diagnostic'] = 'NOT_SPAWNED'
        return row
    row['sim_present'] = True
    row['position'] = _position(sim)
    try:
        row['posture'] = _type(getattr(sim, 'posture', None))
    except Exception as exc:
        row['posture'] = 'READ_' + type(exc).__name__
    try:
        queue = getattr(sim, 'queue', None)
        action = getattr(queue, 'running', None) if queue else None
        row['running_action'] = _type(action)
        target = getattr(action, 'target', None) if action else None
        row['action_target'] = _type(target)
        ident = getattr(target, 'id', None) if target else None
        row['action_target_id'] = _str(ident)
        row['action_target_position'] = _position(target)
    except Exception as exc:
        row['diagnostic'] = 'ACTION_READ_' + type(exc).__name__
    return row


class DayJournal(object):
    def __init__(self, folder, slot, groups, output=None):
        self.folder = folder
        self.slot = str(slot)
        self.output=OUTPUT if output is None else output
        if (not isinstance(self.output,str) or not self.output.startswith('MHS_')
                or os.path.basename(self.output)!=self.output
                or not self.output.endswith('.json')):
            raise ValueError('INVALID_JOURNAL_FILENAME')
        self.groups = tuple(tuple(str(i) for i in group)
                            for group in groups)
        if len(self.groups) != 2 or any(len(g) != 8 for g in self.groups):
            raise ValueError('TWO_CLASSES_OF_EIGHT_REQUIRED')
        if len(set(self.groups[0] + self.groups[1])) != 16:
            raise ValueError('DUPLICATE_STUDENT')
        self.samples = []
        self.errors = []
        self.write_error = None

    def append(self, clock, students, event='interval', player_jobs=None,
               auto_reports=None):
        if len(self.samples) >= MAX_SAMPLES:
            return False
        if len(students) != 16:
            self.errors.append('INCOMPLETE_STUDENT_SAMPLE')
            return False
        self.samples.append({
            'event': str(event)[:80],
            'clock': clock,
            'students': students,
            'player_jobs': player_jobs if player_jobs is not None else [],
            'auto_push_reports': auto_reports if auto_reports is not None else [],
        })
        if len(self.samples) % FLUSH_EVERY == 0:
            self.flush()
        return True

    def flush(self):
        try:
            if not os.path.isdir(self.folder):
                os.makedirs(self.folder)
            target = os.path.join(self.folder, self.output)
            temp = target + '.tmp'
            data = {
                'kind': 'M143_READ_ONLY_SCHOOL_DAY_JOURNAL',
                'save_slot': self.slot,
                'class_1': self.groups[0],
                'class_2': self.groups[1],
                'snapshots': self.samples,
                'errors': self.errors,
                'game_state_mutations_by_journal': 0,
                'sampled_interactions_not_proof_of_completion': True,
                'lunch_service_outcome_not_inferred': True,
                'missing_events_between_samples_possible': True,
            }
            with open(temp, 'w', encoding='utf-8') as stream:
                json.dump(data, stream, ensure_ascii=False, indent=2)
            os.replace(temp, target)
            self.write_error = None
            return True
        except Exception as exc:
            self.write_error = type(exc).__name__
            return False
