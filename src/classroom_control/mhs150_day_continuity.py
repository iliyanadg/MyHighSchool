"""M150 school-day identity continuity: external diagnostic, no EA mutations.

A frozen report-time selection can be compared to the previous *distinct*
school day on the same save slot. This proves only identity stability in the
saved registry, never that every Sim arrived or completed lessons.
The single file is separate from the MHS roster and never edits a save.
Python 3.7 compatible.
"""
import json
import os
import tempfile


def _ids(values):
    values=tuple(str(x) for x in values)
    if any(not x.isdigit() or int(x)<1 or str(int(x))!=x
           for x in values) or len(set(values))!=len(values):
        raise ValueError('INVALID_SIM_IDS')
    return list(values)


def snapshot(slot,day_key,classes,staff):
    """Validate read-only selections captured before/during EA school day."""
    slot=str(slot)
    if not slot.isdigit() or int(slot)<1 or str(int(slot))!=slot:
        raise ValueError('INVALID_SAVE_SLOT')
    if (not isinstance(day_key,(tuple,list)) or len(day_key)!=2
            or str(day_key[0])!=slot or type(day_key[1]) is not int
            or day_key[1]<0):
        raise ValueError('INVALID_SCHOOL_DAY_KEY')
    if not isinstance(classes,(tuple,list)) or len(classes)!=2:
        raise ValueError('REQUIRE_TWO_GAMEPLAY_CLASSES')
    normalized=[_ids(group) for group in classes]
    if any(len(group)!=8 for group in normalized) or len(
            set(normalized[0]+normalized[1]))!=16:
        raise ValueError('REQUIRE_EXACT_SIXTEEN_STUDENTS')
    if not isinstance(staff,dict):
        raise ValueError('MISSING_STAFF_SELECTION')
    roles={}
    for role,ids in sorted(staff.items()):
        if not isinstance(role,str) or not isinstance(ids,(tuple,list)):
            raise ValueError('INVALID_STAFF_ROLE')
        roles[role]=_ids(ids)
    return {'schema':1,'save_slot':slot,'sim_day_number':day_key[1],
            'class_1':normalized[0],'class_2':normalized[1],
            'staff_roles':roles,
            'these_are_registered_not_proven_physically_present':True}


def compare(previous,current):
    """Explicitly separate same day from a real following-school-day check."""
    if previous is None:
        return {'status':'FIRST_DAY_BASELINE','compared_distinct_days':False}
    if (previous.get('schema')!=1 or
            previous.get('save_slot')!=current['save_slot'] or
            type(previous.get('sim_day_number')) is not int):
        return {'status':'PRIOR_BASELINE_INVALID','compared_distinct_days':False}
    earlier=previous['sim_day_number']
    now=current['sim_day_number']
    if now==earlier:
        return {'status':'SAME_SCHOOL_DAY','compared_distinct_days':False,
                'sim_day_number':now}
    if now<earlier:
        return {'status':'EARLIER_SAVE_STATE','compared_distinct_days':False,
                'previous_sim_day':earlier,'current_sim_day':now}
    roster_same=(previous.get('class_1')==current['class_1'] and
                 previous.get('class_2')==current['class_2'])
    staff_same=previous.get('staff_roles')==current['staff_roles']
    return {'status':('SAME_SAVED_SELECTIONS_ON_NEXT_SCHOOL_DAY'
                       if roster_same and staff_same else
                       'REGISTRY_OR_PERSONNEL_CHANGED'),
            'compared_distinct_days':True,
            'previous_sim_day':earlier,'current_sim_day':now,
            'identical_class_1_ids':previous.get('class_1')==current['class_1'],
            'identical_class_2_ids':previous.get('class_2')==current['class_2'],
            'identical_selected_staff':staff_same,
            'registered_not_proof_of_actual_ea_spawn_or_roles':True}


def record(folder,current):
    """Read and atomically update a tiny per-slot baseline, never game data."""
    slot=current['save_slot']
    path=os.path.join(folder,'MHS_M150_GIORNI_SLOT_{}.json'.format(slot))
    previous=None
    if os.path.lexists(path):
        if os.path.islink(path) or not os.path.isfile(path):
            return {'status':'BASELINE_PATH_NOT_REGULAR',
                    'compared_distinct_days':False}
        try:
            with open(path,'r',encoding='utf-8') as stream:
                previous=json.load(stream)
        except (OSError,ValueError,TypeError,UnicodeError):
            return {'status':'PRIOR_BASELINE_UNREADABLE',
                    'compared_distinct_days':False}
    verdict=compare(previous,current)
    verdict['baseline_file_is_not_school_registry']=True
    verdict['world_mutations']=0
    if verdict['status'] in ('FIRST_DAY_BASELINE','SAME_SCHOOL_DAY',
                            'SAME_SAVED_SELECTIONS_ON_NEXT_SCHOOL_DAY',
                            'REGISTRY_OR_PERSONNEL_CHANGED'):
        # Same-day reports must not overwrite the first frozen selection.
        if verdict['status']=='SAME_SCHOOL_DAY':
            return verdict
        try:
            if not os.path.isdir(folder):
                os.makedirs(folder)
            fd,stage=tempfile.mkstemp(dir=folder,prefix='.mhs150_',suffix='.tmp')
            try:
                with os.fdopen(fd,'w',encoding='utf-8') as stream:
                    json.dump(current,stream,sort_keys=True,indent=2)
                    stream.flush()
                    os.fsync(stream.fileno())
                os.replace(stage,path)
            finally:
                if os.path.exists(stage):
                    os.unlink(stage)
        except (OSError,UnicodeError,TypeError,ValueError):
            verdict['baseline_update']='WRITE_FAILED'
        else:
            verdict['baseline_update']='WRITTEN'
    return verdict
