"""Pure saved-setting visibility policy for a nested school menu (Py 3.7)."""


class VisibilityError(ValueError):
    pass


def allowed(active, class_count, action, klass=0):
    if type(active) is not bool or type(class_count) is not int or class_count not in (2,3):
        raise VisibilityError('Configurazione non valida')
    if action=='enable':
        return not active
    if action=='disable':
        return active
    if action=='activate_third':
        return active and class_count==2
    if action=='deactivate_third':
        return active and class_count==3
    if action=='class':
        return (active and type(klass) is int and 1<=klass<=class_count)
    if action=='transfer':
        return (active and isinstance(klass,tuple) and len(klass)==2
                and all(type(n) is int and 1<=n<=class_count for n in klass)
                and klass[0]!=klass[1])
    raise VisibilityError('Operazione non definita')


def available_from_settings(settings, action, klass=0):
    return allowed(settings.active,settings.class_count,action,klass)
