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
    return install(manager_class,resolve,job_tuning,guest_info_class,purpose,
                   on_applied=session.confirm)
