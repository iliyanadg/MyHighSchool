"""M91 EA school roster resolver — a runtime bridge for the M89/M90 prototype.

NOT enabled by the M85 diagnostic build. The runtime entrypoint must verify
school/save identity, call connect once per zone+school day BEFORE EA creates
the Base Student situations, and explicitly opt in on a test save.
"""
def verified_candidates(manifest, all_sim_infos, teen_age, human_species):
    """Return actual EA-eligible teen IDs and instantiated IDs, read-only.

    This is preliminary: EA's career/blacklist SimFilter is stricter than
    age/species, so callers MUST additionally verify the real EA filter before
    enabling a live selection. No IDs outside the registered roster escape.
    """
    registered=set(manifest.all_student_ids)
    playable=set(manifest.active_household_teens)
    eligible=[]
    present=[]
    for info in all_sim_infos:
        try:
            sid=str(info.sim_id)
            if sid not in registered:
                continue
            if info.get_sim_instance() is not None:
                present.append(sid)
            if sid in playable:
                continue
            if info.age!=teen_age or info.species!=human_species:
                continue
            eligible.append(sid)
        except (AttributeError,TypeError,ValueError):
            continue
    return tuple(eligible),tuple(present)


def can_use_school_roster(manifest, ea_filter_verified, save_verified,
                          school_zone_verified, capacity_verified):
    """Never install a mutating hook unless ALL independent gates pass."""
    if manifest is None or not ea_filter_verified or not save_verified:
        return False
    if not school_zone_verified or not capacity_verified:
        return False
    if len(manifest.class_ids)!=2:
        return False
    if any(len(group)!=8 for group in manifest.class_ids):
        return False
    return len(manifest.all_student_ids)==16
