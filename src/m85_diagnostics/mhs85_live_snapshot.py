"""M85 read-only scan of already-instantiated Sims and their EA situations."""
from mhs85_reconcile import summarize

def snapshot(manifest, infos, manager, teen_age, human_species, guid_getter):
    groups=manifest.class_ids
    visible=[]
    roles={}
    get_situations=getattr(manager,'get_situations_sim_is_in',None)
    if not callable(get_situations):
        return {'status':'EA situation query unavailable'}
    for info in infos:
        try:
            if info.age!=teen_age or info.species!=human_species:
                continue
            sim=info.get_sim_instance()
            if sim is None:
                continue
            sid=str(info.sim_id)
            visible.append(sid)
            roles[sid]=tuple(g for g in
                             (guid_getter(s) for s in tuple(get_situations(sim) or ()))
                             if g is not None)
        except Exception:
            continue
    result=summarize(groups,visible,roles)
    result['status']='observed'
    return result
