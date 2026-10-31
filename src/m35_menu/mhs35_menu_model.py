"""M35 dynamic menu specification, pure logic, Python 3.7 compatible.

This is deliberately NOT a PieMenuCategory tuning or installed mod yet.
The M30/M32 pie category resources produced an invalid-category-ID UI exception.
Use this data model as a tested contract for future safe UI integration.

No game imports, no I/O, no JSON writes.
"""
from mhs34_settings import SchoolSettings


class MenuModelError(ValueError):
    pass


def build_menu(settings, roster):
    """Return immutable parent and class submenu structure for active save.

    When inactive, only activation is offered. When active, number of
    visible classes follows saved 2/3 selection. Each active class has
    exactly two destination-specific transfer options (or one when
    only 2 classes are selected). This does not imply that real Sims
    interactions already obey those conditions.
    """
    if not isinstance(settings, SchoolSettings):
        raise MenuModelError('Impostazioni non valide')
    if settings.slot != roster.slot:
        raise MenuModelError('Slot registro e impostazioni non corrispondono')

    if not settings.active:
        return {
            'root':'MY HIGH SCHOOL',
            'active':False,
            'actions':('attiva',),
            'classes':()
        }

    active_classes=tuple(range(1,settings.class_count+1))
    tabs=[]
    for klass in active_classes:
        members=tuple(roster.class_members(klass))
        tabs.append({
            'name':'Classe {}'.format(klass),
            'class_id':klass,
            'enrolled':len(members),
            'capacity':8,
            'actions':(
                ('iscrivi',klass),
                ('consulta',klass),
                ('rimuovi',klass),
            ) + tuple(('trasferisci',klass,target)
                      for target in active_classes if target!=klass)
        })
    return {
        'root':'MY HIGH SCHOOL',
        'active':True,
        'actions':('disattiva','impostazioni'),
        'classes':tuple(tabs)
    }


def can_select_class(settings,klass):
    """Explicit visibility gate for optional class 3."""
    return (isinstance(settings,SchoolSettings) and
            settings.active and
            type(klass) is int and 1<=klass<=settings.class_count)
