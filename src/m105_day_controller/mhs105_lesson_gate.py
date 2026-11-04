"""M105: proof requirements for two classes at the actual EA lesson phase.

EA WeeklyScheduleSituationData.try_start takes the *already instantiated*
sims from the zone director and assigns each to a SituationJob based on
tests, skipping the phase entirely if its minimum jobs can't be met.

Therefore a proposed 8+8 enrollment or an EA school invitation is NOT
evidence of actual classroom membership or seating.
This module is read-only; it never spawns or assigns a Sim.
"""
def _ids(values):
    if not isinstance(values,(tuple,list,set,frozenset)):
        return None
    ids=tuple(str(x) for x in values)
    if any(not x.isdigit() or int(x)<=0 or str(int(x))!=x for x in ids):
        return None
    return frozenset(ids)

def assess_lesson_phase(classes,observed_on_lot,observed_ea_students,
                        observed_ea_class_members=None,
                        observed_sitting_by_class=None):
    """Separate physical presence, EA school membership, class job and sitting.

    observed_ea_class_members = tuple of two iterable SimID sets observed
    as ACTUAL EA lesson job assignments, not MHS registration.
    observed_sitting_by_class = optional tuple of two sets confirmed to be
    physically seated in their registered class. A missing observation
    must NEVER become a 'verified seated' claim.
    """
    base={'actual_students_present':False,'ea_school_membership_verified':False,
          'eight_plus_eight_class_jobs_verified':False,
          'seated_correctly_verified':False,'game_modified':False}
    def report(status,reason='',**detail):
        return dict(base,status=status,reason=reason,**detail)
    if not isinstance(classes,(tuple,list)) or len(classes)!=2:
        return report('BLOCKED','exactly two enrolled classes required')
    class_ids=tuple(_ids(group) for group in classes)
    if (any(g is None or len(g)!=8 for g in class_ids)
            or len(class_ids[0]|class_ids[1])!=16):
        return report('BLOCKED','eight unique members per class required')
    on_lot=_ids(observed_on_lot)
    ea=_ids(observed_ea_students)
    if on_lot is None or ea is None:
        return report('UNKNOWN','live zone and EA school member sets unavailable')
    enrolled=class_ids[0]|class_ids[1]
    absent=enrolled-on_lot
    if absent:
        return report('INSUFFICIENT_PHYSICAL_ATTENDANCE',
                      'EA lesson schedule cannot assign absent Sims',
                      registered_on_lot=len(enrolled&on_lot),
                      absent_enrolled=tuple(sorted(absent)))
    extra=ea-enrolled
    if extra:
        return report('UNREGISTERED_EA_STUDENTS',
                      'EA has unregistered school students',
                      extra_count=len(extra),
                      registered_in_ea=len(ea&enrolled))
    if enrolled-ea:
        return report('SCHOOL_ROLE_MISSING',
                      'some enrolled Sims lack an active EA school situation',
                      registered_in_ea=len(ea&enrolled))
    ready={'actual_students_present':True,
           'ea_school_membership_verified':True}
    if observed_ea_class_members is None:
        return dict(report('PHYSICALLY_PRESENT_NOT_CLASS_VERIFIED',
                           'EA lesson assignment not yet observed'),
                    **ready)
    if not isinstance(observed_ea_class_members,(tuple,list)) or len(observed_ea_class_members)!=2:
        return report('UNKNOWN','need real membership of both EA lesson jobs')
    actual=tuple(_ids(group) for group in observed_ea_class_members)
    if any(g is None for g in actual):
        return report('UNKNOWN','EA lesson job members unreadable')
    if actual!=class_ids:
        return dict(report('WRONG_EA_CLASS_ASSIGNMENT',
                           'EA lesson jobs do not match 8+8 registry',
                           class1_verified=len(class_ids[0]&actual[0]),
                           class2_verified=len(class_ids[1]&actual[1])),
                    **ready)
    qualified={'actual_students_present':True,
               'ea_school_membership_verified':True,
               'eight_plus_eight_class_jobs_verified':True}
    if observed_sitting_by_class is None:
        return dict(report('EA_CLASSES_VERIFIED_NOT_SEATED',
                           'EA job assignment is not proof of actual seating'),
                    **qualified)
    if (not isinstance(observed_sitting_by_class,(tuple,list))
            or len(observed_sitting_by_class)!=2):
        return report('UNKNOWN','sitting must be verified for both classes')
    seated=tuple(_ids(group) for group in observed_sitting_by_class)
    if any(g is None for g in seated) or seated!=class_ids:
        return dict(report('SEATING_NOT_VERIFIED',
                           'not all registered students confirmed at their desks'),
                    **qualified)
    return dict(report('SCHOOL_DAY_16_8_8_SEATED_VERIFIED'),
                **qualified,seated_correctly_verified=True)
