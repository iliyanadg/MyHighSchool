"""M90/M89 bridge: roster selection for existing EA student requests.

NOT auto-installed. Runtime must pass verified eligibility and school checks.
Never creates situations, spawns Sims, or changes EA school capacity.
"""
from mhs89_precreate_hook import install

def connect(manager_class, session, eligibility_provider, zone_checker,
            job_tuning, guest_info_class, purpose):
    """Attach a session to M89. Provider returns (eligible IDs, on-lot IDs).

    Caller must verify school/save/day and eligibility in the current game.
    """
    if not callable(eligibility_provider) or not callable(zone_checker):
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
