"""M145: only known EA subject Attend class2 follow-through tuning adapter.

Evidence: EA XML from user's 2026-11-04 Sims4Studio extraction:
- 276774 (Class_Start) global tests are SimInfo + 279071 PickWhiteboard
- 293197 and 293200 subject Attend globals are teen playable, Class1_True,
  and subject-day test reference.
- 279071 PickWhiteboard has EA/Zerbu compatibility adapted by M139 to test
  exact trait and board on both classes (no assignment to the wrong board).
- NPC 297779 cannot safely be pushed on playables: its global test requires
  SimInfoTest(npc=True). This module NEVER changes the NPC affordance.

Patch subject interaction 'test_globals' by replacing ONLY their standalone
Class1-only StateTest with the very same PickWhiteboard TestSetReference object
used by the original Class_Start. The original subject/day tests stay intact.
All 8 known EA subjects are validated and patched together or NONE are patched.
Any unknown post-update tuning refuses the install. A restore callback restores
the exact original objects with identity checks; third-party changes refuse
restoration, rather than overwriting other mods.

This patch runs only under manually armed MHS and only after the M139 school
picker has been successfully adapted; no permanent package override.
"""
SUBJECT_IDS=(293193,293194,293195,293196,293197,293198,293199,293200)
CLASS_START_ID=276774
PICKER_ID=279071
CLASS1_STATE_ID=276075


def _typename(value):
    return type(value).__name__


def _ref_guid(item):
    if item is None:
        return None
    # TestSetReference has a tuned "test_set_reference" referencing the
    # actual immutable TestSetInstance, while StateTest.value is StateValue.
    for key in ('test_set_reference','value'):
        try:
            v=getattr(item,key,None)
            guid=getattr(v,'guid64',None)
            if type(guid) is int:
                return guid
        except Exception:
            pass
    return None


def _repr_has(item,name):
    try:
        return name in repr(item)
    except Exception:
        return False


def _is_picker_reference(item):
    if _typename(item)!='TestSetReference':
        return False
    guid=_ref_guid(item)
    return guid==PICKER_ID or (guid is None and
        _repr_has(item,'PickWhiteboard_Student'))


def _is_class1_state(item):
    if _typename(item)!='StateTest':
        return False
    guid=_ref_guid(item)
    return guid==CLASS1_STATE_ID or (guid is None and
        _repr_has(item,'HighSchool_Active_Whiteboard_Class1_True'))


def _validate_source(source):
    if source is None or getattr(source,'guid64',None)!=CLASS_START_ID:
        return None,'CLASS_START_AFFORDANCE_MISSING'
    original=getattr(source,'test_globals',None)
    if original is None:
        return None,'CLASS_START_TEST_GLOBALS_MISSING'
    try:
        tests=tuple(original)
    except Exception:
        return None,'CLASS_START_TEST_GLOBALS_UNREADABLE'
    if len(tests)!=2 or _typename(tests[0])!='SimInfoTest':
        return None,'CLASS_START_TESTS_CHANGED'
    if not _is_picker_reference(tests[1]):
        return None,'CLASS_START_PICKER_REF_UNVERIFIED'
    return tests[1],'EA_CLASS_START_PICKER_VERIFIED'


def _validate_subject(affordance,expected_guid):
    if affordance is None or getattr(affordance,'guid64',None)!=expected_guid:
        return None,'SUBJECT_NOT_FOUND'
    if 'super_HighSchool_Active_Whiteboard_Attend_' not in str(
            getattr(affordance,'__name__','')):
        return None,'NOT_KNOWN_SUBJECT_AFFORDANCE'
    old=getattr(affordance,'test_globals',None)
    if old is None:
        return None,'SUBJECT_GLOBAL_TESTS_MISSING'
    try:
        tests=tuple(old)
    except Exception:
        return None,'SUBJECT_GLOBAL_TESTS_UNREADABLE'
    if len(tests)!=3:
        return None,'SUBJECT_TESTS_CHANGED'
    if _typename(tests[0])!='SimInfoTest':
        return None,'SUBJECT_SIM_INFO_TEST_CHANGED'
    if not _is_class1_state(tests[1]):
        return None,'SUBJECT_CLASS1_STATE_UNVERIFIED'
    if _typename(tests[2])!='TestSetReference':
        return None,'SUBJECT_DAY_TEST_MISSING'
    if _is_picker_reference(tests[2]):
        return None,'SUBJECT_ALREADY_PATCHED_OR_WRONG_REFERENCE'
    return (old,tests),'SUBJECT_EXACT_VANILLA_TUNING_VERIFIED'


def install_subject_picker(source,subject_map,picker_patch_applied=False):
    """Return (result, rollback) with fail-closed behavior.

    A fully successful M139 patch is a strict prerequisite. Building the
    subject TestList by its existing type avoids inventing EA tuning objects.
    """
    if not picker_patch_applied:
        return {'applied':False,'reason':'M139_PICKER_NOT_APPLIED'},None
    picker,reason=_validate_source(source)
    if picker is None:
        return {'applied':False,'reason':reason},None
    if not isinstance(subject_map,dict) or set(subject_map)!=set(SUBJECT_IDS):
        return {'applied':False,'reason':'REQUIRE_ALL_EIGHT_EA_SUBJECTS'},None
    checked=[]
    for guid in SUBJECT_IDS:
        affordance=subject_map[guid]
        prior,why=_validate_subject(affordance,guid)
        if prior is None:
            return {'applied':False,'reason':why,
                    'subject_guid':guid},None
        old,original=prior
        try:
            new=type(old)((original[0],picker,original[2]))
            if len(tuple(new))!=3 or tuple(new)[1] is not picker:
                raise ValueError('NEW_TEST_LIST_SHAPE_INVALID')
        except Exception as exc:
            return {'applied':False,'reason':'TESTLIST_BUILD_'+type(exc).__name__,
                    'subject_guid':guid},None
        checked.append((affordance,old,new))
    changed=[]
    try:
        for obj,old,new in checked:
            obj.test_globals=new
            changed.append((obj,old,new))
            if getattr(obj,'test_globals',None) is not new:
                raise RuntimeError('TEST_GLOBALS_WRITE_NOT_CONFIRMED')
    except Exception as exc:
        restored=True
        for obj,old,new in reversed(changed):
            try:
                if getattr(obj,'test_globals',None) is new:
                    obj.test_globals=old
                if getattr(obj,'test_globals',None) is not old:
                    restored=False
            except Exception:
                restored=False
        return {'applied':False,
                'reason':'PATCH_'+type(exc).__name__,
                'rollback_verified':restored},None

    def undo():
        # Refuse partial restoration if another mod modified ANY entry.
        if any(getattr(obj,'test_globals',None) is not new
               for obj,old,new in checked):
            return False
        try:
            for obj,old,new in reversed(checked):
                obj.test_globals=old
            return all(getattr(obj,'test_globals',None) is old
                       for obj,old,new in checked)
        except Exception:
            return False

    return {
        'applied':True,
        'reason':'EA_EIGHT_SUBJECTS_CLASS_PICKER_REUSED',
        'original_297779_npc_affordance_unchanged':True,
        'subject_day_test_preserved':True,
        'player_class_selector_aligned_with_M139':True,
        'subject_ids':SUBJECT_IDS,
        'native_ea_test_bypass':False,
        'gameplay_seating_not_yet_verified':True,
    },undo
