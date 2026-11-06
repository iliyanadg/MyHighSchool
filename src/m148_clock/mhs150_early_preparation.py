"""M150 read-only EA prep evidence near simulated 09:40; not proof of seating."""
def audit_940_preparation(entries,groups,anchors):
    result={'kind':'M150_0940_PREPARATION','sample_clock':None,
            'displayed_clock':None,'lag_minutes':None,'per_class':{},
            'all_present':None,'correct_native_board_actions':None,
            'class_actions':None,'does_not_prove_routing_or_seating':True,
            'original_ea_schedule_unmodified':True,'world_mutations':0}
    eligible=[]
    for row in entries or ():
        if not isinstance(row,dict) or row.get('period')!='morning':
            continue
        clk=row.get('clock') or {}
        h,m=clk.get('hour'),clk.get('minute')
        if type(h) is int and type(m) is int and h==9 and 36<=m<=49:
            eligible.append((abs(m-40),m,row))
    if not eligible:
        result['reason']='NO_0940_SIM_TIME_SAMPLE'
        return result
    chosen=min(eligible,key=lambda x:(x[0],x[1]))[2]
    result['sample_clock']=(chosen.get('clock') or {}).get('repr')
    dual=chosen.get('dual_clock') or {}
    result['displayed_clock']=(dual.get('game_time_displayed') or {}).get('repr')
    result['lag_minutes']=dual.get('lag_minutes')
    rows={str(x.get('sim_id')):x for x in chosen.get('students',())
          if isinstance(x,dict)}
    present=actions=board_actions=0
    for klass,group in enumerate(groups,1):
        anchor=(anchors or {}).get(klass) or (anchors or {}).get(str(klass))
        expected=str(anchor.get('id')) if isinstance(anchor,dict) else None
        counts={'registered':len(group),'present':0,'class_actions':0,
                'correct_native_board_actions':0}
        for sim_id in group:
            row=rows.get(str(sim_id),{})
            if row.get('registered_class')!=klass:
                continue
            if row.get('sim_present') is True:
                counts['present']+=1
            name=str(row.get('running_action') or '').lower()
            native=('highschool_active_attendclass_npc' in name or
                    'highschool_active_whiteboard_attend_' in name or
                    'highschool_active_ping_gotoobject' in name)
            if native:
                counts['class_actions']+=1
                if expected and str(row.get('action_target_id'))==expected:
                    counts['correct_native_board_actions']+=1
        result['per_class'][str(klass)]=counts
        present+=counts['present']
        actions+=counts['class_actions']
        board_actions+=counts['correct_native_board_actions']
    result['all_present']=present==sum(len(g) for g in groups)
    result['class_actions']=actions
    result['correct_native_board_actions']=board_actions
    result['reason']='OBSERVATION_ONLY'
    return result
