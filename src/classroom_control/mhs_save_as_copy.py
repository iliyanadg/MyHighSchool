"""Safe, explicit transfer of four MHS registries after EA 'Save As'.

EA .save files do NOT contain the external MHS JSON registries.  The only
supported operation is a user-initiated import into a completely EMPTY target
slot, with every enrolled/student/staff identity validated in the *current*
save.  No guesses based on display names, no changes to a .save file,
no cross-save aliasing, and no mutation of already configured destinations.

Python 3.7-compatible, no Sims 4 runtime imports. Caller supplies the live
SimInfo lookup, age/species constants and current active household Sim IDs.
"""
import os
import re
import tempfile

from mhs_m2_roster import SchoolRoster, canonical_save_slot
from mhs_m2_store import RosterStore
from mhs34_settings import SchoolSettings, SettingsStore
from mhs53_staff_store import StaffRoster, StaffStore
from mhs97_core_role_store import CoreRoleRoster, CoreRoleStore


class SaveAsCopyError(ValueError):
    pass


def _stores(folder):
    return (
        ('students', RosterStore(folder), SchoolRoster),
        ('settings', SettingsStore(folder), SchoolSettings),
        ('staff', StaffStore(folder), StaffRoster),
        ('core', CoreRoleStore(folder), CoreRoleRoster),
    )


def _path(store, slot):
    return store.path(slot)


def _existing_destinations(folder, slot):
    return [kind for kind, store, _ in _stores(folder)
            if os.path.lexists(_path(store, slot))]


def _positive_id(value):
    if type(value) not in (int, str):
        raise SaveAsCopyError('SIM_ID_INVALID')
    value = str(value)
    if not value.isdigit() or not int(value) or str(int(value)) != value:
        raise SaveAsCopyError('SIM_ID_INVALID')
    return value


def _game_identity_ok(student_roster, staff_roster, core_roster, info_manager,
                      teen, human, adult_ages, active_household_ids):
    getter = getattr(info_manager, 'get', None)
    if not callable(getter):
        raise SaveAsCopyError('LIVE_SIM_MANAGER_UNAVAILABLE')
    ids = set(student_roster.assignments)
    groups = (student_roster.class_members(1), student_roster.class_members(2))
    if (len(groups[0]) != 8 or len(groups[1]) != 8 or
            len(ids) != 16 or student_roster.class_members(3)):
        raise SaveAsCopyError('SOURCE_REQUIRES_TWO_CLASSES_OF_EIGHT')
    if not core_roster.complete:
        raise SaveAsCopyError('SOURCE_REQUIRES_FIVE_CORE_ROLES')
    core_ids = set(core_roster.chosen().values())
    if len(core_ids) != 5 or not core_ids <= ids:
        raise SaveAsCopyError('CORE_STUDENTS_NOT_REGISTERED')
    staff_ids = staff_roster.all_ids()
    if staff_ids & ids:
        raise SaveAsCopyError('STUDENT_AND_STAFF_COLLISION')

    played = set(_positive_id(x) for x in active_household_ids)
    # A copied EA save retains original Sim IDs; require a current, played,
    # registered teen in this save before any import. A completely unrelated
    # target with different household identities cannot be populated.
    if not played or not played & ids:
        raise SaveAsCopyError('CURRENT_HOUSEHOLD_DOES_NOT_MATCH_SOURCE')
    if played & core_ids:
        raise SaveAsCopyError('PLAYABLE_HAS_CORE_NPC_ROLE')

    for sid in sorted(ids | staff_ids, key=int):
        try:
            info = getter(int(sid))
            if info is None:
                raise SaveAsCopyError('SAVED_SIM_MISSING_IN_CURRENT_SAVE')
            if sid in ids:
                if getattr(info, 'age', None) != teen or getattr(info, 'species', None) != human:
                    raise SaveAsCopyError('REGISTERED_SIM_NOT_HUMAN_TEEN')
                # Current household membership (checked above) determines
                # who is player-controlled for this save. The EA selectable
                # flag is transient and must not prevent copying identical
                # registered Sims into a genuine Save As destination.
            else:
                if (getattr(info, 'age', None) not in adult_ages or
                        getattr(info, 'species', None) != human):
                    raise SaveAsCopyError('SAVED_STAFF_NOT_ADULT_HUMAN')
        except SaveAsCopyError:
            raise
        except Exception:
            raise SaveAsCopyError('LIVE_SIM_INFO_UNREADABLE')
    return len(staff_ids)


