"""The Sims 4 EA *class-phase* read-only diagnostic.

Mapping is grounded in the user's extracted original High School Years tunings.
Important: the class1 hidden trait is not proof that the NPC has actually
been assigned by the schedule to classroom 1. We do NOT change/remove roles,
situations or whiteboard states here.
"""
EA_CLASS1_TRAIT = 293779
CLASS_PHASE_GUIDS = {
  293815: 'GoToClass1 (fase Classe 1)',
  304701: 'GoToClass1_NoTrait (fase Classe 1 alternativa)',
  297774: 'Background_GoToClass_Others (smistamento altri)',
  304565: 'Background_AttendClass1 (lezione Classe 1)',
  304703: 'Background_AttendClass1_NoTrait (lezione Classe 1 alternativa)',
  304567: 'Background_AttendClass_Others (lezione altri)',
}


def inspect_phase(info, situation_manager, class1_trait, guid_from_situation):
    """Reads loaded Sim's visible phase situations without changing anything."""
    trait = bool(info.has_trait(class1_trait)) if class1_trait is not None else None
    getter = getattr(info, 'get_sim_instance', None)
    sim = getter() if callable(getter) else None
    if sim is None:
        return {'loaded':False, 'class1_trait':trait, 'phases':[]}
    if situation_manager is None:
        return {'loaded':True, 'class1_trait':trait, 'phases':[],
                'warning':'SituationManager non disponibile'}
    get_situations = getattr(situation_manager, 'get_situations_sim_is_in', None)
    if not callable(get_situations):
        return {'loaded':True, 'class1_trait':trait, 'phases':[],
                'warning':'API situazioni non disponibile'}
    situations = tuple(get_situations(sim) or ())
    phases = []
    for sit in situations:
        guid = guid_from_situation(sit)
        if guid in CLASS_PHASE_GUIDS:
            phases.append(CLASS_PHASE_GUIDS[guid])
    return {'loaded':True, 'class1_trait':trait,
            'phases':sorted(set(phases))}
