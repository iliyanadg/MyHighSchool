"""M56: pure, session-scoped save identity bridge across EA scratch slots.

Lot51 Core's public Context.save_slot_id uses the EA method
PersistenceService.get_save_slot_proto_guid() precisely because the game
switches to a scratch save during zone travel. A stable GUID alone is not
assumed equal to the *external JSON slot number*. We bind it to an actual
positive proto.slot_id observed in this very Python session and the current
active household. Travel fallback is READ-ONLY / transient attendance only.

Never persist this mapping to disk, never choose a stale slot by default,
and never derive a slot from Sims' names or a save filename.
"""


class IdentityError(ValueError):
    pass


def positive_id(raw):
    if type(raw) not in (str, int):
        return None
    text = str(raw)
    if (not text.isdigit() or int(text) < 1 or
            str(int(text)) != text):
        return None
    return text


def positive_slot(raw):
    sid = positive_id(raw)
    if sid is not None and 1 <= int(sid) < 0xFFFFFFFE:
        return sid
    return None


class TravelSlotGuard(object):
    def __init__(self):
        self.slot = None
        self.stable_guid = None
        self.household_id = None
        self.last_source = 'unbound'

    def reset(self):
        self.slot = self.stable_guid = self.household_id = None
        self.last_source = 'unbound'

    def resolve(self, raw_slot, stable_guid, household_id, allow_travel=False):
        current = positive_slot(raw_slot)
        stable = positive_id(stable_guid)
        household = positive_id(household_id)
        if current is not None:
            # A *real* slot is available: this is the only place where an
            # anchor may be updated. An unverified GUID cannot seed one.
            if stable is not None and household is not None:
                self.slot = current
                self.stable_guid = stable
                self.household_id = household
            else:
                self.reset()
            self.last_source = 'live_proto'
            return current

        if not allow_travel:
            self.last_source = 'blocked_write_scratch'
            raise IdentityError('ID salvataggio temporaneo: modifiche bloccate')

        if (self.slot is None or self.stable_guid is None or
                self.household_id is None):
            self.last_source = 'unverified_school_zone'
            raise IdentityError('Nessun slot verificato prima del viaggio')

        if stable is None:
            self.last_source = 'stable_guid_temporarily_missing'
            raise IdentityError('GUID stabile EA momentaneamente indisponibile')
        if stable != self.stable_guid:
            self.reset()
            self.last_source = 'stable_guid_mismatch'
            raise IdentityError('Identita salvataggio cambiata; nessun registro letto')

        if household is None:
            self.last_source = 'household_temporarily_missing'
            raise IdentityError('Famiglia attiva EA non ancora caricata')
        if household != self.household_id:
            self.reset()
            self.last_source = 'household_mismatch'
            raise IdentityError('Nucleo attivo diverso; nessun registro letto')

        self.last_source = 'verified_zone_travel'
        return self.slot
