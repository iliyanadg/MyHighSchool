"""M89: opt-in pre-create school selection adapter (not in installed M85).

Wrap only EA's existing create_situation request. Never create an extra situation.
Activation requires a caller-supplied, verified save/zone roster resolver.
No changes to EA core situations, staff, or already explicit invitations.
"""
from mhs88_replace_guest import replace_unassigned_guest

BASE=277733

def install(manager_class, resolver, job_tuning, guest_info_class, purpose, on_applied=None):
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
        except Exception:
            new_list=None
        if new_list is None:
            return previous(self,situation_type,*args,**kwargs)
        if 'guest_list' in kwargs:
            copied=dict(kwargs)
            copied['guest_list']=new_list
            result=previous(self,situation_type,*args,**copied)
        elif args:
            result=previous(self,situation_type,new_list,*args[1:],**kwargs)
        else:
            return previous(self,situation_type,*args,**kwargs)
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
