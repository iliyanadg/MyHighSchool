"""M138 Zerbu GTS5: make player Class 1 / 2 whiteboard tests exclusive.

Live M136 recorded exactly these native EA branches (CompoundTestList):
  [0] SimInfoTest(npc=False), StateTest(Class1)
  [1] TraitTest(whitelist Class1Student), StateTest(Class1)
  [2] SimInfoTest(npc=True), TraitTest(blacklist Class1Student), StateTest(Class2)
  [3] SituationJobTest(Zerbu ElementaryStudentBase)

The [0] branch is why Sandro/Sofia could select Class 1. Replace it
with [0] plus the *existing* class1 whitelist, while adding a
Class2-player branch with the *existing* class1 blacklist and Class2
state. Keep the NPC and Elementary paths byte-for-byte untouched.

Applies only while experimental MHS controller is armed on the test save.
The synced Class1Student trait is the class discriminator; this module
does not assert that it enforces enrollment independently of that trait.
"""

SNIPPET_ID=279071


def _type_is(value,name):
    return type(value).__name__ == name


def _contains_trait(value):
    return 'Class1Student' in repr(value)


def install_exclusive_playable_whiteboard_rules(affordance):
    """Return (status,undo). No mutations unless every expected test matches."""
    if affordance is None:
        return {'applied':False,'reason':'AFFORDANCE_NOT_LOADED'},None
    snippet=None
    for candidate in getattr(affordance,'test_globals',()) or ():
        if getattr(candidate,'guid64',None)==SNIPPET_ID:
            snippet=candidate
            break
    if snippet is None:
        return {'applied':False,'reason':'ZERBU_SNIPPET_NOT_LOADED'},None
    if getattr(snippet,'__name__',None)!='Zerbu_GTS5_WhiteboardStudentTestSnippet':
        return {'applied':False,'reason':'UNRECOGNIZED_SNIPPET_CLASS'},None

    old=getattr(snippet,'test',None)
    if not _type_is(old,'CompoundTestList'):
        return {'applied':False,'reason':'NOT_EXPECTED_COMPOUND_TEST'},None
    groups=tuple(old)
    if len(groups)!=4 or tuple(len(g) for g in groups)!=(2,2,3,1):
        return {'applied':False,'reason':'NOT_EXPECTED_FOUR_BRANCHES'},None
    a,b,c,d=groups
    if not (
        _type_is(a[0],'SimInfoTest')
        and getattr(a[0],'npc',None) is False
        and _type_is(a[1],'StateTest')
        and _type_is(b[0],'TraitTest')
        and _type_is(b[1],'StateTest')
        and _type_is(c[0],'SimInfoTest')
        and getattr(c[0],'npc',None) is True
        and _type_is(c[1],'TraitTest')
        and _type_is(c[2],'StateTest')
        and _type_is(d[0],'SituationJobTest')
        and _contains_trait(b[0])
        and _contains_trait(c[1])
    ):
        return {'applied':False,'reason':'EA_TEST_LAYOUT_MISMATCH'},None

    # Require positive Class1 whitelist and negative Class1 blacklist.
    white=getattr(b[0],'whitelist_traits',None)
    black=getattr(c[1],'blacklist_traits',None)
    if not white or not black:
        return {'applied':False,'reason':'CLASS_TRAIT_POLARITY_UNVERIFIED'},None
    if not all('Class1Student' in repr(x) for x in white):
        return {'applied':False,'reason':'CLASS1_WHITELIST_UNKNOWN'},None
    if not all('Class1Student' in repr(x) for x in black):
        return {'applied':False,'reason':'CLASS2_BLACKLIST_UNKNOWN'},None

    # The original [1], [2], [3] groups are preserved exactly.
    # Group [0] becomes restricted to Class1; new group [3] adds Class2
    # player only. This is still EA native test objects (not custom bypass).
    new_groups=(
        (a[0],b[0],a[1]),
        b,
        c,
        (a[0],c[1],c[2]),
        d,
    )
    try:
        replacement=type(old)(new_groups)
        snippet.test=replacement
        if getattr(snippet,'test',None) is not replacement:
            raise RuntimeError('TUNING_WRITE_NOT_PERSISTED')
    except Exception as exc:
        try:snippet.test=old
        except Exception:pass
        return {'applied':False,
                'reason':'NATIVE_COMPOUND_WRITE_'+type(exc).__name__},None

    def undo():
        if getattr(snippet,'test',None) is replacement:
            snippet.test=old
            return True
        return False

    return {'applied':True,'reason':'PLAYER_CLASS1_ONLY_OR_CLASS2_ONLY',
            'original_branches':4,'new_branches':5,
            'zerbu_elementary_preserved':replacement[-1] is d,
            'npc_class2_preserved':replacement[2] is c,
            'class1_trait_requirement':True},undo
