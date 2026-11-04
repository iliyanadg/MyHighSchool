"""M109 original EA descriptor snapshot, partial rollback and hook isolation.

Synthetic test classes ONLY. This does not validate an actual The Sims
runtime, compiled Mac bytecode or Bouncer assignment.
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src' / 'm109_activation'))

from mhs109_native_hook_stage import (
    M109NativeStage, KNOWN_HOOKS,
)


def count_class():
    class WeeklyDay(object):
        @classmethod
        def get_long_term_situation_count(cls, data, resolver):
            return (6, 6)
    return WeeklyDay


def install_count_hook(owner, fail=False, return_none=False):
    old = owner.__dict__['get_long_term_situation_count']

    def callback(plan, evidence):
        def wrapper(cls, data, resolver):
            return (8, 8)
        wrapper._mhs108_count_hook = True
        owner.get_long_term_situation_count = classmethod(wrapper)
        if fail:
            raise RuntimeError('EA hook changed but install interrupted')
        if return_none:
            return None

        def native_uninstall():
            owner.get_long_term_situation_count = old
            return True
        return native_uninstall
    return callback


def request_class():
    class Request(object):
        def __init__(self, value):
            self.value = value
        def get_additional_filter_terms(self):
            return ('EA_ORIGINAL',)
    return Request


class OriginalNativeHookStages(unittest.TestCase):
    def test_six_verified_original_method_names_are_stable(self):
        self.assertEqual(set(KNOWN_HOOKS), {
            'native_base_count','native_precreate',
            'school_filter_scope','no_show_guard',
            'unified_lessons','post_bouncer_observer'})
        self.assertEqual(
            KNOWN_HOOKS['school_filter_scope'][0],
            ('__init__','get_additional_filter_terms'))

    def test_classmethod_descriptor_is_restored_not_just_bound_method(self):
        owner = count_class()
        descriptor = owner.__dict__['get_long_term_situation_count']
        stage = M109NativeStage(
            'native_base_count', owner, install_count_hook(owner))
        self.assertTrue(stage.install(None, None))
        self.assertEqual(owner.get_long_term_situation_count(None,None),
                         (8, 8))
        self.assertTrue(stage.restore())
        self.assertIs(owner.__dict__['get_long_term_situation_count'],
                      descriptor)
        self.assertEqual(owner.get_long_term_situation_count(None,None),
                         (6, 6))

    def test_partial_install_raise_restores_already_modified_classmethod(self):
        owner = count_class()
        original = owner.__dict__['get_long_term_situation_count']
        stage = M109NativeStage(
            'native_base_count', owner, install_count_hook(owner,fail=True))
        with self.assertRaises(RuntimeError):
            stage.install(None,None)
        self.assertEqual(owner.get_long_term_situation_count(None,None),
                         (8,8))
        self.assertTrue(stage.restore())
        self.assertIs(owner.__dict__['get_long_term_situation_count'],
                      original)

    def test_no_returned_uninstall_callback_is_still_restorable(self):
        owner = count_class()
        old = owner.__dict__['get_long_term_situation_count']
        stage = M109NativeStage(
            'native_base_count', owner,
            install_count_hook(owner,return_none=True))
        self.assertFalse(stage.install(None,None))
        self.assertTrue(stage.restore())
        self.assertIs(owner.__dict__['get_long_term_situation_count'],old)

    def test_school_filter_scope_partial_two_function_install(self):
        owner = request_class()
        init = owner.__dict__['__init__']
        terms = owner.__dict__['get_additional_filter_terms']

        def partially_install(plan,evidence):
            def patch_init(self,value):
                init(self,value)
            patch_init._mhs108_school_filter = True
            owner.__init__ = patch_init
            # Critically, second method has NOT yet been patched.
            raise RuntimeError('failed between two school filter hooks')

        stage = M109NativeStage(
            'school_filter_scope',owner,partially_install)
        with self.assertRaises(RuntimeError):
            stage.install(None,None)
        self.assertIsNot(owner.__dict__['__init__'],init)
        self.assertIs(owner.__dict__['get_additional_filter_terms'],terms)
        self.assertTrue(stage.restore())
        self.assertIs(owner.__dict__['__init__'],init)
        self.assertIs(owner.__dict__['get_additional_filter_terms'],terms)
        self.assertEqual(owner(123).get_additional_filter_terms(),
                         ('EA_ORIGINAL',))

    def test_two_method_hook_full_native_restore(self):
        owner = request_class()
        init = owner.__dict__['__init__']
        terms = owner.__dict__['get_additional_filter_terms']

        def install(plan,evidence):
            def patch_init(self,value):
                init(self,value)
            def patch_terms(self):
                return ()
            patch_init._mhs108_school_filter=True
            patch_terms._mhs108_school_filter=True
            owner.__init__=patch_init
            owner.get_additional_filter_terms=patch_terms
            def undo():
                owner.__init__=init
                owner.get_additional_filter_terms=terms
                return True
            return undo

        stage=M109NativeStage('school_filter_scope',owner,install)
        self.assertTrue(stage.install(None,None))
        self.assertEqual(owner(3).get_additional_filter_terms(),())
        self.assertTrue(stage.restore())
        self.assertIs(owner.__dict__['__init__'],init)
        self.assertIs(owner.__dict__['get_additional_filter_terms'],terms)

    def test_foreign_patch_after_install_is_not_overwritten(self):
        owner=count_class()
        stage=M109NativeStage(
            'native_base_count',owner,install_count_hook(owner))
        self.assertTrue(stage.install(None,None))

        @classmethod
        def foreign(cls,data,resolver):
            return (44,44)
        owner.get_long_term_situation_count=foreign
        self.assertFalse(stage.restore())
        self.assertEqual(owner.get_long_term_situation_count(None,None),
                         (44,44))

    def test_classmethod_wrong_owner_does_not_install(self):
        parent = count_class()
        class Child(parent):
            pass
        stage=M109NativeStage(
            'native_base_count',Child,
            lambda m,e:None)
        # The actual descriptor owner for an inherited EA method is
        # the parent class, never Child.__dict__.
        self.assertFalse(stage.install(None,None))
        self.assertNotIn('get_long_term_situation_count', Child.__dict__)
        self.assertEqual(Child.get_long_term_situation_count(None,None),
                         (6,6))

    def test_missing_source_method_and_duplicate_install_fails_closed(self):
        class WrongOwner(object):
            pass
        stage=M109NativeStage(
            'native_base_count',WrongOwner,lambda m,e:None)
        self.assertFalse(stage.install(None,None))
        self.assertTrue(stage.restore())
        owner=count_class()
        stage=M109NativeStage('native_base_count',owner,
                              install_count_hook(owner))
        self.assertTrue(stage.install(None,None))
        self.assertFalse(stage.install(None,None))
        self.assertTrue(stage.restore())

    def test_cleanup_failure_keeps_restore_record_for_reporting(self):
        owner=count_class()
        attempts=[]
        def cleanup():
            attempts.append('cleanup')
            return len(attempts)>1

        stage=M109NativeStage('native_base_count',owner,
                              install_count_hook(owner),cleanup=cleanup)
        self.assertTrue(stage.install(None,None))
        self.assertFalse(stage.restore())
        self.assertEqual(attempts,['cleanup'])
        # Callback already restored owner but the per-request cleanup
        # can still be retried from the retained captured originals.
        self.assertTrue(stage.restore())
        self.assertEqual(attempts,['cleanup','cleanup'])


if __name__=='__main__':
    unittest.main()
