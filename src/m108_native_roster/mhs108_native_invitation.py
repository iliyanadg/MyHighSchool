"""M108: exact native EA school invitations, offline contract only (Python 3.7).

Uses the already established SituationManager.create_situation guest-list seam.
This is deliberately NOT installed in any Mac beta. It prepares invitations
for the SAME original EA Base/Core situations; it never creates extra ones.

A successful create_situation ID is NOT proof that Bouncer accepted, spawned,
assigned or seated a Sim. Native job filters and no-show replacements remain
UNRESOLVED and must be solved before installing any gameplay hook.
"""
BASE_SITUATION = 277733
CORE_SITUATION = 298052
BASE_JOB = 277894
CORE_JOBS = (278965, 278966, 278967, 278968, 303765)
TEACHER_JOBS = frozenset((277895, 278963))
SCHEDULES = frozenset((277657, 279958))


class InvitationPlanError(ValueError):
    pass


def _sid(value):
    if type(value) not in (int, str):
        raise InvitationPlanError('invalid Sim ID')
    value = str(value)
    if not value.isdigit() or int(value) < 1 or value != str(int(value)):
        raise InvitationPlanError('invalid Sim ID')
    return value


def _id_list(values, length):
    if not isinstance(values, (tuple, list)) or len(values) != length:
        raise InvitationPlanError('wrong number of Sim IDs')
    result = tuple(_sid(value) for value in values)
    if len(set(result)) != length:
        raise InvitationPlanError('duplicate Sim ID')
    return result


def prepare_fixed_manifest(classes, playable_ids, core_assignments,
                           save_slot, sim_day, school_zone):
    """Validate immutable user choices. Do not apply the original EA filters.

    Those original filters are demonstrably incompatible with some user
    choices, so compatibility needs a separate school-only admission path.
    """
    if not isinstance(classes, (list, tuple)) or len(classes) != 2:
        raise InvitationPlanError('exactly two classes required')
    groups = tuple(_id_list(group, 8) for group in classes)
    all_students = groups[0] + groups[1]
    if len(set(all_students)) != 16:
        raise InvitationPlanError('student registered more than once')
    played = _id_list(playable_ids, 3)
    if not set(played) <= set(all_students):
        raise InvitationPlanError('playable teen not enrolled')
    if not isinstance(core_assignments, dict) or set(core_assignments) != set(CORE_JOBS):
        raise InvitationPlanError('five exact user-confirmed Core assignments required')
    core = tuple((job, _sid(core_assignments[job])) for job in CORE_JOBS)
    core_ids = tuple(sid for _, sid in core)
    if len(set(core_ids)) != 5:
        raise InvitationPlanError('one student assigned to two Core jobs')
    if not set(core_ids) <= set(all_students) - set(played):
        raise InvitationPlanError('Core role holder must be an enrolled NPC')
    base = tuple(sid for sid in all_students
                 if sid not in set(played) and sid not in set(core_ids))
    if len(base) != 8:
        raise InvitationPlanError('exactly eight Base NPCs required')
    slot = _sid(save_slot)
    zone = _sid(school_zone)
    if type(sim_day) is not int or sim_day < 0:
        raise InvitationPlanError('invalid school day')
    return {
        'status': 'M108_INVITATIONS_PREPARED_NOT_GAME_AUTHORIZED',
        'classes': groups,
        'all_16': all_students,
        'playable': played,
        'core_assignments': core,
        'base_ids': base,
        'save_slot': slot,
        'sim_day': sim_day,
        'school_zone': zone,
        'native_filter_bypass_verified': False,
        'no_show_replacement_blocked': False,
        'school_count_eight_verified': False,
        'class_8_plus_8_verified': False,
        'lot_capacity_verified': False,
        'attendance_verified': False,
    }


