"""M137 narrowly scoped repair to Zerbu GTS5 high-school board test.

The live M136 report verified four OR alternatives in the TestSet:
  (npc=False, class1 board)
  (Class1 trait, class1 board)
  (npc=True, not Class1 trait, class2 board)
  (Zerbu Elementary situation job)
We add one *additional* EA-native test alternative, and keep every existing
branch, including Elementary, untouched. Applies only in the MHS school
session; original is restored on STOP.

No external tuning IDs or fake situation jobs. No player teleport or push.
"""
SNIPPET_GUID=279071

def _typ(obj,expected):
    return expected in type(obj).__name__


def install_class2_playable_alternative(affordance):
    """Returns (result,undo), no partial edits on validation failures."""
    if affordance is None:
        return {'applied':False,'reason':'AFFORDANCE_MISSING'},None
    globals_tests=getattr(affordance,'test_globals',None)
    candidate=None
    for item in globals_tests or ():
        if getattr(item,'guid64',None)==SNIPPET_GUID:
            candidate=item
            break
    if candidate is None:
        return {'applied':False,'reason':'LIVE_SNIPPET_NOT_279071'},None
    if 'Zerbu_GTS5_WhiteboardStudentTestSnippet' not in candidate.__name__:
        return {'applied':False,'reason':'NOT_IDENTIFIED_ZERBU_SNIPPET'},None
    original=getattr(candidate,'test',None)
    if original is None or not _typ(original,'CompoundTestList'):
        return {'applied':False,'reason':'EXPECTED_COMPOUND_TESTS_MISSING'},None
    groups=tuple(original)
    if len(groups)!=4:
        return {'applied':False,'reason':'EXPECTED_FOUR_OR_GROUPS_MISSING'},None
    if any(not isinstance(group,(tuple,list)) for group in groups):
        return {'applied':False,'reason':'UNEXPECTED_TEST_GROUP'},None
    if tuple(map(len,groups))!=(2,2,3,1):
        return {'applied':False,'reason':'UNEXPECTED_OR_GROUP_LENGTHS'},None
    one,trait,state=groups[0][0],groups[2][1],groups[2][2]
    if (not _typ(one,'SimInfoTest') or
            getattr(one,'npc',None) is not False or
            not _typ(trait,'TraitTest') or
            not _typ(state,'StateTest') or
            not _typ(groups[3][0],'SituationJobTest')):
        return {'applied':False,'reason':'UNEXPECTED_ZERBU_TEST_TYPES'},None
    # Note: class2 board and trait gate are the *existing* original EA
    # test instances, so we cannot accidentally target class1 board.
    # A registered-MHS-enrollment predicate cannot be expressed by these
    # EA test objects. The alternative therefore only exists while MHS is
    # active at the original high-school lot; not elsewhere.
    group=(one,trait,state)
    try:
        patched=type(original)(tuple(groups[:3])+(group,)+tuple(groups[3:]))
        candidate.test=patched
        if getattr(candidate,'test',None) is not patched:
            raise RuntimeError('PATCH_NOT_STORED')
    except Exception as exc:
        try:candidate.test=original
        except Exception:pass
        return {'applied':False,'reason':'PATCH_'+type(exc).__name__},None
    def undo():
        if getattr(candidate,'test',None) is patched:
            candidate.test=original
            return True
        return False
    return {'applied':True,'reason':'CLASS2_PLAYABLE_BRANCH_ADDED',
            'old_groups':len(groups),'new_groups':len(patched),
            'elementary_branch_preserved':patched[-1] is groups[-1],
            'npc_branch_preserved':patched[2] is groups[2]},undo
