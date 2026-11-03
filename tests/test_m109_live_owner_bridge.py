"""M109 live owner bridge regressions; no Sims imports or patches."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src' / 'm109_activation'))

from mhs109_readonly_ea_probe import METHOD_CONTRACT
from mhs109_live_owner_bridge import (
    EXPECTED_EA_OWNERS, resolve_six_native_stage_owners,
)


def ea_like_classes():
    """Fake class descriptors with names mirroring the observed EA probe.

    This is a shape-only fixture and never a proof of real EA game behavior.
    """
    attributes = {}
    for class_key, name, kind in METHOD_CONTRACT:
        def original(*args, **kwargs):
            return 'unchanged'
        attributes.setdefault(class_key, {})[name] = (
            classmethod(original) if kind == 'classmethod' else original)
    fake = {}
    for key, (attrs) in attributes.items():
        if key not in EXPECTED_EA_OWNERS:
            qualified = {
                'bouncer': 'situations.bouncer.bouncer.Bouncer',
                'base_situation': 'situations.base_situation.BaseSituation',
            }[key]
        else:
            qualified = EXPECTED_EA_OWNERS[key]
        namespace, name = qualified.rsplit('.', 1)
        fake[key] = type(name, (object,), dict(attrs, __module__=namespace))
    return fake


class M109LiveOwnerBridgeTests(unittest.TestCase):
    def test_six_real_layout_owners_resolve_without_mutation_or_install(self):
        classes = ea_like_classes()
        before = {key: dict(cls.__dict__) for key, cls in classes.items()}
        owners = resolve_six_native_stage_owners(classes)
        self.assertEqual(set(owners), {
            'native_base_count', 'native_precreate',
            'school_filter_scope', 'no_show_guard', 'unified_lessons',
            'post_bouncer_observer'})
        self.assertIs(owners['native_base_count'], classes['weekly_day'])
        self.assertIs(owners['native_precreate'],
                      classes['situation_manager'])
        self.assertIs(owners['school_filter_scope'],
                      classes['bouncer_request'])
        self.assertIs(owners['no_show_guard'],
                      classes['bouncer_request'])
        self.assertIs(owners['unified_lessons'], classes['weekly_data'])
        self.assertIs(owners['post_bouncer_observer'],
                      classes['situation_manager'])
        self.assertEqual(
            before, {key: dict(cls.__dict__) for key, cls in classes.items()})

    def test_report_owner_names_cannot_replace_actual_python_classes(self):
        with self.assertRaisesRegex(ValueError, 'CHANGED_OR_CONFLICTING'):
            resolve_six_native_stage_owners({
                'weekly_day': 'venues.weekly_schedule_zone_director.'
                              'WeeklyScheduleDay'})
        with self.assertRaisesRegex(ValueError, 'NOT_SUPPLIED'):
            resolve_six_native_stage_owners(None)

    def test_wrong_module_blocks_even_if_method_shape_matches(self):
        classes = ea_like_classes()
        classes['weekly_data'].__module__ = 'unknown_school_override'
        with self.assertRaisesRegex(ValueError, 'OWNER_CHANGED_unified_lessons'):
            resolve_six_native_stage_owners(classes)

    def test_split_bouncer_request_owners_block_school_filter_scope(self):
        classes = ea_like_classes()
        original = classes['bouncer_request']
        base = type('BouncerRequest', (object,), {
            '__module__':
                'situations.bouncer.bouncer_request',
            'get_additional_filter_terms':
                original.__dict__['get_additional_filter_terms'],
        })
        attrs = {
            k: v for k, v in original.__dict__.items()
            if k not in ('get_additional_filter_terms', '__dict__',
                         '__weakref__', '__doc__', '__module__')}
        attrs['__module__'] = 'situations.bouncer.bouncer_request'
        classes['bouncer_request'] = type('BouncerRequest', (base,), attrs)
        with self.assertRaisesRegex(ValueError, 'CHANGED_OR_CONFLICTING'):
            resolve_six_native_stage_owners(classes)

    def test_known_mhs_wrapper_marker_blocks_full_stage_graph(self):
        classes = ea_like_classes()
        classes['weekly_data'].__dict__['try_start'].__func__._mhs108_unified_lessons = True
        with self.assertRaisesRegex(ValueError, 'CHANGED_OR_CONFLICTING'):
            resolve_six_native_stage_owners(classes)

    def test_inherited_lookup_is_allowed_but_not_a_hook_owner(self):
        classes = ea_like_classes()
        manager = classes['situation_manager']
        parent = type('IndexedManager', (object,), {
            '__module__': 'indexed_manager',
            'get': manager.__dict__['get'],
        })
        own = {k: v for k, v in manager.__dict__.items()
               if k not in ('__module__', '__dict__', '__weakref__',
                            '__doc__', 'get')}
        own['__module__'] = 'situations.situation_manager'
        classes['situation_manager'] = type('SituationManager',
                                            (parent,), own)
        owners = resolve_six_native_stage_owners(classes)
        self.assertIs(owners['native_precreate'],
                      classes['situation_manager'])
        self.assertNotIn('get', owners)

if __name__ == '__main__':
    unittest.main()
