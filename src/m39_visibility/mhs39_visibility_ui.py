"""Conditional M39 menu affordances. Experimental in-game behavior.

All existing interactions inherit their original Python implementations.
This module wraps ONLY the test result, so the UI can hide Class 3
when 2-class mode is enabled, and show only 'Enable' when deactivated.

The game's runtime test behavior and category nesting still need in-game
verification.  Use an actual TestResult(False) rather than the nonexistent
TestResult.FALSE class constant (M41 caused repeat LastExceptions on the mailbox). No school-attendance override or pause-time execution yet.
"""
from event_testing.results import TestResult
from interactions.base.picker_interaction import SimPickerInteraction
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
            config=_CONFIG.load(current_slot(allow_travel=True))
            show=available_from_settings(
                config,cls._mhs39_action,cls._mhs39_class)
        except Exception:
            # Settings errors must never reveal unsafe write operations.
            return TestResult(False, 'MY HIGH SCHOOL: azione non disponibile')
        if not show:
            return TestResult(False, 'MY HIGH SCHOOL: azione non disponibile')
        return super()._test(*args,**kwargs)


for _module,_name,_action,_klass in SPECS:
    # The M52 native multi-removal implementation is now in the existing
    # mhs27_remove_ui module, used by all three class actions. Avoid an
    # import of an optional mhs52_picker module absent from the 17-module
    # M51-compatible TS4 archive.
    _base=getattr(__import__(_module),_name)
    _wrapper='MHS39_'+_name
    globals()[_wrapper]=type(
        _wrapper,(_MHS39VisibilityMixin,_base),
        {'__module__':__name__,
         '_mhs39_action':_action,
         '_mhs39_class':_klass}
    )


# M45: the three *visible* 'Prepara iscrizione' buttons are EA
# SimPickerInteraction tunings. M39 deliberately left them unguarded,
# so the class categories remained on screen after disabling the
# school or Class 3 even though the other 19 actions disappeared.
# Create distinct subclasses because all three tunings share the same
# original SimPickerInteraction tuning class but have different class IDs.
for _class_number in (1, 2, 3):
    _class_name='MHS45ChooseClass{}'.format(_class_number)
    globals()[_class_name]=type(
        _class_name,(_MHS39VisibilityMixin,SimPickerInteraction),
        {'__module__':__name__,
         '_mhs39_action':'class',
         '_mhs39_class':_class_number}
    )



# M53: existing M52 affordances keep their exact tunings and menu classes.
# New staff actions use the proven M39 per-save visibility mixin. Their
# native UI and persistence live in mhs53_staff_ui / mhs53_staff_store.
from mhs53_staff_ui import STAFF_ACTIONS
for _token,_role,_mode,_klass in STAFF_ACTIONS:
    _staff_name='MHS53'+_token
    _staff_base=getattr(__import__('mhs53_staff_ui'),_staff_name)
    globals()['MHS39_'+_staff_name]=type(
        'MHS39_'+_staff_name,
        (_MHS39VisibilityMixin,_staff_base),
        {'__module__':__name__,
         '_mhs39_action':'class',
         '_mhs39_class':_klass})


# Only the unified build supplies the lifecycle owner. Historical M54 packages
# keep working without it; this imports no second attendance controller.
try:
    import mhs_classroom_bootstrap
except ImportError:
    pass
else:
    mhs_classroom_bootstrap.install()
