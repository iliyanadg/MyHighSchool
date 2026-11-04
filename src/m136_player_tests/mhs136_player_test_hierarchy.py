"""M136 limited read-only EA test hierarchy inspection for PLAYABLE students.

Never bypass a test. The native interaction list can be modified by other
installed mods, so record actual loaded types, limited attributes and object
references, without executing any test or modifying native tunings.
"""

RELEVANT_TOKENS=('SituationJob','TestSet','PickWhiteboard','SimInfo',
                 'Trait','Buff','ObjectState','State')
SEQUENCE_ATTRIBUTES=('test_globals','tests','test_set','test_sets','_tests',
                     'test','_test','test_list','_test_list','test_set_reference')
CHECK_ATTRIBUTES=('situation_jobs','situation_job','job','jobs',
                  'whitelist','blacklist','_whitelist','_blacklist',
                  'test_set_reference','sim','who','target','subject',
                  'participant','_situation_jobs')
MAX_DEPTH=5
MAX_NODES=160


def _safe_repr(value):
    try: return repr(value)[:220]
    except Exception: return 'REPR_UNAVAILABLE'


def _guid(value):
    out=getattr(value,'guid64',None)
    return out if type(out) is int else None


def _children(value):
    if value is None:return ()
    if isinstance(value,(list,tuple,set,frozenset)):
        return tuple((str(i),v) for i,v in enumerate(value))[:80]
    if isinstance(value,dict):
        return tuple((str(k),v) for k,v in list(value.items())[:80])
    result=[]
    for name in SEQUENCE_ATTRIBUTES:
        try: v=getattr(value,name,None)
        except Exception:continue
        if v is not None and v is not value and not callable(v):
            result.append((name,v))
    try:
        if type(value).__name__ in ('TestList','CompoundTestList','TestSetInstance'):
            result.extend((str(i),v) for i,v in
                          enumerate(tuple(iter(value))[:80]))
    except Exception:
        pass
    return result[:80]


def inspect_test_hierarchy(affordance,played,boards):
    rows=[]
    pending=[('affordance',affordance,0)]
    seen=set()
    while pending and len(rows)<MAX_NODES:
        path,item,depth=pending.pop(0)
        if item is None or id(item) in seen:continue
        seen.add(id(item))
        t=type(item)
        label=t.__module__+'.'+t.__name__
        row={'path':path,'type':label,'guid64':_guid(item),
             'depth':depth,'repr':_safe_repr(item)}
        if any(word in label or word in path for word in RELEVANT_TOKENS):
            fields={}
            for name in CHECK_ATTRIBUTES:
                try: v=getattr(item,name,None)
                except Exception:continue
                if v is None or callable(v):continue
                fields[name]=_safe_repr(v)
            if fields:row['fields']=fields
        rows.append(row)
        if depth>=MAX_DEPTH:continue
        for name,value in _children(item):
            if isinstance(value,(int,float,str,bool,bytes)):continue
            pending.append((path+'.'+name,value,depth+1))

    return {'kind':'M136_LIVE_PLAYER_WHITEBOARD_TEST_HIERARCHY',
            'playable_ids':[str(row['sim_id']) for row in played],
            'registered_classes':{str(row['sim_id']):row['registered_class']
                                  for row in played},
            'class_board_ids':{str(c):[str(getattr(v,'id',None))
                             for v in boards.get(c,())] for c in (1,2)},
            'nodes':rows,'truncated':bool(pending),
            'no_test_bypassed':True,'no_ea_push':True,
            'game_mutations':0}
