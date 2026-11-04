"""M139 compatible class-exclusive player whiteboards: EA original + Zerbu.

Installed only by an explicitly armed MHS controller. This is a targeted
tuning adapter, *not* a final universal enrollment filter: MHS pre-lesson
Class1Student synchronization must succeed for its saved registry.
Expected test shape:
EA original: 3 OR alternatives:
  player Class1, trait Class1 board, NPC Class2
Zerbu GTS5: same plus existing Elementary situation-job exception.
No existing NPC/Elementary branch is changed. Exact identity and structure
validation; do nothing if a new game update changes the test hierarchy.
"""
SNIPPET_ID=279071
ZERBU_NAME='Zerbu_GTS5_WhiteboardStudentTestSnippet'
EA_NAME='testSet_HighSchool_Active_PickWhiteboard_Student'

def _type(obj,cls):
    return type(obj).__name__==cls

def _check_trait_test(test,attribute):
    value=getattr(test,attribute,None)
    if value is None or len(value)!=1:
        return False
    return 'trait_HighSchool_Active_Class1Student' in repr(tuple(value)[0])

def install_known_whiteboard_adapter(affordance):
    """Return status and undo callback; refuse unknown tuning structures."""
    if affordance is None:
        return {'applied':False,'reason':'PLAYER_AFFORDANCE_MISSING'},None
    snippet=next((test for test in getattr(affordance,'test_globals',()) or ()
                  if getattr(test,'guid64',None)==SNIPPET_ID),None)
    if snippet is None:
        return {'applied':False,'reason':'PICK_WHITEBOARD_TESTSET_MISSING'},None
    name=getattr(snippet,'__name__',None)
    if name not in (EA_NAME,ZERBU_NAME):
        return {'applied':False,'reason':'UNKNOWN_EA_OR_ZERBU_TESTSET'},None
    old=getattr(snippet,'test',None)
    if not _type(old,'CompoundTestList'):
        return {'applied':False,'reason':'TESTSET_NOT_COMPOUND'},None
    groups=tuple(old)
    expected=4 if name==ZERBU_NAME else 3
    if len(groups)!=expected or tuple(len(g) for g in groups[:3])!=(2,2,3):
        return {'applied':False,'reason':'UNKNOWN_OR_BRANCHES'},None
    player,positive,negative=groups[:3]
    if not (
        _type(player[0],'SimInfoTest') and
        getattr(player[0],'npc',None) is False and
        _type(player[1],'StateTest') and
        _type(positive[0],'TraitTest') and
        _type(positive[1],'StateTest') and
        _check_trait_test(positive[0],'whitelist_traits') and
        _type(negative[0],'SimInfoTest') and
        getattr(negative[0],'npc',None) is True and
        _type(negative[1],'TraitTest') and
        _check_trait_test(negative[1],'blacklist_traits') and
        _type(negative[2],'StateTest')
    ):
        return {'applied':False,'reason':'UNKNOWN_CLASS_TEST_SEMANTICS'},None
    if (name==ZERBU_NAME and
        (len(groups[3])!=1 or
         not _type(groups[3][0],'SituationJobTest') or
         'Zerbu_GTS5_ElementaryStudentBase' not in
         repr(getattr(groups[3][0],'situation_jobs',None)))):
        return {'applied':False,'reason':'UNKNOWN_ELEMENTARY_ROLE_TEST'},None

    # Class1 player requires original positive Class1 trait.
    # Class2 player requires original negative Class1 trait.
    # No known EA test removed except the over-broad original player branch.
    amended=(
        (player[0],positive[0],player[1]),
        positive,
        negative,
        (player[0],negative[1],negative[2]),
    )+groups[3:]
    try:
        new=type(old)(amended)
        snippet.test=new
        if getattr(snippet,'test',None) is not new:
            raise RuntimeError('WRITE_NOT_CONFIRMED')
    except Exception as exc:
        try:snippet.test=old
        except Exception:pass
        return {'applied':False,
                'reason':'WRITE_'+type(exc).__name__},None

    def restore():
        if getattr(snippet,'test',None) is new:
            snippet.test=old
            return True
        return False

    return {
        'applied':True,
        'reason':'EA_AND_ZERBU_PLAYABLE_CLASS_RULES',
        'variant':'ZERBU' if name==ZERBU_NAME else 'EA_ORIGINAL',
        'before':len(groups),'after':len(new),
        'npc_branch_unchanged':new[2] is negative,
        'elementary_branch_unchanged':(
            name!=ZERBU_NAME or new[-1] is groups[-1]),
        'class1_trait_synced_separately':True,
        'seat_arrival_at_10_not_yet_proven':True
    },restore