def prepare_copy(folder, source_slot, target_slot, info_manager,
                 teen, human, adult_ages, active_household_ids):
    """Validate the complete source and empty destination; don't write data."""
    try:
        source = canonical_save_slot(source_slot)
        target = canonical_save_slot(target_slot)
    except Exception:
        raise SaveAsCopyError('SAVE_SLOT_ID_INVALID')
    if source == target:
        raise SaveAsCopyError('SAME_SOURCE_AND_TARGET')
    # A user may already have edited the copied save's school menus.
    # We may fill ONLY missing files; existing files must match their
    # expected cloned contents exactly or the import fails without writes.
    stores = _stores(folder)
    records = {}
    for kind, store, _ in stores:
        path = _path(store, source)
        if not os.path.isfile(path) or os.path.islink(path):
            raise SaveAsCopyError('SOURCE_' + kind.upper() + '_MISSING')
        try:
            records[kind] = store.load(source)
        except Exception:
            raise SaveAsCopyError('SOURCE_' + kind.upper() + '_INVALID')

    settings = records['settings']
    if not settings.active or settings.class_count != 2:
        raise SaveAsCopyError('SOURCE_SCHOOL_NOT_ACTIVE_TWO_CLASSES')
    staff_count = _game_identity_ok(
        records['students'], records['staff'], records['core'],
        info_manager, teen, human, adult_ages, active_household_ids)

    # Rebuild using each validated schema: do not copy the old slot field,
    # filename or undo journal into a different save.
    cloned = {
        'students': SchoolRoster(target, dict(records['students'].assignments)),
        'settings': SchoolSettings(target, settings.active, settings.class_count),
        'staff': StaffRoster(target, records['staff'].to_dict()['roles']),
        'core': CoreRoleRoster(target, dict(records['core'].roles)),
    }
    payload=[]
    unchanged=[]
    for kind,store,_ in stores:
        dest=_path(store,target)
        expected=cloned[kind].to_json()
        if os.path.lexists(dest):
            if not os.path.isfile(dest) or os.path.islink(dest):
                raise SaveAsCopyError('TARGET_' + kind.upper() + '_NOT_REGULAR')
            try:
                present=store.load(target)
            except Exception:
                raise SaveAsCopyError('TARGET_' + kind.upper() + '_INVALID')
            if present.to_json()!=expected:
                raise SaveAsCopyError(
                    'TARGET_' + kind.upper() + '_DIFFERS_NO_OVERWRITE')
            unchanged.append(kind)
        else:
            payload.append((kind,dest,expected))
    return {'source':source,'target':target,'payload':tuple(payload),
            'unchanged':tuple(unchanged),'students':16,
            'staff':staff_count,'roles':5,
            # Compare candidates after rebinding to the SAME target slot.
            # Multiple source saves with identical school configuration are
            # equivalent; choosing any cannot select different students.
            'configuration':tuple((kind,cloned[kind].to_json())
                                  for kind,_,_ in stores)}


def import_copy(folder, source_slot, target_slot, info_manager,
                teen, human, adult_ages, active_household_ids):
    """Create only missing target files; rollback only files we created.

    Existing matching files remain unchanged, allowing recovery of a partly
    initialized Save As fork; existing DIFFERENT files are never overwritten.
    A crash part-way through a multi-file import can leave matching partial
    files; a retry safely completes the missing ones after revalidation.
    """
    plan = prepare_copy(folder,source_slot,target_slot,info_manager,
                        teen,human,adult_ages,active_household_ids)
    staged = []
    created = []
    try:
        if not os.path.isdir(folder):
            os.makedirs(folder)
        # Stage every payload in the same folder before publishing any.
        for kind, dest, data in plan['payload']:
            fd, staging = tempfile.mkstemp(prefix='.mhs_saveas_',
                                            suffix='.tmp',dir=folder)
            staged.append(staging)
            with os.fdopen(fd, 'w', encoding='utf-8') as out:
                out.write(data)
                out.flush()
                os.fsync(out.fileno())
        # Exclusive creation is the final race-safety gate: another writer
        # cannot have created a target file between preflight and commit.
        for (kind,dest,data),staging in zip(plan['payload'],staged):
            with open(staging,'rb') as src:
                blob=src.read()
            fd=os.open(dest,os.O_CREAT | os.O_EXCL | os.O_WRONLY,0o600)
            created.append(dest)
            with os.fdopen(fd,'wb') as out:
                out.write(blob)
                out.flush()
                os.fsync(out.fileno())
        report={key:plan[key] for key in ('source','target','students','staff','roles')}
        report['copied_files']=len(created)
        report['unchanged_files']=len(plan['unchanged'])
        return report
    except Exception as exc:
        for dest in reversed(created):
            try:
                os.unlink(dest)
            except OSError:
                pass
        if isinstance(exc, FileExistsError):
            raise SaveAsCopyError('TARGET_CHANGED_NO_OVERWRITE')
        raise SaveAsCopyError('COPY_ABORTED_' + type(exc).__name__)
    finally:
        for staging in staged:
            try:
                os.unlink(staging)
            except OSError:
                pass


def eligible_source_slots(folder, target_slot, info_manager,
                          teen, human, adult_ages, active_household_ids):
    """Return only verified source slots; ambiguous candidates need a choice."""
    target=canonical_save_slot(target_slot)
    if not os.path.isdir(folder):
        return ()
    sources=[]
    try:
        names=os.listdir(folder)
    except OSError:
        return ()
    for name in names:
        match=re.fullmatch(r'Registro_slot_([1-9][0-9]*)\.json',name)
        if not match or match.group(1)==target:
            continue
        try:
            plan=prepare_copy(folder,match.group(1),target,info_manager,
                              teen,human,adult_ages,active_household_ids)
            sources.append((plan['source'],plan['students'],plan['staff']))
        except (SaveAsCopyError,ValueError):
            continue
    return tuple(sorted(sources,key=lambda row:int(row[0])))


def import_unique_copy(folder,target_slot,info_manager,teen,human,
                       adult_ages,active_household_ids):
    """User opted in: recover only when exactly one verified source exists."""
    matches=eligible_source_slots(folder,target_slot,info_manager,teen,human,
                                  adult_ages,active_household_ids)
    if not matches:
        raise SaveAsCopyError('NO_MATCHING_SOURCE_SAVE')
    if len(matches)!=1:
        # Exact-equivalent copies of an earlier save are safe to merge: all
        # four records produce identical target-slot JSON. Differing sources
        # remain ambiguous and must never be selected by file timestamp.
        signatures = [
            prepare_copy(folder,row[0],target_slot,info_manager,teen,
                         human,adult_ages,active_household_ids)['configuration']
            for row in matches]
        if any(signature != signatures[0] for signature in signatures[1:]):
            raise SaveAsCopyError('MULTIPLE_SOURCE_SAVES_CHOOSE_SLOT')
    return import_copy(folder,matches[0][0],target_slot,info_manager,teen,
                       human,adult_ages,active_household_ids)
