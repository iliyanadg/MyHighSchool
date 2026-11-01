"""M96 experimental, opt-in deterministic EA Base student *COUNT* hook.

Evidence: actual EA weekly_schedule_zone_director.py:
WeeklyScheduleDay.get_long_term_situation_count(cls,data,resolver) -> (lo,hi).
The stock random number of Base situations causes roster shortfalls.

This adapter is NOT installed by released M94, DOES NOT spawn students and
DOES NOT modify EA situation jobs, other calendars, or the game save.
Live runtime must provide an atomically verified M92 full-cohort plan and
school/save/day/zone/eligibility checks BEFORE enabling this hook.
"""
SCHEDULE_GUIDS=frozenset((277657,279958))  # High School Main/FromVenue
BASE_SITUATION=277733
MAX_STUDENTS=16

def approved_base_count(schedule_guid, situation_guid, plan):
    """Return exact (min,max) or None if not provably safe to override EA.

    M92 already accounts for the active playable students and live core job
    members. Never subtract playable twice (EA vanilla does this itself).
    """
    if type(schedule_guid) is not int or schedule_guid not in SCHEDULE_GUIDS:
        return None
    if type(situation_guid) is not int or situation_guid!=BASE_SITUATION:
        return None
    if not isinstance(plan,dict):
        return None
    if plan.get('status')!='READY_FOR_ADAPTER' or plan.get('core_jobs_verified') is not True:
        return None
    # The EA CoreClassNPCs situation can be created AFTER the Base count
    # is computed. Reading currently active core occupants alone is not
    # enough: role reservations must be locked BEFORE EA's first invitation.
    # This token can only be set by a future early core reservation engine;
    # M94 cannot supply it and this adapter remains safely uninstalled.
    if plan.get('core_roles_reserved_before_ea') is not True:
        return None
    groups=plan.get('classes')
    if (not isinstance(groups,(tuple,list)) or len(groups)!=2 or
            any(not isinstance(g,(tuple,list)) or len(g)!=8 for g in groups)):
        return None
    members=tuple(str(x) for group in groups for x in group)
    expected=tuple(str(x) for x in plan.get('all_16',()))
    if members!=expected or len(set(expected))!=MAX_STUDENTS:
        return None
    playable=tuple(str(x) for x in plan.get('playable',()))
    core=tuple(str(x) for x in plan.get('core',()))
    normal=tuple(str(x) for x in plan.get('normal_npcs',()))
    if (any(len(g)!=len(set(g)) for g in (playable,core,normal))
            or set(playable)&set(core)
            or set(playable)&set(normal)
            or set(core)&set(normal)
            or set(playable+core+normal)!=set(expected)
            or len(playable)+len(core)+len(normal)!=MAX_STUDENTS):
        return None
    needed=plan.get('base_invites_needed')
    if type(needed) is not int or needed!=len(normal) or not 0<=needed<=MAX_STUDENTS:
        return None
    return (needed,needed)

def install(schedule_class, verified_plan_provider):
    """Patch *only* this classmethod on EA's WeeklyScheduleDay parent.

    verified_plan_provider(tuned_schedule_cls,long_term_data,resolver)
      -> full M92 plan, or None.
    Provider must NEVER infer today's core occupations from Tuning metadata.
    It must enforce school venue, active save, exact live roster, full sim
    eligibility and lot-capacity before returning a plan.

    Preserve EA unmodified if the provider is absent/raises/returns invalid.
    """
    if not callable(verified_plan_provider):
        return False
    owner=None
    for cls in getattr(schedule_class,'__mro__',(schedule_class,)):
        descriptor=cls.__dict__.get('get_long_term_situation_count')
        if isinstance(descriptor,classmethod):
            owner=cls
            break
    if owner is None:
        return False
    previous=owner.__dict__['get_long_term_situation_count'].__func__
    if getattr(previous,'_mhs96_count_hook',False):
        return False

    def wrapped(cls,data,resolver):
        # We never call original twice, and none of the original outcomes
        # for unrelated situations or schools are changed.
        original=previous(cls,data,resolver)
        try:
            sid=getattr(cls,'guid64',None)
            situation=getattr(data,'situation',None)
            gid=getattr(situation,'guid64',None)
            if type(sid) is not int or type(gid) is not int:
                return original
            if sid not in SCHEDULE_GUIDS or gid!=BASE_SITUATION:
                return original
            plan=verified_plan_provider(cls,data,resolver)
            exact=approved_base_count(sid,gid,plan)
            return original if exact is None else exact
        except Exception:
            return original
    wrapped._mhs96_count_hook=True
    setattr(owner,'get_long_term_situation_count',classmethod(wrapped))
    return True