class SchoolNativeGuestSession(object):
    """Prepare a cloned guest list for the original EA creation call.

    No monkey patches, no spawning, no writing save files. An external
    caller must validate native call provenance AND separately solve all
    five runtime gates before installing any adapter.
    """

    def __init__(self, manifest, guest_info_class, invited_purpose, job_by_id):
        if (not isinstance(manifest, dict) or
                manifest.get('status') !=
                'M108_INVITATIONS_PREPARED_NOT_GAME_AUTHORIZED'):
            raise InvitationPlanError('not an M108 manifest')
        # This pure adapter refuses fabricated/partial job object mappings.
        if not isinstance(job_by_id, dict) or set(job_by_id) != set((BASE_JOB,) + CORE_JOBS):
            raise InvitationPlanError('six native school SituationJob tunings required')
        for job_id, tuned in job_by_id.items():
            if type(job_id) is not int or getattr(tuned, 'guid64', None) != job_id:
                raise InvitationPlanError('native SituationJob mismatch')
        if not callable(getattr(guest_info_class, 'construct_from_purpose', None)):
            raise InvitationPlanError('EA SituationGuestInfo constructor missing')
        self.manifest = manifest
        self.guest_info_class = guest_info_class
        self.invited_purpose = invited_purpose
        self.job_by_id = job_by_id
        self._pending = set()
        self._confirmed = set()
        self._core_confirmed = False
        self._base_cursor = 0
        self._created_situation_ids = set()

    def _valid_origin(self, context):
        """'native_origin_verified' must come from a verified EA call-site.

        creation_source text alone is NOT sufficient for this flag.
        """
        if not isinstance(context, dict):
            return False
        try:
            return (context.get('native_origin_verified') is True and
                    context.get('school_verified') is True and
                    context.get('schedule_guid') in SCHEDULES and
                    str(context.get('save_slot')) == self.manifest['save_slot'] and
                    type(context.get('sim_day')) is int and
                    context['sim_day'] == self.manifest['sim_day'] and
                    str(context.get('zone_id')) == self.manifest['school_zone'])
        except (KeyError, TypeError):
            return False

    def _guest_list(self, original, new_entries, permit_teacher_guests):
        if original is None:
            return None
        try:
            old = tuple(original.guest_info_gen())
            if permit_teacher_guests:
                if any(getattr(getattr(g, 'job_type', None), 'guid64', None)
                       not in TEACHER_JOBS for g in old):
                    return None
            elif old:
                # Never silently erase a pre-existing EA invitation.
                return None
            replacement = type(original)(
                invite_only=True,
                host_sim_id=original.host_sim_id,
                filter_requesting_sim_id=original.filter_requesting_sim_id)
            for guest in old:
                replacement.add_guest_info(guest.clone_for_guest_list())
            for sid, job_id in new_entries:
                guest = self.guest_info_class.construct_from_purpose(
                    int(sid), self.job_by_id[job_id], self.invited_purpose)
                if (str(getattr(guest, 'sim_id', None)) != sid or
                        getattr(getattr(guest, 'job_type', None), 'guid64', None)
                        != job_id or
                        getattr(guest, 'accept_alternate_sim', None) is not False):
                    return None
                replacement.add_guest_info(guest)
            actual = tuple(replacement.guest_info_gen())
            if (len(actual) != len(old) + len(new_entries) or
                    tuple(str(g.sim_id) for g in actual[len(old):]) !=
                    tuple(sid for sid, _ in new_entries) or
                    replacement.invite_only is not True):
                return None
            return replacement
        except (AttributeError, ValueError, TypeError):
            return None

    def preview(self, situation_guid, original_guest_list, context):
        """Return (ticket, clone) or (None,None), never change EA.

        Core is ONE EA situation with five explicit student roles;
        Base is EIGHT individual EA situations with one exact NPC each.
        Native filter and scheduling compatibility are NOT assumed.
        """
        if not self._valid_origin(context):
            return None, None
        if situation_guid == CORE_SITUATION:
            ticket = 'core'
            if ticket in self._pending or self._core_confirmed:
                return None, None
            entries = tuple((sid, job) for job, sid in
                            self.manifest['core_assignments'])
            clone = self._guest_list(original_guest_list, entries, True)
        elif situation_guid == BASE_SITUATION:
            if 'core' in self._pending or not self._core_confirmed:
                # The fixed Core identities must be committed first;
                # this still does NOT assert that EA spawned them.
                return None, None
            if self._base_cursor >= 8:
                return None, None
            sid = self.manifest['base_ids'][self._base_cursor]
            ticket = 'base:' + sid
            if ticket in self._pending or ticket in self._confirmed:
                return None, None
            clone = self._guest_list(original_guest_list, ((sid, BASE_JOB),), False)
        else:
            return None, None
        if clone is None:
            return None, None
        self._pending.add(ticket)
        return ticket, clone

    def acknowledge_created(self, ticket, situation_id):
        """Commit only an EA situation-creation receipt, NOT attendance."""
        if (ticket not in self._pending or type(situation_id) is not int or
                situation_id <= 0 or situation_id in self._created_situation_ids):
            return False
        self._pending.remove(ticket)
        self._confirmed.add(ticket)
        self._created_situation_ids.add(situation_id)
        if ticket == 'core':
            self._core_confirmed = True
        else:
            self._base_cursor += 1
        return True

    def cancel(self, ticket):
        """Rollback an unsuccessful original EA creation attempt."""
        if ticket in self._pending:
            self._pending.remove(ticket)
            return True
        return False

    def snapshot(self):
        return {
            'status': 'NATIVE_INVITATION_RECEIPTS_ONLY',
            'core_situation_created': self._core_confirmed,
            'base_situations_created': self._base_cursor,
            'base_situations_required': 8,
            'all_nine_situations_created': (
                self._core_confirmed and self._base_cursor == 8),
            'student_ids_requested': (
                tuple(sid for _, sid in self.manifest['core_assignments'])
                if self._core_confirmed else ()) +
                self.manifest['base_ids'][:self._base_cursor],
            'attendance_verified': False,
            'ea_job_assignment_verified': False,
            'class_8_plus_8_verified': False,
        }
