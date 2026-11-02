"""M105: measure EA's ORIGINAL Base Student situation budget before spawn.

Read-only bridge between the 3+5+8 roster planner and M96's school count.
It records what EA would have scheduled and how it compares with the eight
Base places required; it NEVER adjusts the number, creates situations,
claims core roles have been reserved, or authorizes the M96 count override.

Not in a shipped Mac archive. Install only after the EA WeeklyScheduleDay
class and its original classmethod have been verified in the current game.
"""
SCHOOL_SCHEDULES=frozenset((277657,279958))
BASE_SITUATION=277733
MAX_EVENTS=32


def _count_range(value):
    if (not isinstance(value,(tuple,list)) or len(value)!=2
            or any(type(x) is not int or x<0 for x in value)
            or value[0]>value[1]):
        return None
    return tuple(value)


def _valid_plan(plan):
    if not isinstance(plan,dict):
        return False
    if (plan.get('status')!='PREPARED_NOT_EA_BOUND'
            or plan.get('all_core_appointments_confirmed') is not True
            or plan.get('base_invites_needed')!=8
            or plan.get('core_count')!=5
            or plan.get('playable_count')!=3):
        return False
    classes=plan.get('classes')
    if (not isinstance(classes,(tuple,list)) or len(classes)!=2
            or any(not isinstance(c,(tuple,list)) or len(c)!=8 for c in classes)):
        return False
    enrolled=tuple(str(x) for c in classes for x in c)
    core=plan.get('core_role_assignments')
    base=plan.get('normal_base_ids')
    played=plan.get('playable')
    if (not isinstance(core,(tuple,list)) or len(core)!=5
            or not isinstance(base,(tuple,list)) or len(base)!=8
            or not isinstance(played,(tuple,list)) or len(played)!=3):
        return False
    try:
        core_ids=tuple(str(sid) for _,sid in core)
        groups=(tuple(str(x) for x in played),core_ids,tuple(str(x) for x in base))
        if (len(set(enrolled))!=16
                or tuple(str(x) for x in plan.get('all_16',()))!=enrolled
                or any(len(set(g))!=len(g) for g in groups)
                or set(groups[0])|set(groups[1])|set(groups[2])!=set(enrolled)
                or len(set(groups[0]+groups[1]+groups[2]))!=16):
            return False
    except (TypeError,ValueError):
        return False
    return True


class NativeScheduleAudit(object):
    """One immutable M105 plan, bounded history, zero count overrides."""

    def __init__(self,plan,save_slot,sim_day):
        if not _valid_plan(plan):
            raise ValueError('sixteen-student M105 plan not complete')
        if (type(save_slot) not in (int,str) or
                not str(save_slot).isdigit() or int(save_slot)<=0
                or type(sim_day) is not int or sim_day<0):
            raise ValueError('invalid school save/day')
        self.plan=plan
        self.slot=str(save_slot)
        self.day=sim_day
        self.events=[]
        self.installed=False
        self.errors=0

    def observe(self,schedule_guid,situation_guid,original,context):
        """Record only original EA count for the verified current school day."""
        if (type(schedule_guid) is not int
                or schedule_guid not in SCHOOL_SCHEDULES
                or type(situation_guid) is not int
                or situation_guid!=BASE_SITUATION):
            return original
        if not isinstance(context,dict) or (
                context.get('school_verified') is not True or
                str(context.get('save_slot'))!=self.slot or
                context.get('sim_day')!=self.day):
            return original
        zone=context.get('school_zone')
        if type(zone) not in (str,int) or not str(zone).isdigit() or int(zone)<=0:
            return original
        bounds=_count_range(original)
        if bounds is None:
            self.errors+=1
            return original
        low,high=bounds
        entry={
            'kind':'EA_BASE_SITUATION_ORIGINAL_COUNT',
            'schedule_guid':schedule_guid,
            'situation_guid':situation_guid,
            'school_zone':str(zone),
            'save_slot':self.slot,
            'sim_day':self.day,
            'ea_original_min':low,'ea_original_max':high,
            'mhs_base_targets_needed':8,
            'vanilla_min_guarantees_eight':low>=8,
            'vanilla_max_can_reach_eight':high>=8,
            'minimum_shortfall':max(0,8-low),
            'maximum_shortfall':max(0,8-high),
            'core_roles_pre_spawn_reserved':False,
            'm96_override_authorized':False,
            'ea_count_changed':False,
            'attendance_verified':False,
        }
        self.events.append(entry)
        del self.events[:-MAX_EVENTS]
        return original

    def snapshot(self):
        return {
            'kind':'M105_EA_SCHOOL_COUNT_AUDIT_ONLY',
            'status':'ORIGINAL_BASE_COUNT_OBSERVED' if self.events else 'NO_VERIFIED_EA_COUNT_YET',
            'save_slot':self.slot,'sim_day':self.day,
            'observations':len(self.events),
            'last_event':dict(self.events[-1]) if self.events else None,
            'errors':self.errors,
            'm96_override_authorized':False,
            'game_count_changed':False,
            'core_roles_pre_spawn_reserved':False,
            'student_arrival_verified':False,
        }

    def install(self,weekly_day_class,context_provider):
        """Optional OBSERVATION-only hook; never change EA's return.

        Require the real EA classmethod, not a guessed instance method.
        Reject an M96 count hook to avoid logging an already altered count.
        No hook is installed by importing this module.
        """
        if self.installed or not callable(context_provider):
            return False
        owner=None
        for cls in getattr(weekly_day_class,'__mro__',(weekly_day_class,)):
            descriptor=cls.__dict__.get('get_long_term_situation_count')
            if isinstance(descriptor,classmethod):
                owner=cls
                break
        if owner is None:
            return False
        previous=owner.__dict__['get_long_term_situation_count'].__func__
        if (getattr(previous,'_mhs96_count_hook',False)
                or getattr(previous,'_mhs105_schedule_audit',False)):
            return False

        def wrapped(cls,data,resolver):
            original=previous(cls,data,resolver)
            try:
                schedule_guid=getattr(cls,'guid64',None)
                situation=getattr(data,'situation',None)
                situation_guid=getattr(situation,'guid64',None)
                if (schedule_guid in SCHOOL_SCHEDULES
                        and situation_guid==BASE_SITUATION):
                    context=context_provider()
                    self.observe(schedule_guid,situation_guid,original,context)
            except Exception:
                self.errors+=1
            return original

        wrapped._mhs105_schedule_audit=True
        setattr(owner,'get_long_term_situation_count',classmethod(wrapped))
        self.installed=True
        return True
