"""Conditional M39 menu affordances. Experimental in-game behavior.

All existing interactions inherit their original Python implementations.
This module wraps ONLY the test result, so the UI can hide Class 3
when 2-class mode is enabled, and show only 'Enable' when deactivated.

The game's runtime test behavior and category nesting still need in-game
verification.  Use an actual TestResult(False) rather than the nonexistent
TestResult.FALSE class constant (M41 caused repeat LastExceptions on the mailbox). No school-attendance override or pause-time execution yet.
"""
from event_testing.results import TestResult
from mhs_m2_game_bridge import current_slot
from mhs34_settings_ui import _CONFIG
from mhs39_visibility_rules import available_from_settings

# Tuple: original source module, original tuning class, action type, class
SPECS=(
 ('mhs25_confirmation','MHS25StageConfirmClass1','class',1),
 ('mhs25_confirmation','MHS25StageConfirmClass2','class',2),
 ('mhs28_controls','MHS28StageConfirmClass3','class',3),
 ('mhs27_remove_ui','MHS27RemoveClass1','class',1),
 ('mhs27_remove_ui','MHS27RemoveClass2','class',2),
 ('mhs28_controls','MHS28RemoveClass3','class',3),
 ('mhs29_controls','MHS29ViewClass1','class',1),
 ('mhs29_controls','MHS29ViewClass2','class',2),
 ('mhs29_controls','MHS29ViewClass3','class',3),
 ('mhs32_transfer_ui','MHS32Transfer1To2','transfer',(1,2)),
 ('mhs32_transfer_ui','MHS32Transfer1To3','transfer',(1,3)),
 ('mhs32_transfer_ui','MHS32Transfer2To1','transfer',(2,1)),
 ('mhs32_transfer_ui','MHS32Transfer2To3','transfer',(2,3)),
 ('mhs32_transfer_ui','MHS32Transfer3To1','transfer',(3,1)),
 ('mhs32_transfer_ui','MHS32Transfer3To2','transfer',(3,2)),
 ('mhs34_settings_ui','MHS34Enable','enable',0),
 ('mhs34_settings_ui','MHS34Disable','disable',0),
 ('mhs34_settings_ui','MHS34TwoClasses','deactivate_third',0),
 ('mhs34_settings_ui','MHS34ThreeClasses','activate_third',0),
)


class _MHS39VisibilityMixin(object):
    @classmethod
    def _test(cls,*args,**kwargs):
        try:
            config=_CONFIG.load(current_slot())
            show=available_from_settings(
                config,cls._mhs39_action,cls._mhs39_class)
        except Exception:
            # Settings errors must never reveal unsafe write operations.
            return TestResult(False, 'MY HIGH SCHOOL: azione non disponibile')
        if not show:
            return TestResult(False, 'MY HIGH SCHOOL: azione non disponibile')
        return super()._test(*args,**kwargs)


for _module,_name,_action,_klass in SPECS:
    _base=getattr(__import__(_module),_name)
    _wrapper='MHS39_'+_name
    globals()[_wrapper]=type(
        _wrapper,(_MHS39VisibilityMixin,_base),
        {'__module__':__name__,
         '_mhs39_action':_action,
         '_mhs39_class':_klass}
    )
