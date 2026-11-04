"""M102 read-only probe: situation requests and manager/Bouncer metadata.

The M101d game report established that EA accepted the original
school situation guest Rahul Chopra, but did not instantiate him.
A guest-list ID alone is not proof that the bouncer allocated a sim.
This tool INSPECTS only: no callbacks, spawning, forcing requests, or
modifications of EA situation data. Missing private EA attributes are
reported as UNKNOWN, not as an absence of requests.
"""
MATCH=('bouncer','request','spawn','guest','job','assignment','sim')
CONTAINERS=('_bouncer_requests','_requests','_all_requests',
            '_unfulfilled_requests','_pending_requests',
            '_active_requests','_job_requests','_jobs',
            '_guest_list','_bouncer')
REQUEST_FIELDS=('sim_id','_sim_id','request_priority','_request_priority',
                'status','_status','request_status','_request_status',
                'job_type','_job_type','requested_sim_id',
                'sim_filter','_sim_filter','assigned_sim','_assigned_sim',
                'spawn_option','_spawn_option','priority','_priority')

def _safe(value):
    if value is None or type(value) in (int,bool,float):
        return value
    if isinstance(value,str):
        return value[:96]
    return type(value).__name__

def _names(obj):
    if obj is None:
        return []
    try:
        return [key for key in sorted(dir(obj))
                if not key.startswith('__') and
                any(term in key.lower() for term in MATCH)][:40]
    except Exception:
        return []

def _size(value):
    if type(value) in (tuple,list,dict,set,frozenset):
        return len(value)
    return None

def _requests(obj):
    """Inspect known attribute names only; never run EA request methods."""
    if obj is None:
        return {'availability':'OBJECT_UNAVAILABLE'}
    result={'availability':'UNKNOWN','candidate_attribute_names':_names(obj),
            'found_containers':[]}
    for name in CONTAINERS:
        try:
            val=getattr(obj,name,None)
        except Exception:
            continue
        if val is None:
            continue
        entry={'attribute':name,'type':type(val).__name__,'size':_size(val)}
        if name=='_guest_list':
            guests=getattr(val,'guest_info_gen',None)
            if callable(guests):
                try:
                    entries=tuple(guests())
                    entry['size']=len(entries)
                    entry['guest_sim_ids']=[
                        getattr(g,'sim_id',None)
                        for g in entries[:12] if type(getattr(g,'sim_id',None)) is int]
                except Exception:
                    entry['guest_sim_ids']='UNAVAILABLE'
        if name!='_bouncer' and type(val) in (list,tuple,dict,set,frozenset):
            values=list(val.values()) if isinstance(val,dict) else list(val)
            items=[]
            for request in values[:6]:
                fields={}
                for field in REQUEST_FIELDS:
                    try:
                        value=getattr(request,field)
                    except Exception:
                        continue
                    fields[field]=_safe(value)
                items.append({'type':type(request).__name__,'fields':fields})
            entry['sample_requests']=items
        result['found_containers'].append(entry)
    if result['found_containers']:
        result['availability']='ATTRIBUTES_OBSERVED'
    return result

def bouncer_probe(manager,situation_id):
    """Pure inspection, bound to the already existing EA situation ID."""
    report={'kind':'M102_READ_ONLY_BOUNCER_INSPECTION',
            'created_situation_id':situation_id,
            'situation_lookup':'NOT_CHECKED',
            'manager_requests':{},
            'situation_requests':{},
            'bouncer_requests':{},
            'bouncer_owner':'UNKNOWN',
            'does_not_prove_bouncer_assignment':True}
    if type(situation_id) is not int or situation_id<=0:
        report['situation_lookup']='INVALID_ID'
        return report
    try:
        getter=getattr(manager,'get',None)
        if not callable(getter):
            report['situation_lookup']='LOOKUP_UNAVAILABLE'
            return report
        situation=getter(situation_id)
        report['situation_lookup']='FOUND' if situation is not None else 'NOT_FOUND'
        if situation is None:
            return report
        report['manager_requests']=_requests(manager)
        report['situation_requests']=_requests(situation)
        bouncer=getattr(manager,'_bouncer',None)
        if bouncer is None:
            bouncer=getattr(situation,'_bouncer',None)
            if bouncer is not None:
                report['bouncer_owner']='SITUATION'
        else:
            report['bouncer_owner']='MANAGER'
        report['bouncer_requests']=_requests(bouncer)
        return report
    except Exception as exc:
        report['inspection_error']=type(exc).__name__
        return report
