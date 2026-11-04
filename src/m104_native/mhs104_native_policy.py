"""M104: pure native EA Base Student SimFilter single-request constrainer.

Unlike M61-M102 this NEVER touches a SituationGuestList or creates any
situation. It constrains ONE native EA Bouncer submit_matching_filter
request, leaving EA's entire invitation and spawn machinery intact.
Source observations: filter GUID 280516, native wrapper M57 currently
ISOLATION_DISABLED, 13 registered NPCs with 12 valid results from M101d.

Not a claim of full 16/24 attendance. Fail closed on unexpected input.
"""
BASE_FILTER=280516

def _id(value):
    if type(value) not in (str,int) or not str(value).isdigit():
        return None
    val=int(value)
    return val if val>0 else None

def eligible_npcs(classes,playable,already_on_lot):
    """Two exact 8-member classes, exclude accompanied playable and on-lot."""
    if type(classes) not in (tuple,list) or len(classes)!=2:
        return None
    groups=[]
    for group in classes:
        if type(group) not in (tuple,list) or len(group)!=8:
            return None
        parsed=tuple(_id(x) for x in group)
        if None in parsed:
            return None
        groups.extend(parsed)
    if len(set(groups))!=16:
        return None
    if type(playable) not in (tuple,list,set,frozenset):
        return None
    if type(already_on_lot) not in (tuple,list,set,frozenset):
        return None
    played={_id(x) for x in playable}
    loaded={_id(x) for x in already_on_lot}
    if None in played or None in loaded or not played<=set(groups):
        return None
    return tuple(x for x in groups if x not in played and x not in loaded)

def native_base_arguments(mode,args,kwargs,tuning_guid,npc_ids):
    """Return new args/kwargs with exact native filter, or preserve original.

    Important signature detail: EA submit_matching_filter is
      (number_of_sims_to_find, sim_filter, callback=..., callback_event_data,
       sim_constraints, ...).
    M57's old submit_filter positional filter index 0 is INCORRECT:
    its first position is the required callback; do not reuse that index.
    This pilot handles matching only, not staff/club filters.
    """
    if mode!='matching' or tuning_guid!=BASE_FILTER:
        return ('preserve',tuple(args),dict(kwargs),'not native Base matching')
    if npc_ids is None or not isinstance(npc_ids,(tuple,list)):
        return ('block',tuple(args),dict(kwargs),'cohort not verified')
    requested=tuple(_id(x) for x in npc_ids)
    if not requested or None in requested or len(set(requested))!=len(requested):
        return ('block',tuple(args),dict(kwargs),'no eligible registered NPC')
    values=list(args)
    options=dict(kwargs)
    # EA positional index four is the explicit Sim constraint list. Never
    # replace a caller's own explicit target with one from the MHS roster.
    original=(options['sim_constraints'] if 'sim_constraints' in options
              else values[4] if len(values)>4 else None)
    if original is not None:
        return ('preserve',tuple(args),dict(kwargs),'explicit native EA targets')
    if len(values)>4:
        values[4]=requested
    else:
        options['sim_constraints']=requested
    # Stop the matching filter from choosing random Sims if none qualify.
    for key,index in (('continue_if_constraints_fail',8),
                      ('conform_if_constraints_fail',9)):
        if len(values)>index:
            values[index]=False
        else:
            options[key]=False
    return ('constrain',tuple(values),options,'native EA Bouncer chooses from registered NPCs')
