"""Save-independent attendance facts and bounded EA lesson requests.

This module never imports the game, cancels actions, changes jobs or clocks,
creates situations, teleports Sims, or completes goals. A positive decision
only permits the caller to run the ORIGINAL EA interaction test. It does not
authorize bypassing a failed native test and never proves physical attendance.

Use one LessonRequestLedger per school day. Prep and lesson share a student's
budget, while the afternoon gets its own budget. All time inputs are processed
simulation time, not the displayed UI clock.
"""

_CLASS_ACTIONS = (
    'highschool_active_whiteboard_', 'highschool_active_usebook_class',
    'highschool_active_createbook_class', 'highschool_active_writeonbook',
    'highschool_active_listen_',
)
_PROTECTED_GAMEPLAY = (
    'detention', 'catchtruant', 'trytoavoiddetention',
    'social_highschool_active', 'toilet', 'shower', 'sleep',
    'sickness', 'pregnancy', 'food_eat', 'generic_consume_food',
    'eat_to_clean_from_sit', 'orderfood',
    'highschool_active_npc_lunch_createfood',
)


def classroom_action(action_name):
    """True only for an observed/queued recognized school interaction name."""
    if not isinstance(action_name, str):
        return False
    name = action_name.lower()
    return any(token in name for token in _CLASS_ACTIONS)


def protected_gameplay(action_name):
    """Shared protection for needs, discipline, meals and existing lessons."""
    if not isinstance(action_name, str):
        return False
    name = action_name.lower()
    return classroom_action(name) or any(
        token in name for token in _PROTECTED_GAMEPLAY)


def _minute(clock):
    if not isinstance(clock, dict):
        return None
    hour, minute = clock.get('hour'), clock.get('minute')
    if (type(hour) is not int or type(minute) is not int or
            not 0 <= hour < 24 or not 0 <= minute < 60):
        return None
    return hour * 60 + minute


def _student_id(raw):
    if type(raw) not in (str, int):
        return None
    sid = str(raw)
    if not sid.isdigit() or int(sid) < 1 or str(int(sid)) != sid:
        return None
    return sid


def classify_attendance(registered, invited=None, has_native_job=None,
                        present=None, request_accepted=None,
                        running_class=None, seated_in_class=None,
                        ea_completion_observed=None, protected=False):
    """Describe the most advanced observed stage, preserving unknown facts.

    The caller must pass completion=True ONLY after independent EA completion
    evidence. Neither a request, an action nor a seat supplies that evidence.
    In particular NOT_INVITED is only reported when invited is explicitly False.
    No absent observation is silently changed into False or into success.
    """
    if registered is not True:
        stage = 'NOT_REGISTERED' if registered is False else 'REGISTRATION_UNKNOWN'
    elif ea_completion_observed is True:
        stage = 'EA_COMPLETION_OBSERVED'
    elif running_class is True and seated_in_class is True:
        stage = 'CLASS_ACTION_AND_PHYSICAL_SEAT_OBSERVED'
    elif running_class is True:
        stage = 'CLASS_ACTION_OBSERVED'
    elif protected is True:
        stage = 'PROTECTED_GAMEPLAY'
    elif has_native_job is True and present is False:
        stage = 'ADMITTED_NOT_INSTANTIATED'
    elif present is True and has_native_job is False:
        stage = 'PRESENT_WITHOUT_CLASS_JOB'
    elif request_accepted is True:
        stage = 'REQUEST_ACCEPTED_NOT_OBSERVED'
    elif request_accepted is False:
        stage = 'REQUEST_REFUSED'
    elif has_native_job is True:
        stage = 'NATIVE_JOB_OBSERVED'
    elif seated_in_class is True:
        stage = 'PHYSICAL_SEAT_WITHOUT_CLASS_ACTION'
    elif invited is True and has_native_job is False:
        stage = 'INVITED_NOT_ADMITTED'
    elif invited is True:
        stage = 'INVITED_ADMISSION_UNKNOWN'
    elif invited is False:
        stage = 'NOT_INVITED'
    else:
        stage = 'REGISTERED_INVITATION_UNKNOWN'
    return {
        'stage': stage,
        'registered': registered,
        'invited': invited,
        'has_native_job': has_native_job,
        'present': present,
        'request_accepted': request_accepted,
        'running_class': running_class,
        'seated_in_class': seated_in_class,
        'ea_completion_observed': ea_completion_observed,
        'completion_known': type(ea_completion_observed) is bool,
        'completion_not_inferred_from_queue_or_seat': True,
    }


