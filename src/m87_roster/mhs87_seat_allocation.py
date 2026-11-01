"""M87: deterministic school-seat allocation plan; no game hooks or mutations.

The current EA roster is mostly random (3/16 registered in roles at 10:09).
This maps the exact registered non-playable teens to *verified* available
EA base jobs without creating new student situations or claiming attendance.
"""
def _ids(items):
    if items is None:
        return None
    try:
        vals=tuple(str(s) for s in items)
    except TypeError:
        return None
    if any(not s.isdigit() or int(s)<1 or str(int(s))!=s for s in vals):
        return None
    if len(vals)!=len(set(vals)):
        return None
    return vals

def allocate(class1, class2, playable, core_role_members, ea_eligible,
             base_slot_count):
    """Return a fail-closed capacity plan, never a live invitation.

    Core and playable registered teens consume classroom seats, not new
    Base Student job invitations. Base seat capacity must be verified against
    currently installed EA tuning and active day before calling.
    """
    a=_ids(class1)
    b=_ids(class2)
    play=_ids(playable)
    core=_ids(core_role_members)
    eligible=_ids(ea_eligible)
    if any(x is None for x in (a,b,play,core,eligible)):
        return {'status':'BLOCKED','reason':'invalid Sim IDs'}
    if len(a)!=8 or len(b)!=8 or len(set(a+b))!=16:
        return {'status':'BLOCKED','reason':'requires 8+8 distinct enrolled teens'}
    enrolled=a+b
    if set(core).difference(enrolled) or set(core).intersection(play):
        return {'status':'BLOCKED','reason':'core role conflict'}
    required=tuple(s for s in enrolled if s not in play and s not in core)
    if not set(required).issubset(eligible):
        return {'status':'BLOCKED','reason':'EA base filter eligibility not verified',
                'required_base_npcs':len(required)}
    if type(base_slot_count) is not int or base_slot_count<0:
        return {'status':'BLOCKED','reason':'base situation capacity not verified'}
    if base_slot_count<len(required):
        return {'status':'BLOCKED','reason':'insufficient base school jobs',
                'required_base_npcs':len(required),
                'verified_base_slots':base_slot_count}
    return {'status':'PLAN_ONLY','required_base_npcs':len(required),
            'verified_base_slots':base_slot_count,
            'base_job_candidates':required,
            'classes':(a,b),'changes_to_ea':False}
