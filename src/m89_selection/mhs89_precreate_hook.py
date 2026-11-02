"""M89: opt-in pre-create school selection adapter (not in installed M85).

Wrap only EA's existing create_situation request. Never create an extra situation.
Activation requires a caller-supplied, verified save/zone roster resolver.
No changes to EA core situations, staff, or already explicit invitations.
"""
from mhs88_replace_guest import (replace_unassigned_guest,
    build_guest_for_empty_ea_request)

BASE=277733

def install(manager_class, resolver, job_tuning, guest_info_class, purpose, on_applied=None, on_exhausted=None, context_checker=None, on_created=None):
    """resolver(manager, situation_type, guest_list) -> (student_id, verified_zone, active)

    The resolver MUST validate school zone, save identity, Sim eligibility,
    non-playable status and daily uniqueness. A None result leaves EA unchanged.
    No resolver is provided here: M89 is NOT safe to enable in-game yet.
    """
    previous=getattr(manager_class,'create_situation',None)
    if not callable(previous) or not callable(resolver):
        return False
    if getattr(previous,'_mhs89_hook',False):
        return False

    def wrapper(self,situation_type,*args,**kwargs):
        guid=getattr(situation_type,'guid64',None)
        if guid!=BASE:
            return previous(self,situation_type,*args,**kwargs)
        guest_list=kwargs.get('guest_list', args[0] if args else None)
        if guest_list is None:
            return previous(self,situation_type,*args,**kwargs)
        # M101's optional check requires proof that THIS request came from
        # the EA WeeklyScheduleDay, with all original spin-up flags intact.
        # Existing M89/M90 offline callers do not use this option.
        if callable(context_checker):
            try:
                if context_checker(self,situation_type,guest_list,args,kwargs) is not True:
                    return previous(self,situation_type,*args,**kwargs)
            except Exception:
                return previous(self,situation_type,*args,**kwargs)
        # Candidate preparation may fail; fall back before the EA call only.
        try:
            candidate=resolver(self,situation_type,guest_list)
            new_list=None
            if candidate is not None:
                student_id,verified_zone,active=candidate[:3]
                provenance=candidate[3] if len(candidate)>3 else None
                new_list=replace_unassigned_guest(
                    guid,guest_list,student_id,job_tuning,
                    guest_info_class,purpose,verified_zone,active,
                    ea_generated_explicit=bool(
                        provenance and provenance.get('ea_auto_generated')),
                    registered_ids=provenance.get('registered_ids',())
                    if provenance else ())
                if new_list is None:
                    new_list=build_guest_for_empty_ea_request(
                        guid,guest_list,student_id,job_tuning,
                        guest_info_class,purpose,verified_zone,active)
        except Exception:
            new_list=None
        if new_list is None:
            # A fully allocated, VERIFIED cohort must not fall back to
            # another random EA pupil. Opt-in only: the coordinator must
            # attest that all required Base slots have already succeeded.
            # An unverified or incomplete cohort always preserves vanilla.
            if callable(on_exhausted):
                try:
                    guests=tuple(guest_list.guest_info_gen())
                    auto_unassigned=(not guests or (
                        len(guests)==1
                        and getattr(guests[0],'sim_id',None) in (0,None)
                        and getattr(getattr(guests[0],'job_type',None),
                                    'guid64',None)==277894))
                    if (auto_unassigned and
                            on_exhausted(self,situation_type,guest_list) is True):
                        # EA SituationManager uses a falsy result for no
                        # situation. This returns no new EA situation; it
                        # does NOT create, terminate or delete Sims.
                        return None
                except Exception:
                    pass
            return previous(self,situation_type,*args,**kwargs)
        if 'guest_list' in kwargs:
            copied=dict(kwargs)
            copied['guest_list']=new_list
            result=previous(self,situation_type,*args,**copied)
        elif args:
            result=previous(self,situation_type,new_list,*args[1:],**kwargs)
        else:
            return previous(self,situation_type,*args,**kwargs)
        # A separate opt-in callback may record the actual Situation ID.
        # It cannot modify or retry the EA call.
        if result and callable(on_created):
            try:
                on_created(student_id,result)
            except Exception:
                pass
        # Never call the original EA method twice even if it raises.
        if result and callable(on_applied):
            try:
                on_applied(student_id)
            except Exception:
                pass
        return result
    wrapper._mhs89_hook=True
    manager_class.create_situation=wrapper
    return True
