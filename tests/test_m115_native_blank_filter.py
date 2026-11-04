"""M115 native EA TunableSimFilter.BLANK_FILTER reader tests (offline)."""
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'/'m115_filter'))
from mhs115_native_blank_filter import (
    inspect_native_blank_filter, native_blank_matches,
)


class NativeBlank(object):
    repurpose_game_breaker = False

    def get_filter_terms(self):
        return ()

    def get_additional_conform_terms(self):
        return ()

    def is_aggregate_filter(self):
        return False


def modules(blank=None,missing=False):
    filters=types.ModuleType('filters')
    filters.__path__=[]
    tunable=types.ModuleType('filters.tunable')
    if blank is None:
        blank=NativeBlank()
    attrs={} if missing else {'BLANK_FILTER':blank}
    tunable.TunableSimFilter=type('TunableSimFilter',(),attrs)
    filters.tunable=tunable
    return {'filters':filters,'filters.tunable':tunable}


class M115NativeEABlankTests(unittest.TestCase):
    def test_read_exact_EA_constant_and_no_mutation(self):
        blank=NativeBlank()
        with patch.dict(sys.modules,modules(blank)):
            result,proof=inspect_native_blank_filter()
            self.assertIs(result,blank)
            self.assertTrue(native_blank_matches(blank))
            self.assertFalse(native_blank_matches(NativeBlank()))
        self.assertEqual(proof['status'],
                         'EA_BLANK_CONSTANT_INSPECTED_NOT_BOUNCER_AUTHORIZED')
        self.assertTrue(proof['native_constant_loaded'])
        self.assertFalse(proof['bouncer_request_patched'])
        self.assertFalse(proof['activation_authorized'])
        self.assertFalse(proof['bouncer_blank_filter_safe_in_game'])
        self.assertEqual(blank.get_filter_terms(),())

    def test_absent_constant_fails_closed(self):
        with patch.dict(sys.modules,modules(missing=True)):
            result,proof=inspect_native_blank_filter()
            self.assertIsNone(result)
            self.assertEqual(proof['status'],'NATIVE_EA_BLANK_FILTER_MISSING')

    def test_nonempty_terms_rejected(self):
        class Restricted(NativeBlank):
            def get_filter_terms(self):
                return ('alien terms',)
        with patch.dict(sys.modules,modules(Restricted())):
            result,proof=inspect_native_blank_filter()
        self.assertIsNone(result)
        self.assertFalse(proof['filter_terms_observed_empty'])

    def test_nonempty_conform_terms_rejected(self):
        class Conform(NativeBlank):
            def get_additional_conform_terms(self):
                return ('alien conform',)
        with patch.dict(sys.modules,modules(Conform())):
            result,proof=inspect_native_blank_filter()
        self.assertIsNone(result)
        self.assertFalse(proof['conform_terms_observed_empty'])

    def test_aggregate_filter_rejected(self):
        class Aggregate(NativeBlank):
            def is_aggregate_filter(self):
                return True
        with patch.dict(sys.modules,modules(Aggregate())):
            result,proof=inspect_native_blank_filter()
        self.assertIsNone(result)
        self.assertFalse(proof['aggregate_filter_observed_false'])

    def test_missing_methods_and_repurpose_flag_rejected(self):
        with patch.dict(sys.modules,modules(object())):
            result,proof=inspect_native_blank_filter()
        self.assertIsNone(result)
        self.assertEqual(proof['status'],
                         'NATIVE_EA_BLANK_FILTER_METHODS_MISSING')
        class NoFlag(NativeBlank):
            repurpose_game_breaker=None
        with patch.dict(sys.modules,modules(NoFlag())):
            result,proof=inspect_native_blank_filter()
        self.assertIsNone(result)
        self.assertFalse(proof['filter_repurpose_flag_observed'])

    def test_unsafe_boolean_or_misleading_list_is_not_equivalent(self):
        class Bogus(NativeBlank):
            def is_aggregate_filter(self):
                return 0
        with patch.dict(sys.modules,modules(Bogus())):
            result,proof=inspect_native_blank_filter()
        self.assertIsNone(result)
        self.assertFalse(proof['aggregate_filter_observed_false'])


if __name__=='__main__':
    unittest.main()
