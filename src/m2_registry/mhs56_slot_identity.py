"""M56/M160: strict EA slot identity, including validated persistent continuity.

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


def stable_token(raw):
    """Treat EA save GUID as an opaque identifier; never parse as slot index."""
    if raw is None or isinstance(raw, bool):
        return None
    value = str(raw).strip()
    if (not value or len(value) > 128 or
            value.lower() in ('0', '0x0', 'none', 'null')):
        return None
    return value


def positive_slot(raw):
    sid = positive_id(raw)
    if sid is not None and 1 <= int(sid) < 0xFFFFFFFE:
        return sid
    return None


def synthetic_slot_for_guid(raw):
    """Reserved high-range store key for a stable EA Save ID.

    No file can be selected by filename or the temporary EA slot number.
    A synthetic key is used only after validating/copying the exact live
    2x8 roster into a new, isolated four-file MHS data set.
    """
    import hashlib
    stable=stable_token(raw)
    if stable is None:
        return None
    bits=int(hashlib.sha256(
        ('MHS-GUID-STORE-v1:' + stable).encode('utf-8')).hexdigest()[:8],16)
    return str(0x80000000 + (bits % 0x7FFFFFFE))


class TravelSlotGuard(object):
    def __init__(self):
        self.slot = None
        self.stable_guid = None
        self.household_id = None
        self.last_source = 'unbound'

    def reset(self):
        self.slot = self.stable_guid = self.household_id = None
        self.last_source = 'unbound'

    def resolve(self, raw_slot, stable_guid, household_id, allow_travel=False,
                verified_home_write=False):
        current = positive_slot(raw_slot)
        stable = stable_token(stable_guid)
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

        # Only the caller can verify that a live, already armed controller
        # belongs to the same HOME session. A scratch ID alone is never a
        # writable identity, including at first startup or after Save As.
        if not allow_travel and not verified_home_write:
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
            if verified_home_write:
                # Same already verified save GUID and active HOME controller:
                # changing played household does not create a new EA save.
                # This is not permitted on a cold start or at school.
                self.household_id = household
            else:
                self.reset()
                self.last_source = 'household_mismatch'
                raise IdentityError('Nucleo attivo diverso; nessun registro letto')

        self.last_source = ('verified_home_write' if verified_home_write and
                            not allow_travel else 'verified_zone_travel')
        return self.slot


class VerifiedSlotBindings(object):
    """Cache only actual EA slot/GUID observations, never infer a slot.

    Cache collisions after Save As remain ambiguous. No unrelated save may
    inherit students based on a matching household or file name.
    """
    VERSION=1

    def __init__(self, path):
        self.path=path

    def _load(self):
        import os
        import json
        if not os.path.isfile(self.path) or os.path.islink(self.path):
            return ()
        try:
            if os.path.getsize(self.path)>65536:
                return ()
            with open(self.path, 'r', encoding='utf-8') as handle:
                obj=json.load(handle)
            if (type(obj) is not dict or set(obj)!=set(('version','bindings'))
                    or obj['version']!=self.VERSION
                    or type(obj['bindings']) is not list
                    or len(obj['bindings'])>256):
                return ()
            result=[]
            for item in obj['bindings']:
                if (type(item) is not dict or
                        set(item)!=set(('guid','slot','household')) or
                        stable_token(item['guid'])!=item['guid'] or
                        positive_slot(item['slot'])!=item['slot'] or
                        positive_id(item['household'])!=item['household']):
                    return ()
                result.append(item)
            return tuple(result)
        except (OSError, ValueError, TypeError, UnicodeError):
            return ()

    def unique(self, guid, household):
        """Return a slot only if an exact GUID+household maps to one slot."""
        guid=stable_token(guid)
        household=positive_id(household)
        if guid is None or household is None:
            return None
        matches=set(item['slot'] for item in self._load()
                    if item['guid']==guid and item['household']==household)
        return next(iter(matches)) if len(matches)==1 else None

    def has_identity(self, guid, household):
        guid=stable_token(guid)
        household=positive_id(household)
        return any(item['guid']==guid and item['household']==household
                   for item in self._load())

    def remember(self, slot, guid, household):
        """Durably store only a live EA slot after caller validates its roster."""
        import os
        import json
        import tempfile
        slot=positive_slot(slot)
        guid=stable_token(guid)
        household=positive_id(household)
        if slot is None or guid is None or household is None:
            return False
        previous=list(self._load())
        new={'slot':slot,'guid':guid,'household':household}
        if new in previous:
            return True
        if len(previous)>=256:
            return False
        previous.append(new)
        folder=os.path.dirname(os.path.abspath(self.path))
        try:
            if not os.path.isdir(folder):
                os.makedirs(folder)
            if os.path.islink(self.path):
                return False
            fd,temp=tempfile.mkstemp(prefix='.mhs_verified_',suffix='.tmp',
                                     dir=folder)
            try:
                with os.fdopen(fd,'w',encoding='utf-8') as out:
                    json.dump({'version':self.VERSION,'bindings':previous},
                              out,sort_keys=True,indent=2)
                    out.flush()
                    os.fsync(out.fileno())
                os.replace(temp,self.path)
            finally:
                if os.path.exists(temp):
                    os.unlink(temp)
        except OSError:
            return False
        return True
