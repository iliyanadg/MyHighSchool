"""M103 strictly read-only deep inspection of one original EA Bouncer request.

M102 verified that Bouncer._unfulfilled_requests is a list containing 40
*lists*, not 40 unfulfilled student requests. This probe counts buckets,
safely unwraps bounded priority-heap entries, and looks specifically for
the MHS selected Sim ID and original EA situation ID. NO mutation, no
filter query, no spawning, no calling bouncer generators or methods.
Missing/unknown data is NOT evidence of rejection by EA.
"""
from mhs102_bouncer_observer import bouncer_probe

_CONTAINER_NAMES=('_unfulfilled_requests','_fulfilled_requests',
                  '_reserved_sims','_sim_to_bouncer_sim_data',
                  '_situation_to_bouncer_situation_data')
_SIM_ATTRS=('sim_id','_sim_id','requested_sim_id','_requested_sim_id',
            'sim_info','_sim_info','sim','_sim','requested_sim_info')
_SITUATION_ATTRS=('situation','_situation','situation_id',
                  '_situation_id','situation_type')
_DETAILS=('status','_status','request_status','_request_status',
          'priority','_priority','request_priority','_request_priority',
          'job_type','_job_type','spawn_option','_spawn_option',
          'assigned_sim','_assigned_sim','_sim_filter')

def _view(value):
    if value is None or type(value) in (int,bool,float):
        return value
    if type(value) is str:
        return value[:64]
    return type(value).__name__

def _attr(value,name):
    try:
        return getattr(value,name,None)
    except Exception:
        return None

def _safe_id(value):
    if type(value) is int and value>0:
        return value
    for field in ('sim_id','id'):
        found=_attr(value,field)
        if type(found) is int and found>0:
            return found
    return None

def _count(value):
    if type(value) in (tuple,list,dict,set,frozenset):
        return len(value)
    return None

def _bounded(value,limit=14):
    """Only snapshots in-memory collections; never exhaust EA iterators."""
    if type(value) is dict:
        return tuple(list(value.items())[:limit])
    if type(value) in (tuple,list):
        return tuple(value[:limit])
    if type(value) in (set,frozenset):
        return tuple(list(value)[:limit])
    return ()

def _peek(request,target_sim,target_situation):
    fields={}
    for name in _SIM_ATTRS:
        sid=_safe_id(_attr(request,name))
        if sid is not None:
            fields[name]=sid
    for name in _SITUATION_ATTRS:
        obj=_attr(request,name)
        sitid=_safe_id(obj)
        if sitid is not None:
            fields[name]=sitid
    details={}
    for name in _DETAILS:
        val=_attr(request,name)
        if val is not None:
            details[name]=_view(val)
    known_sim=any(v==target_sim for k,v in fields.items()
                  if k in _SIM_ATTRS)
    known_situation=any(v==target_situation for k,v in fields.items()
                        if k in _SITUATION_ATTRS)
    return {
        'request_type':type(request).__name__,
        'candidate_attribute_names':tuple(
            x for x in _SIM_ATTRS+_SITUATION_ATTRS+_DETAILS
            if _attr(request,x) is not None)[:20],
        'target_sim_match':known_sim,
        'target_situation_match':known_situation,
        'target_sim_id_fields':{k:v for k,v in fields.items()
                                if k in _SIM_ATTRS and v==target_sim},
        'target_situation_id_fields':{k:v for k,v in fields.items()
                                     if k in _SITUATION_ATTRS and v==target_situation},
        'details':details,
    }

def _request_tree(bouncer,target_sim,target_situation):
    out={'availability':'UNKNOWN',
         'not_proof_of_absence':True,
         'containers':[],
         'matching_requests':[],
         'inspected_request_nodes':0,
         'observed_request_nodes':0}
    if bouncer is None:
        out['availability']='BOUNCER_UNAVAILABLE'
        return out
    for name in _CONTAINER_NAMES:
        value=_attr(bouncer,name)
        if value is None:
            continue
        row={'name':name,'container_type':type(value).__name__,
             'outer_size':_count(value)}
        if name=='_unfulfilled_requests' and type(value) in (list,tuple):
            row['nested_list_sizes']=[len(x) if type(x) in (list,tuple)
                                      else None for x in value[:64]]
            row['nonempty_bucket_count']=sum(1 for x in value[:64]
                                            if type(x) in (list,tuple) and x)
            row['count_of_nested_items']=sum(len(x) for x in value[:64]
                                            if type(x) in (list,tuple))
        seen=0
        seen_types=[]
        to_walk=_bounded(value,64)
        for one in to_walk:
            if seen>=60:
                break
            # EA priority queues may hold inner lists, tuples, or
            # (rank, request) pairs. Inspect bounded levels, not the
            # 40 outer buckets as if they were 40 requests.
            children=(_bounded(one,10) if type(one) in (list,tuple)
                      else (one,))
            for child in children:
                if seen>=60:
                    break
                if type(child) is tuple:
                    seq=_bounded(child,5)
                    objects=tuple(v for v in seq if type(v) not in
                                  (int,float,bool,str,type(None)))
                    candidates=objects or (child,)
                else:
                    candidates=(child,)
                for item in candidates:
                    if seen>=60:
                        break
                    if type(item) in (int,float,bool,str,type(None)):
                        continue
                    seen+=1
                    view=_peek(item,target_sim,target_situation)
                    if view['request_type'] not in seen_types:
                        seen_types.append(view['request_type'])
                    if view['target_sim_match'] or view['target_situation_match']:
                        if len(out['matching_requests'])<12:
                            out['matching_requests'].append(
                                {'container':name,'request':view})
        row['inspected_nodes']=seen
        row['sample_node_types']=seen_types[:8]
        out['inspected_request_nodes']+=seen
        out['containers'].append(row)
    if out['containers']:
        out['availability']='CONTAINERS_OBSERVED'
    return out

def inspect_bouncer(manager,situation_id,target_sim_id):
    """Inspect only one known original situation + registered student."""
    result=bouncer_probe(manager,situation_id)
    result['kind']='M103_BOUNCER_BUCKET_AND_TARGET_REQUEST_READ_ONLY'
    result['target_sim_id']=target_sim_id
    result['deep_request_probe']={'availability':'NOT_CHECKED'}
    try:
        if (result.get('situation_lookup')!='FOUND'
                or type(target_sim_id) is not int or target_sim_id<=0):
            result['deep_request_probe']['availability']='NOT_APPLICABLE'
            return result
        bouncer=_attr(manager,'_bouncer')
        result['deep_request_probe']=_request_tree(
            bouncer,target_sim_id,situation_id)
    except Exception as exc:
        result['deep_request_probe']={
            'availability':'INSPECTION_ERROR',
            'error_type':type(exc).__name__,
            'not_proof_of_absence':True}
    return result
