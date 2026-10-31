"""M57: one verified school selection manifest for EA tuning adapters.

This module is pure Python 3.7, with NO EA imports or side effects.
Student eligibility, staff roles and class capacities come only from the
MHS save-scoped registries. EA's school filters MUST eventually consume
these exact IDs before situation roles are filled; invitations after EA
has picked classmates are not a substitute.

Never silently count playable teens *on top* of eight classroom places.
Never generate random replacements. Do not auto-assign special roles.
"""


class ManifestError(ValueError):
    pass


STUDENT_LIMIT = 8
STAFF_ROLES = (
    'principal', 'teacher1', 'teacher2', 'teacher3',
    'cafeteria', 'custodians'
)
CORE_ROLES = ('mean', 'chess', 'cheer', 'football', 'computer')


def _id(raw):
    if isinstance(raw, bool) or not isinstance(raw, (str, int)):
        raise ManifestError('ID Sim non valido')
    val = str(raw)
    if not val.isdigit() or int(val) < 1 or str(int(val)) != val:
        raise ManifestError('ID Sim non valido')
    return val


def _all_ids(staff, role):
    if role not in STAFF_ROLES:
        raise ManifestError('Ruolo personale non riconosciuto')
    return tuple(_id(x) for x in staff.members(role))


class SchoolManifest(object):
    """Read-only planned cohort, not a claim that EA spawned these people."""

    def __init__(self, slot, class_ids, staff_ids, active_household_teens):
        self.slot = str(slot)
        self.class_ids = tuple(tuple(group) for group in class_ids)
        self.staff_ids = {role:tuple(values) for role, values in staff_ids.items()}
        self.active_household_teens = frozenset(active_household_teens)
        self.all_student_ids = frozenset(s for group in self.class_ids for s in group)
        self.to_invite = frozenset(
            sid for sid in self.all_student_ids
            if sid not in self.active_household_teens)
        self.playable_in_classes = frozenset(
            sid for sid in self.all_student_ids
            if sid in self.active_household_teens)
        self.playable_unenrolled = frozenset(
            self.active_household_teens - self.all_student_ids)

    @property
    def capacity(self):
        return len(self.class_ids) * STUDENT_LIMIT

    @property
    def selected_count(self):
        return len(self.all_student_ids)

    def match_student(self, sid):
        return _id(sid) in self.all_student_ids

    def match_staff(self, role, sid):
        return _id(sid) in self.staff_ids.get(role, ())

    def class_of(self, sid):
        sid = _id(sid)
        for klass, cohort in enumerate(self.class_ids, 1):
            if sid in cohort:
                return klass
        return None

    def compare_live_ids(self, observed_students, observed_staff=None):
        """Report who really showed up, without removing nonregistered NPCs."""
        actual = frozenset(_id(x) for x in observed_students)
        planned = self.all_student_ids
        staff = observed_staff or {}
        summary = {
            'registered_total': len(planned),
            'physical_registered': len(actual & planned),
            'missing_registered': tuple(sorted(planned - actual, key=int)),
            'physical_unregistered': tuple(sorted(actual - planned, key=int)),
            'active_playable_not_registered': tuple(
                sorted(self.playable_unenrolled, key=int)),
            'registered_per_class': tuple(len(c) for c in self.class_ids),
            'physical_registered_per_class': tuple(
                len(actual.intersection(c)) for c in self.class_ids),
        }
        mismatch = {}
        for role in STAFF_ROLES:
            candidates = frozenset(_id(x) for x in staff.get(role, ()))
            expected = frozenset(self.staff_ids[role])
            mismatch[role] = {
                'configured': tuple(sorted(expected, key=int)),
                'physical_matching': tuple(sorted(candidates & expected, key=int)),
                'physical_unassigned': tuple(sorted(candidates - expected, key=int)),
                'missing_configured': tuple(sorted(expected - candidates, key=int))
            }
        summary['staff'] = mismatch
        return summary


def make_manifest(roster, staff, class_count, household_teen_ids):
    """A complete deterministic class-and-staff plan, scoped to one save.

    The selection adapter will need to map these IDs onto EA filters:
      students: 280516 + team/mean filters
      staff: principal, teacher1, teacher2, janitor, cafeteria filters

    Those adapters are deliberately NOT installed by this pure module.
    """
    if class_count not in (2, 3):
        raise ManifestError('Numero classi non valido')
    if roster.slot != staff.slot:
        raise ManifestError('Registro studenti/personale di salvataggi diversi')
    class_ids = [tuple(_id(x) for x in roster.class_members(k))
                 for k in range(1, class_count+1)]
    all_students = [x for group in class_ids for x in group]
    if any(len(group) > STUDENT_LIMIT for group in class_ids):
        raise ManifestError('Una classe supera 8 studenti')
    if len(set(all_students)) != len(all_students):
        raise ManifestError('Studente assegnato a piu classi')
    staff_ids = {role:_all_ids(staff,role) for role in STAFF_ROLES}
    all_staff = [sid for role in STAFF_ROLES for sid in staff_ids[role]]
    if len(set(all_staff)) != len(all_staff):
        raise ManifestError('Personale duplicato nei ruoli')
    if set(all_staff) & set(all_students):
        raise ManifestError('Un Sim e studente e personale')
    household = tuple(_id(x) for x in household_teen_ids)
    if len(set(household)) != len(household):
        raise ManifestError('Giocabile duplicato nel nucleo')
    return SchoolManifest(roster.slot, class_ids, staff_ids, household)
