"""MY HIGH SCHOOL v0.8: one-Sim, one-school-day class-routing experiment.

The user-provided EA XML tuning says:
* 293779: trait_HighSchool_Active_Class1Student (HIDDEN)
* 293778: EA loot giving the class 1 trait, triggered by GoToClass1 buff.
* 304593: EA loot removing that trait, triggered by GoToClass2 buff.
* EA class attend interaction tests trait vs. Class1/Class2 whiteboard states.

Do not override EA tuning or change any other Sim. An added hidden trait can be
saved with a Sim, and EA's own buffs can later remove it. Test save ONLY.
"""
CLASS1_TRAIT_ID = 293779

class ClassRouteError(RuntimeError):
    pass


def fetch_class1_trait(trait_manager):
    if trait_manager is None:
        raise ClassRouteError('Gestore dei tratti non disponibile; nessun cambiamento.')
    trait = trait_manager.get(CLASS1_TRAIT_ID)
    if trait is None or int(getattr(trait, 'guid64', -1)) != CLASS1_TRAIT_ID:
        raise ClassRouteError('Tratto originale Classe 1 EA 293779 non trovato; nessun cambiamento.')
    return trait


def set_ae_class_trait(sim_info, enrolled_class, class1_trait):
    """Apply only original EA Class1Student marker according to user's roster.

    Return original boolean trait state for explicit rollback if situation fails.
    All errors fail closed. Caller MUST ensure Sim is target teen in test save.
    """
    if enrolled_class not in (1,2):
        raise ClassRouteError('Classe del registro non supportata (solo 1/2).')
    if sim_info is None or class1_trait is None:
        raise ClassRouteError('Sim o tratto non disponibile.')
    check = getattr(sim_info, 'has_trait', None)
    add = getattr(sim_info, 'add_trait', None)
    remove = getattr(sim_info, 'remove_trait', None)
    if not callable(check) or not callable(add) or not callable(remove):
        raise ClassRouteError('API tratti SimInfo non disponibili.')
    before = bool(check(class1_trait))
    desired = enrolled_class == 1
    if before != desired:
        try:
            if desired:
                add(class1_trait)
            else:
                remove(class1_trait)
        except Exception as exc:
            raise ClassRouteError('Impossibile aggiornare il tratto EA: {}.'.format(type(exc).__name__))
    if bool(check(class1_trait)) != desired:
        raise ClassRouteError('Tratto EA non verificato dopo l aggiornamento.')
    return before


def restore_trait_state(sim_info, class1_trait, before):
    """Best-effort rollback only if a new situation could NOT be created."""
    if bool(sim_info.has_trait(class1_trait)) == bool(before):
        return True
    try:
        if before:
            sim_info.add_trait(class1_trait)
        else:
            sim_info.remove_trait(class1_trait)
    except Exception:
        return False
    return bool(sim_info.has_trait(class1_trait)) == bool(before)
