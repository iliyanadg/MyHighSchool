"""M145: only known EA subject Attend class2 follow-through tuning adapter.

Evidence: EA XML from user's 2026-11-04 Sims4Studio extraction:
- 276774 (Class_Start) global tests are SimInfo + 279071 PickWhiteboard
- 293197 and 293200 exported subject Attend globals are teen playable,
  Class1_True, and subject-day test reference. Other six EA subjects might
  have additional runtime tests: preserve every other item and its position.
- 279071 PickWhiteboard has EA/Zerbu compatibility adapted by M139 to test
  exact trait and board on both classes (no assignment to the wrong board).
- NPC 297779 cannot safely be pushed on playables: its global test requires
  SimInfoTest(npc=True). This module NEVER changes the NPC affordance.

Patch subject interaction 'test_globals' by replacing ONLY their standalone
Class1-only StateTest with the very same PickWhiteboard TestSetReference object
used by the original Class_Start. The original subject/day tests stay intact.
All 8 known EA subjects require exactly one recognized SimInfoTest, a
unique Class1-only StateTest, and at least one subject day test. The latter
may be the exported XML's TestSetReference or the game's expanded
HashedTunedInstanceMetaclass testSet_HighSchool_Active_* tuning instance.
Every other existing test is preserved in its original order. All eight are
patched together or NONE are patched; unknown post-update tuning refuses the
install with a compact runtime shape diagnostic. A restore callback restores
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
    """Find M139's actual tuned EA/Zerbu picker, not a wrapper position.

    Under EA runtime a TestSetReference in exported XML is resolved into a
    snippet instance with guid64 279071. M139 already uses this exact source.
    Its class-start globals can have a runtime-expanded shape, so requiring
    len(test_globals)==2 or a TestSetReference object rejects valid installs.
    """
    if source is None or getattr(source,'guid64',None)!=CLASS_START_ID:
        return None,'CLASS_START_AFFORDANCE_MISSING'
    original=getattr(source,'test_globals',None)
    if original is None:
        return None,'CLASS_START_TEST_GLOBALS_MISSING'
    try:
        tests=tuple(original)
    except Exception:
        return None,'CLASS_START_TEST_GLOBALS_UNREADABLE'
    snippets=[test for test in tests
              if getattr(test,'guid64',None)==PICKER_ID and
              getattr(test,'__name__',None) in (
                  'testSet_HighSchool_Active_PickWhiteboard_Student',
                  'Zerbu_GTS5_WhiteboardStudentTestSnippet')]
    if len(snippets)!=1:
        return None,'CLASS_START_PICKER_NOT_UNIQUE_OR_MISSING'
    picker=snippets[0]
    # The M139 installer validated the game's expected OR-branch hierarchy
    # and appended precisely one playable Class2 branch, retaining EA NPC
    # and Zerbu Elementary branches. Confirm that applied shape remains.
    tests=getattr(picker,'test',None)
    if getattr(tests,'_mhs_scoped',False):
        tests=tests.amended
    if type(tests).__name__!='CompoundTestList':
        return None,'PICKER_IS_NOT_COMPOUND'
    try:
        groups=tuple(tests)
    except Exception:
        return None,'PICKER_BRANCHES_UNREADABLE'
    target_count=(5 if getattr(picker,'__name__',None)==
                  'Zerbu_GTS5_WhiteboardStudentTestSnippet' else 4)
    if len(groups)!=target_count:
        return None,'M139_PICKER_BRANCHES_NOT_PATCHED'
    return picker,'VERIFIED_M139_EA_ZERBU_PICKER_INSTANCE'

def _is_subject_day_test(item):
    """Accept only known forms of EA subject/day TestSet tuning.

    XML references are often resolved by Sims4 runtime into an actual tuned
    class object, whose metaclass is HashedTunedInstanceMetaclass. Do not
    accidentally accept the Class1/2 PickWhiteboard selector as the day test.
    """
    if _typename(item)=='TestSetReference':
        return not _is_picker_reference(item)
    if _typename(item)=='HashedTunedInstanceMetaclass':
        name=str(getattr(item,'__name__',''))
        return (name.startswith('testSet_HighSchool_Active_')
                and 'PickWhiteboard' not in name)
    return False


def _test_shape(tests):
    """Return compact JSON-friendly read-only shape for game diagnostics."""
    result=[]
    for index,item in enumerate(tests):
        try:
            label=repr(item)
        except Exception:
            label='<unprintable>'
        result.append({'index':index,'type':_typename(item),
                       'ref_guid':_ref_guid(item) or
                       getattr(item,'guid64',None),
                       'name':str(getattr(item,'__name__',''))[:90],
                       'label':label[:120]})
    return tuple(result)


def _validate_subject(affordance,expected_guid):
    """Identify exact unique EA semantic tests, NOT exact tuple offsets.

    Subject test_globals may be extended by a pack update or by another mod.
    The known class-specific StateTest and original subject test references
    must remain intact, and the patch must preserve every other test.
    """
    if affordance is None or getattr(affordance,'guid64',None)!=expected_guid:
        return None,'SUBJECT_NOT_FOUND',None
    if 'super_HighSchool_Active_Whiteboard_Attend_' not in str(
            getattr(affordance,'__name__','')):
        return None,'NOT_KNOWN_SUBJECT_AFFORDANCE',None
    old=getattr(affordance,'test_globals',None)
    if old is None:
        return None,'SUBJECT_GLOBAL_TESTS_MISSING',None
    try:
        tests=tuple(old)
    except Exception:
        return None,'SUBJECT_GLOBAL_TESTS_UNREADABLE',None
    shape=_test_shape(tests)
    if not (2 <= len(tests) <= 12):
        return None,'SUBJECT_TEST_COUNT_UNRECOGNIZED',shape
    if sum(_typename(x)=='SimInfoTest' for x in tests)!=1:
        return None,'SUBJECT_SIM_INFO_TEST_NOT_UNIQUE',shape
    candidates=[i for i,x in enumerate(tests) if _is_class1_state(x)]
    if len(candidates)!=1:
        return None,'SUBJECT_CLASS1_STATE_NOT_UNIQUE',shape
    references=[x for x in tests if _typename(x)=='TestSetReference']
    if any(_is_picker_reference(x) for x in references):
        return None,'SUBJECT_ALREADY_PATCHED_OR_WRONG_REFERENCE',shape
    # M145c incorrectly rejected the live, unpacked EA tuning class.
    # E.g. the player's game represents the subject test as
    # <class 'sims4.tuning.instances.testSet_HighSchool_Active_...'>.
    if not any(_is_subject_day_test(x) for x in tests):
        return None,'SUBJECT_DAY_TEST_MISSING',shape
    return (old,tests,candidates[0]),'SUBJECT_CLASS1_STATE_UNIQUE',shape

def install_subject_picker(source,subject_map,picker_patch_applied=False,
                           scope=None,failure=None):
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
        prior,why,shape=_validate_subject(affordance,guid)
        if prior is None:
            return {'applied':False,'reason':why,'subject_guid':guid,
                    'runtime_test_shape':shape},None
        old,original,index=prior
        try:
            new_tests=list(original)
            new_tests[index]=picker
            new=type(old)(tuple(new_tests))
            if (len(tuple(new))!=len(original)
                    or tuple(new)[index] is not picker
                    or any(tuple(new)[i] is not original[i]
                           for i in range(len(original)) if i!=index)):
                raise ValueError('NEW_TEST_LIST_PRESERVATION_INVALID')
        except Exception as exc:
            return {'applied':False,'reason':'TESTLIST_BUILD_'+type(exc).__name__,
                    'subject_guid':guid,'runtime_test_shape':shape},None
        if scope is not None:
            try:
                from mhs_scoped_classroom import ScopedTestList
                new=ScopedTestList(old,new,scope,failure)
            except (TypeError,ValueError):
                return {'applied':False,'reason':'SCOPED_TESTLIST_API_NOT_SUPPORTED',
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
    undo.can_restore=lambda:all(getattr(obj,'test_globals',None) is new
                                for obj,old,new in checked)

    return {
        'applied':True,
        'reason':'EA_EIGHT_SUBJECTS_CLASS_PICKER_REUSED',
        'original_297779_npc_affordance_unchanged':True,
        'subject_day_test_preserved':True,
        'player_class_selector_aligned_with_M139':True,
        'subject_ids':SUBJECT_IDS,
        'native_ea_test_bypass':False,
        'enrollment_scoped':scope is not None,
        'gameplay_seating_not_yet_verified':True,
    },undo
