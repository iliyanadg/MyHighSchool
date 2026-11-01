"""M88: prepare a replacement *within* one existing EA school situation.

Experimental, not installed by any released build. No new situations are made.
Only a verified unassigned or EA-generated Base Student slot can be replaced.
The caller supplies a roster student verified as eligible for EA's Base job.
"""
from mhs58_guest_policy import guest_list_decision

def replace_unassigned_guest(situation_guid, guest_list, student_id, job_tuning,
                             guest_info_cls, purpose,
                             verified_school_zone=False, active=False,
                             ea_generated_explicit=False, registered_ids=()):
    """Return new guest list *only* if the old one was a single EA vacancy.

    Works on a clone, never changes an EA provided guest list in place.
    Return None to preserve EA unchanged if any assumption cannot be checked.
    """
    try:
        old=tuple(guest_list.guest_info_gen())
        jobs=tuple((getattr(getattr(g,'job_type',None),'guid64',None),
                    getattr(g,'sim_id',None)) for g in old)
        if not active or not verified_school_zone or int(situation_guid)!=277733:
            return None
        if len(old)!=1 or jobs[0][0]!=277894:
            return None
        original_id=jobs[0][1]
        if original_id not in (0,None):
            # Explicit EA random invites can be replaced only with opt-in
            # proof; enrolled and unrelated explicit guests remain untouched.
            if not ea_generated_explicit:
                return None
            if str(original_id) in set(str(x) for x in registered_ids):
                return None
        else:
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
        if len(copied)!=1 or getattr(copied[0],'sim_id',None)!=original_id:
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
