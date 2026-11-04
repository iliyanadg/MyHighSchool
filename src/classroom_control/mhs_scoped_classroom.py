"""Enrollment-scoped test-list dispatch using the verified EA run_tests API.

EA TestSetInstance calls test.run_tests(resolver, skip_safe_tests,
search_for_tooltip). Keep original results outside the verified school scope;
never rewrite an original result to True or cache a participant's enrollment.
No EA implementation or user data is included here.
"""


class ScopedTestList(object):
    _mhs_scoped = True

    def __init__(self, original, amended, scope, failure):
        if not all(callable(fn) for fn in (
                getattr(original, 'run_tests', None),
                getattr(amended, 'run_tests', None), scope, failure)):
            raise ValueError('VERIFIED_TEST_LIST_API_REQUIRED')
        self.original = original
        self.amended = amended
        self.scope = scope
        self.failure = failure

    def __iter__(self):
        return iter(self.amended)

    def __len__(self):
        return len(self.amended)

    def __getitem__(self, key):
        return self.amended[key]

    def run_tests(self, resolver, skip_safe_tests=False, search_for_tooltip=False):
        try:
            context = self.scope(resolver)
        except Exception:
            # A resolver from an unrelated mod must not break its EA behavior.
            return self.original.run_tests(resolver, skip_safe_tests, search_for_tooltip)
        if context is None:
            return self.original.run_tests(resolver, skip_safe_tests, search_for_tooltip)
        if (not isinstance(context, dict) or
                context.get('registered_class') not in (1, 2)):
            return self.failure('MHS: contesto classe non verificato')
        if context.get('board_class') != context['registered_class']:
            return self.failure('MHS: lavagna diversa dalla classe iscritta')
        return self.amended.run_tests(resolver, skip_safe_tests, search_for_tooltip)


def registered_board_context(resolver, actor_participant, object_participant,
                             membership, state1, state2):
    """Read the Actor/Object participants verified in EA resolver.pyc.

    Targetless early testing and unregistered actors retain original tests.
    Once a registered actor has an actual target, ambiguous board states
    cannot authorize another classroom. No traits, queues or goals are changed.
    """
    try:
        actor = resolver.get_participant(actor_participant)
        info = getattr(actor, 'sim_info', None)
        if info is None:
            info = actor
        sid = str(getattr(info, 'sim_id', None))
        klass = membership.get(sid)
        if klass not in (1, 2):
            return None
        target = resolver.get_participant(object_participant)
        if target is None:
            return None
    except Exception:
        return None
    result = {'sim_id': sid, 'registered_class': klass, 'board_class': None,
              'target_id': str(getattr(target, 'id', None))}
    try:
        first = bool(target.state_value_active(state1))
        second = bool(target.state_value_active(state2))
        if first != second:
            result['board_class'] = 1 if first else 2
    except Exception:
        pass
    return result


def install_native_board_guard(affordance, scope, failure):
    """Guard NPC 297779; preserve all its native tests and return exact undo."""
    if (affordance is None or getattr(affordance, 'guid64', None) != 297779 or
            'HighSchool_Active_AttendClass_NPC' not in str(
                getattr(affordance, '__name__', ''))):
        return {'applied': False, 'reason': 'NATIVE_NPC_AFFORDANCE_NOT_VERIFIED'}, None
    original = getattr(affordance, 'test_globals', None)
    if (type(original).__name__ not in ('TestList', 'CompoundTestList') or
            not callable(getattr(original, 'run_tests', None))):
        return {'applied': False, 'reason': 'NATIVE_NPC_TEST_LIST_NOT_VERIFIED'}, None
    wrapped = ScopedTestList(original, original, scope, failure)
    try:
        affordance.test_globals = wrapped
        if affordance.test_globals is not wrapped:
            raise ValueError('NPC_GUARD_WRITE_NOT_CONFIRMED')
    except Exception:
        if getattr(affordance, 'test_globals', None) is wrapped:
            affordance.test_globals = original
        return {'applied': False, 'reason': 'NPC_GUARD_NOT_INSTALLED'}, None

    def undo():
        if getattr(affordance, 'test_globals', None) is not wrapped:
            return False
        affordance.test_globals = original
        return affordance.test_globals is original
    undo.can_restore = lambda: getattr(affordance, 'test_globals', None) is wrapped
    return {'applied': True, 'reason': 'REGISTERED_NPC_BOARD_GUARD',
            'native_tests_preserved': True, 'outside_scope_original_results': True,
            'gameplay_arrival_not_yet_verified': True}, undo
