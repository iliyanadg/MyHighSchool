"""M90/M89 bridge: roster selection for existing EA student requests.

NOT auto-installed. Runtime must pass verified eligibility and school checks.
Never creates situations, spawns Sims, or changes EA school capacity.
"""
from mhs89_precreate_hook import install

def connect(manager_class, session, eligibility_provider, zone_checker,
            job_tuning, guest_info_class, purpose, full_plan=None):
    """Attach a session to M89. Provider returns (eligible IDs, on-lot IDs).

    Caller must verify school/save/day and eligibility in the current game.
    """
    if not callable(eligibility_provider) or not callable(zone_checker):
        return False
    # Never enable selection for a partial day or unverified EA capacities.
    if not isinstance(full_plan,dict) or full_plan.get('status')!='READY_FOR_ADAPTER':
        return False
    if full_plan.get('core_jobs_verified') is not True:
        # EA core jobs 278965/6/7/8, 303765 can spawn additional pupils.
        # Never activate with merely assumed core member headcounts.
        return False
    base_count=full_plan.get('base_invites_needed')
    playable=set(str(x) for x in full_plan.get('playable',()))
    core=set(str(x) for x in full_plan.get('core',()))
    if type(base_count) is not int or base_count<0:
        return False
    if len(playable)+len(core)+base_count!=16 or playable & core:
        return False
    if set(session.playable)!=playable or set(session.excluded)!=core:
        return False
    classes=full_plan.get('classes',())
    if len(classes)!=2 or any(len(group)!=8 for group in classes):
        return False
    expected=tuple(str(x) for x in full_plan.get('all_16',()))
    if len(expected)!=16 or len(set(expected))!=16:
        return False
    if tuple(session.roster)!=expected:
        return False
    def resolve(manager,situation,guests):
        if not zone_checker():
            return None
        eligible,present=eligibility_provider()
        sid=session.choose(eligible,present)
        if sid is None:
            return None
        return (sid,True,True)
    def refuse_unassigned_fallback(manager,situation,guests):
        # All EA Base requests for this VERIFIED active plan must use one
        # eligible enrolled Sim or create no situation. Never generate an
        # extra random classmate if all Base invitations were used, or if
        # a registered Sim is ineligible that day.
        try:
            return zone_checker() is True
        except Exception:
            return False
    return install(manager_class,resolve,job_tuning,guest_info_class,purpose,
                   on_applied=session.confirm,
                   on_exhausted=refuse_unassigned_fallback)
