"""M100: select ONE eligible registered teen for ONE ORIGINAL EA Base call.

This is a pure, opt-in precreate selection plan. It MUST NOT start a
separate create_situation: the existing M89 interception handles the
original EA Base situation 277733 with an empty guest list.

Runtime integration has not been released. The caller must obtain
eligible_base_ids from a genuine EA SimFilter 280516 result for THIS
school save/zone/day. DO NOT infer eligibility from teen species/age.
The M99 Baby Ariel experiment proved an explicit guest ID can remain
unspawned for an entire hour despite the situation being active.
"""
BASE=277733
JOB=277894
FILTER=280516

def _ids(raw):
    if not isinstance(raw,(tuple,list,set,frozenset)):
        return None
    result=[]
    for value in raw:
        if type(value) not in (int,str):
            return None
        sid=str(value)
        if not sid.isdigit() or int(sid)<=0 or sid!=str(int(sid)):
            return None
        result.append(sid)
    return tuple(result)

def select_one(original_guid, original_guest_ids, class_ids,
               playable_ids, eligible_base_ids, already_on_zone_ids,
               active_school=False, save_verified=False,
               zone_verified=False, day_verified=False):
    """Return (action, sim_id, reason), with NO situation mutation.

    Candidate must be: in exact 8+8 registry, not an accompanied
    playable, not on lot, in the REAL EA Base SimFilter match set.
    Only the genuine untouched EA empty request may be consumed.
    """
    if original_guid!=BASE:
        return ('bypass',None,'not original EA Base situation')
    if not(active_school and save_verified and zone_verified and day_verified):
        return ('bypass',None,'school/day/save not verified')
    if original_guest_ids is None or tuple(original_guest_ids)!=():
        return ('bypass',None,'EA request not empty; preserve explicit guests')
    if not isinstance(class_ids,(tuple,list)) or len(class_ids)!=2:
        return ('block',None,'two classrooms not verified')
    groups=tuple(_ids(g) for g in class_ids)
    if any(g is None or len(g)!=8 for g in groups):
        return ('block',None,'both groups must have eight distinct IDs')
    cohort=groups[0]+groups[1]
    if len(set(cohort))!=16:
        return ('block',None,'duplicate or invalid enrolled Sim ID')
    playable=_ids(playable_ids)
    eligible=_ids(eligible_base_ids)
    present=_ids(already_on_zone_ids)
    if playable is None or eligible is None or present is None:
        return ('block',None,'live EA eligibility or attendance unknown')
    if not set(playable)<=set(cohort):
        return ('block',None,'unregistered playable teens present')
    verified=set(eligible)
    on_lot=set(present)
    for sid in cohort:
        if sid in verified and sid not in playable and sid not in on_lot:
            return ('choose',int(sid),'one EA-filter-qualified enrolled NPC')
    return ('block',None,'none of the enrolled missing NPCs passed EA Base filter')

class OneSlotPilot(object):
    """Daily at-most-one plan, no retry after the EA callback fails."""
    def __init__(self):
        self.key=None
        self.attempted=False
        self.accepted=False
        self.sim_id=None

    def resolve(self, session_key, original_guid, original_guest_ids, **data):
        if (not isinstance(session_key,tuple) or len(session_key)!=3
                or any(x is None for x in session_key)):
            return ('block',None,'missing save/zone/day identity')
        if self.key!=session_key:
            self.key=session_key
            self.attempted=False
            self.accepted=False
            self.sim_id=None
        if self.attempted:
            return ('bypass',None,'pilot already attempted this school day')
        action,sid,reason=select_one(original_guid,original_guest_ids,**data)
        if action=='choose':
            self.attempted=True
            self.sim_id=sid
        return (action,sid,reason)

    def confirm(self,sim_id):
        if self.attempted and self.sim_id==sim_id and not self.accepted:
            self.accepted=True
            return True
        return False