class LessonRequestLedger(object):
    """Bound requests by student and EA period, not successful-first-push.

    decision() is read-only. record_result() consumes one actual native test /
    push attempt, including native refusals. A not-instanced observation alone
    consumes no attempt. observe() prevents a later duplicate request after a
    real class action has already been observed in this period.
    """
    def __init__(self, max_attempts=3, min_gap_minutes=3):
        if type(max_attempts) is not int or not 1 <= max_attempts <= 3:
            raise ValueError('MAX_ATTEMPTS_MUST_BE_BETWEEN_ONE_AND_THREE')
        if type(min_gap_minutes) is not int or min_gap_minutes < 3:
            raise ValueError('MINIMUM_THREE_SIM_MINUTES_BETWEEN_ATTEMPTS')
        self.max_attempts = max_attempts
        self.min_gap_minutes = min_gap_minutes
        self._states = {}

    def _key(self, period, sid):
        ident = _student_id(sid)
        if period not in ('morning', 'afternoon') or ident is None:
            return None
        return period, ident

    def state(self, period, sid):
        key = self._key(period, sid)
        existing = self._states.get(key, {})
        return {
            'attempts': existing.get('attempts', 0),
            'requested': existing.get('requested', False),
            'accepted': existing.get('accepted', False),
            'observed': existing.get('observed', False),
            'last_minute': existing.get('last_minute'),
            'last_reason': existing.get('last_reason'),
            'native_test_required': True,
        }

    def decision(self, period, sid, registered_class, clock,
                 has_native_job, correct_board, instanced,
                 running_action='', queued_actions=None,
                 native_phase_created=False, phase='lesson',
                 context_verified=False):
        key = self._key(period, sid)
        if key is None or type(registered_class) is not int or registered_class not in (1, 2):
            return False, 'UNENROLLED_OR_INVALID'
        if context_verified is not True:
            return False, 'SESSION_CONTEXT_UNVERIFIED'
        now = _minute(clock)
        if now is None:
            return False, 'SIM_CLOCK_UNAVAILABLE'
        if phase not in ('preparation', 'lesson'):
            return False, 'UNKNOWN_EA_PHASE'
        start = 10 * 60 if period == 'morning' else 14 * 60
        if phase == 'preparation':
            allowed = start - 30 <= now < start
        else:
            allowed = start <= now <= start + 24
        if not allowed:
            return False, 'OUTSIDE_EA_PHASE_WINDOW'
        if native_phase_created is not True:
            return False, 'NATIVE_PHASE_NOT_CONFIRMED'
        if has_native_job is not True:
            return False, 'NATIVE_CLASS_JOB_MISSING'
        if correct_board is not True:
            return False, 'REGISTERED_CLASS_BOARD_UNVERIFIED'
        if instanced is not True:
            return False, 'NOT_INSTANCED'
        if not isinstance(running_action, str):
            return False, 'RUNNING_ACTION_UNAVAILABLE'
        if not isinstance(queued_actions, (tuple, list)) or any(
                not isinstance(name, str) for name in queued_actions):
            return False, 'QUEUE_CONTEXT_UNAVAILABLE'
        if protected_gameplay(running_action) or any(
                protected_gameplay(name) for name in queued_actions):
            return False, 'EXISTING_CLASS_OR_PROTECTED_GAMEPLAY'
        previous = self.state(period, sid)
        if previous['observed']:
            return False, 'CLASS_ACTION_ALREADY_OBSERVED'
        if previous['attempts'] >= self.max_attempts:
            return False, 'REQUEST_BUDGET_EXHAUSTED'
        last = previous['last_minute']
        if last is not None and now < last:
            return False, 'SCHOOL_DAY_RESET_REQUIRED'
        if last is not None and now - last < self.min_gap_minutes:
            return False, 'WAIT_FOR_NATIVE_QUEUE'
        return True, 'ORIGINAL_EA_INTERACTION_TEST_REQUIRED'

    def record_result(self, period, sid, clock, accepted, reason,
                      native_test_passed=None):
        key = self._key(period, sid)
        now = _minute(clock)
        if key is None or now is None or type(accepted) is not bool:
            raise ValueError('INVALID_NATIVE_REQUEST_RESULT')
        if accepted and native_test_passed is not True:
            raise ValueError('ACCEPTANCE_REQUIRES_ORIGINAL_EA_TEST')
        previous = self.state(period, sid)
        if previous['attempts'] >= self.max_attempts:
            raise ValueError('REQUEST_BUDGET_EXHAUSTED')
        last = previous['last_minute']
        if last is not None and now - last < self.min_gap_minutes:
            raise ValueError('REQUEST_INTERVAL_NOT_RESPECTED')
        self._states[key] = {
            'attempts': previous['attempts'] + 1,
            'requested': True,
            'accepted': previous['accepted'] or accepted,
            'observed': previous['observed'],
            'last_minute': now,
            'last_reason': str(reason)[:180],
        }

    def observe(self, period, sid, running_action):
        key = self._key(period, sid)
        if key is None or not classroom_action(running_action):
            return False
        previous = self.state(period, sid)
        previous['observed'] = True
        self._states[key] = previous
        return True
