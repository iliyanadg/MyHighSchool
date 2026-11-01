"""M88: prepare a replacement *within* one existing EA school situation.

Experimental, not installed by any released build. No new situations are made.
Only an unassigned Base Student job in the EA guest list can be replaced.
The caller supplies a roster student verified as eligible for EA's Base job.
"""
from mhs58_guest_policy import guest_list_decision

def replace_unassigned_guest(situation_guid, guest_list, student_id, job_tuning,
                             guest_info_cls, purpose,
                             verified_school_zone=False, active=False):
    """Return new guest list *only* if the old one was a single EA vacancy.

    Works on a clone, never changes an EA provided guest list in place.
    Return None to preserve EA unchanged if any assumption cannot be checked.
    """
    try:
        old=tuple(guest_list.guest_info_gen())
        jobs=tuple((getattr(getattr(g,'job_type',None),'guid64',None),
                    getattr(g,'sim_id',None)) for g in old)
        verdict=guest_list_decision(situation_guid,jobs,[str(student_id)],
                                    verified_school_zone,active)
        if verdict.get('action')!='candidate':
            return None
        if getattr(job_tuning,'guid64',None)!=277894:
            return None
        if not callable(getattr(guest_list,'clone',None)):
            return None
        replacement=guest_list.clone()
        if replacement is guest_list:
            return None
        # Do not assume clone supports removal; require it and verify result.
        remove=getattr(replacement,'remove_guest_info',None)
        add=getattr(replacement,'add_guest_info',None)
        if not callable(remove) or not callable(add):
            return None
        copied=tuple(replacement.guest_info_gen())
        if len(copied)!=1 or getattr(copied[0],'sim_id',None) not in (0,None):
            return None
        remove(copied[0])
        info=guest_info_cls.construct_from_purpose(int(student_id),job_tuning,purpose)
        add(info)
        result=tuple(replacement.guest_info_gen())
        if len(result)!=1 or int(getattr(result[0],'sim_id',0))!=int(student_id):
            return None
        return replacement
    except Exception:
        return None
