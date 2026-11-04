"""M85 offline roster and EA situation counters; no game mutations."""
SCHOOL = frozenset((277733, 298052, 298096, 276686, 276681, 297168))

def summarize(class_ids, physical_sim_ids, school_situations_by_sim):
    groups = tuple(frozenset(str(s) for s in group) for group in class_ids)
    enrolled = frozenset().union(*groups) if groups else frozenset()
    physical = frozenset(str(s) for s in physical_sim_ids)
    school = frozenset(str(s) for s, roles in school_situations_by_sim.items()
                       if str(s) in physical and
                       any(int(role) in SCHOOL for role in roles))
    return {
        'registered': len(enrolled),
        'registered_on_lot': len(enrolled & physical),
        'registered_in_ea_school_situations': len(enrolled & school),
        'unregistered_in_ea_school_situations': len(school - enrolled),
        'on_lot_per_class': tuple(len(group & physical) for group in groups),
        'in_ea_school_situations_per_class': tuple(len(group & school) for group in groups),
        'seated_in_correct_class_verified': False,
    }
