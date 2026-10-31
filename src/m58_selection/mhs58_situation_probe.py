"""M58 read-only school situation creation probe (not activated by builds).

Uses EA SituationManager.create_situation as the observation point. A wrapper
installed in the actual game must be separately validated on the installed
game version before shipping. No guest mutations, spawning or new situations.
"""
BASE_GUIDS={277733:'students',298052:'core',298096:'venue',278011:'cafeteria'}
COUNTS={}
LAST_ERROR='none'
INSTALLED=False


def tuning_guid(obj):
    value=getattr(obj,'guid64',None)
    try:
        return int(value)
    except (TypeError,ValueError):
        return None


def describe_request(situation_type, guest_list=None):
    guid=tuning_guid(situation_type)
    if guid not in BASE_GUIDS:
        return None
    jobs={}
    explicit=0
    unknown=0
    if guest_list is not None:
        for item in guest_list.guest_info_gen():
            job=tuning_guid(getattr(item,'job_type',None))
            sid=getattr(item,'sim_id',0)
            jobs[job]=jobs.get(job,0)+1
            if sid:
                explicit+=1
            else:
                unknown+=1
    return {'situation':guid,'kind':BASE_GUIDS[guid],
            'jobs':jobs,'explicit':explicit,'unassigned':unknown}


def install_probe(manager_class):
    """Install once, preserving signature/call result; no EA imports.

    Installation intentionally NOT called automatically; production
    integration requires version and zone validation first.
    """
    global INSTALLED,LAST_ERROR
    if INSTALLED:
        return True
    previous=getattr(manager_class,'create_situation',None)
    if not callable(previous):
        LAST_ERROR='create_situation missing'
        return False
    if getattr(previous,'_mhs58_readonly_probe',False):
        INSTALLED=True
        return True

    def wrapper(self,situation_type,*args,**kwargs):
        global LAST_ERROR
        try:
            guest_list=kwargs.get('guest_list',args[0] if args else None)
            record=describe_request(situation_type,guest_list)
            if record is not None:
                guid=record['situation']
                old=COUNTS.get(guid,{'calls':0,'explicit':0,'unassigned':0,'jobs':{}})
                old['calls']+=1
                old['explicit']+=record['explicit']
                old['unassigned']+=record['unassigned']
                for job,count in record['jobs'].items():
                    old['jobs'][job]=old['jobs'].get(job,0)+count
                COUNTS[guid]=old
        except Exception as exc:
            LAST_ERROR=type(exc).__name__
        return previous(self,situation_type,*args,**kwargs)
    wrapper._mhs58_readonly_probe=True
    try:
        setattr(manager_class,'create_situation',wrapper)
        INSTALLED=True
        return True
    except Exception as exc:
        LAST_ERROR=type(exc).__name__
        return False


def status():
    return {'installed':INSTALLED,'counts':{
        key:{'calls':value['calls'],'explicit':value['explicit'],
             'unassigned':value['unassigned'],'jobs':dict(value['jobs'])}
        for key,value in COUNTS.items()},'error':LAST_ERROR}
