"""M109 offline read-only native method probe regressions, Python 3.7."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src' / 'm109_activation'))

from mhs109_readonly_ea_probe import (
    METHOD_CONTRACT, inspect_runtime_shapes,
)


def fixture():
    """Synthetic EA surfaces. NOT imported from an actual Sims runtime."""
    owners = {}
    for key, name, kind in METHOD_CONTRACT:
        owners.setdefault(key, {})
        def original(*args, **kwargs):
            return 'EA_ORIGINAL'
        owners[key][name] = (
            classmethod(original) if kind == 'classmethod' else original)
    classes = {key: type('FakeEA_' + key, (object,), descriptors)
               for key, descriptors in owners.items()}
    return classes


class M109NativeEAReadOnlyProbeTests(unittest.TestCase):

    def test_all_expected_ea_method_shapes_present_but_not_live_verified(self):
        classes = fixture()
        originals = {name: dict(cls.__dict__)
                     for name, cls in classes.items()}
        result = inspect_runtime_shapes(classes)
        self.assertEqual(result['status'],
                         'METHOD_SHAPES_AVAILABLE_UNVERIFIED')
        self.assertEqual(result['method_count_expected'],
                         len(METHOD_CONTRACT))
        self.assertEqual(result['method_count_available'],
                         len(METHOD_CONTRACT))
        self.assertEqual(result['problems'], ())
        self.assertFalse(result['activation_authorized_by_game'])
        self.assertFalse(result['ea_live_provenance_verified'])
        self.assertFalse(result['full_16_student_attendance_verified'])
        self.assertFalse(result['mutated_game_objects'])
        self.assertEqual({name: dict(cls.__dict__)
                          for name, cls in classes.items()}, originals)

    def test_situation_manager_get_can_be_inherited_without_wrong_owner(self):
        classes = fixture()
        parent = type('FakeManagerBase', (object,),
                      {'get': classes['situation_manager'].__dict__['get']})
        child = type('FakeSituationManager', (parent,), {
            k:v for k,v in classes['situation_manager'].__dict__.items()
            if k not in ('get', '__module__', '__dict__',
                         '__weakref__', '__doc__')
        })
        classes['situation_manager'] = child
        result = inspect_runtime_shapes(classes)
        self.assertEqual(result['status'],
                         'METHOD_SHAPES_AVAILABLE_UNVERIFIED')
        get_observation = [
            item for item in result['method_observations']
            if item['class_key'] == 'situation_manager'
            and item['method_name'] == 'get'][0]
        self.assertTrue(
            get_observation['declaring_owner'].endswith('FakeManagerBase'))

    def test_missing_orig_ea_method_fails_closed(self):
        classes = fixture()
        class Missing(object):
            pass
        classes['base_situation'] = Missing
        report = inspect_runtime_shapes(classes)
        self.assertEqual(report['status'], 'NATIVE_EA_METHODS_NOT_READY')
        self.assertTrue(report['problems'])
        self.assertFalse(report['activation_authorized_by_game'])

    def test_wrong_classmethod_descriptor_does_not_count_as_ea(self):
        classes = fixture()
        classes['weekly_data'] = type(
            'WrongEAData', (object,),
            {'try_start': lambda *args: None})
        report = inspect_runtime_shapes(classes)
        self.assertIn(
            ('weekly_data','try_start','EA_METHOD_DESCRIPTOR_MISMATCH'),
            report['problems'])

    def test_competing_old_m108_hook_is_detected(self):
        classes = fixture()
        original = classes['weekly_data'].__dict__['try_start'].__func__
        original._mhs108_class1_bridge = True
        report = inspect_runtime_shapes(classes)
        self.assertIn(
            ('weekly_data','try_start',
             'COMPETING_SCHOOL_HOOK_ALREADY_INSTALLED'),
            report['problems'])

    def test_bad_class_objects_and_empty_input_do_not_become_proof(self):
        result = inspect_runtime_shapes({'bouncer':object()})
        self.assertEqual(result['status'], 'NATIVE_EA_METHODS_NOT_READY')
        self.assertEqual(result['method_count_available'], 0)
        self.assertEqual(inspect_runtime_shapes(None)['method_count_available'],
                         0)

    def test_bouncer_request_filter_is_checked_as_two_separate_methods(self):
        report = inspect_runtime_shapes(fixture())
        names = {item['method_name'] for item in
                 report['method_observations']
                 if item['class_key']=='bouncer_request'}
        self.assertIn('__init__', names)
        self.assertIn('get_additional_filter_terms', names)
        self.assertIn('clone_for_replace', names)


if __name__ == '__main__':
    unittest.main()
