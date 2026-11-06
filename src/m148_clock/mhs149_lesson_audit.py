"""M149: read-only lesson and clock evidence summary for one school day.

This module does not patch EA, submit actions, move Sims or infer grades.
It distinguishes instanced Sims and running EA Attend interactions from
completion of a lesson (for which this report has no authoritative event).
Pure Python 3.7; also usable on an exported MHS JSON report.
"""

def _entry_period(sample):
    period=sample.get('period')
    return period if period in ('morning','afternoon') else None


def _positive_running_lesson(action):
    return (isinstance(action,str) and
            ('super_HighSchool_Active_AttendClass_NPC' in action or
             'super_HighSchool_Active_Whiteboard_Attend_' in action))


def _median(values):
    if not values:
        return None
    sorted_values=sorted(values)
    halfway=len(sorted_values)//2
    if len(sorted_values)%2:
        return round(sorted_values[halfway],2)
    return round((sorted_values[halfway-1]+sorted_values[halfway])/2.0,2)


def audit_lesson_entry(entries,classes):
    """Return observed presence/lesson evidence without making gameplay claims.

    Groups are roster Sim IDs; compare against actual sample rows. No sample
    means UNKNOWN, not zero attendance. Records cover only entry windows.
    """
    groups=tuple(tuple(str(sid) for sid in group) for group in classes)
    desired={str(sid):klass for klass,group in enumerate(groups,1)
             for sid in group}
    result={'kind':'M149_READ_ONLY_LESSON_AND_CLOCK_AUDIT',
            'sampling_scope':'EA_09_30_10_30_AND_13_30_14_30_SIM_TIME',
            'sample_count':0,
            'periods':{},
            'clock_lag_minutes':{'observed_samples':0,'minimum':None,
                                 'median':None,'maximum':None},
            'all_registered_present_in_every_sample':None,
            'all_registered_have_running_lesson_evidence':None,
            'lesson_completion':'NOT_VERIFIED_BY_ENTRY_ACTIONS',
            'does_not_prove_completed_lesson_or_grade':True,
            'lag_not_attributed_to_this_mod':True,
            'student_or_staff_mutations':0}
    lags=[]
    overall_presence=[]
    seen_actions=set()
    for phase in ('morning','afternoon'):
        samples=[row for row in entries if isinstance(row,dict)
                 and _entry_period(row)==phase]
        classes_result={}
        for klass,ids in enumerate(groups,1):
            if not samples:
                classes_result[str(klass)]={
                    'registered':len(ids),'minimum_instanced':None,
                    'maximum_instanced':None,'running_lesson_seen':[],
                    'all_instanced_each_sample':None}
                continue
            counts=[]
            for sample in samples:
                students={str(st.get('sim_id')):st
                          for st in sample.get('students',())
                          if isinstance(st,dict)}
                counts.append(sum(
                    students.get(sid,{}).get('sim_present') is True
                    and students.get(sid,{}).get('registered_class')==klass
                    for sid in ids))
            seen=set()
            for sample in samples:
                for item in sample.get('students',()):
                    if not isinstance(item,dict):
                        continue
                    sid=str(item.get('sim_id'))
                    if (sid in ids and item.get('registered_class')==klass
                            and item.get('sim_present') is True and
                            _positive_running_lesson(item.get('running_action'))):
                        seen.add(sid)
            seen_actions.update(seen)
            overall_presence.extend(count==len(ids) for count in counts)
            classes_result[str(klass)]={
                'registered':len(ids),'minimum_instanced':min(counts),
                'maximum_instanced':max(counts),
                'running_lesson_seen':sorted(seen),
                'all_instanced_each_sample':all(count==len(ids)
                                                for count in counts)}
        result['periods'][phase]={
            'snapshot_count':len(samples),'class_results':classes_result,
            'lesson_has_native_running_actions':any(
                data['running_lesson_seen'] for data in classes_result.values())}
    for row in entries:
        if not isinstance(row,dict) or _entry_period(row) is None:
            continue
        result['sample_count']+=1
        lag=row.get('dual_clock',{}).get('lag_minutes')
        if type(lag) in (int,float) and -240<=lag<=1440:
            lags.append(float(lag))
    if overall_presence:
        result['all_registered_present_in_every_sample']=all(overall_presence)
    if result['sample_count']:
        result['all_registered_have_running_lesson_evidence']=(
            bool(desired) and all(sid in seen_actions for sid in desired))
    if lags:
        result['clock_lag_minutes']={
            'observed_samples':len(lags),'minimum':round(min(lags),2),
            'median':_median(lags),'maximum':round(max(lags),2)}
    return result
