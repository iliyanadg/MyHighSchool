"""M97 per-save appointments for five EA high-school student jobs.

EXPLICIT player-owned choices only. Does not auto-fill or invent Sims.
Stores a separate JSON under the MHS test-data folder, not EA save files.
Only the future early school runtime hook may consume these assignments.
"""
import hashlib
import json
import os
import tempfile

ROLE_TO_JOB={
    'cheer':278965,
    'chess':278966,
    'football':278967,
    'computer':278968,
    'mean':303765,
}
ROLES=tuple(ROLE_TO_JOB)

class CoreRosterError(ValueError):
    pass

def _id(raw):
    if type(raw) not in (int,str):
        raise CoreRosterError('Identificativo non valido')
    val=str(raw)
    if not val.isdigit() or int(val)<1 or val!=str(int(val)):
        raise CoreRosterError('Identificativo non valido')
    return val

class CoreRoleRoster(object):
    VERSION=1

    def __init__(self,slot,roles=None):
        self.slot=_id(slot)
        if roles is None:
            roles={r:None for r in ROLES}
        if type(roles) is not dict or set(roles)!=set(ROLES):
            raise CoreRosterError('Mappa dei cinque ruoli incompleta')
        normalized={r:(_id(roles[r]) if roles[r] is not None else None)
                    for r in ROLES}
        chosen=[v for v in normalized.values() if v is not None]
        if len(chosen)!=len(set(chosen)):
            raise CoreRosterError('Uno studente non puo occupare due ruoli')
        self.roles=normalized

    def chosen(self):
        return {ROLE_TO_JOB[r]:self.roles[r] for r in ROLES
                if self.roles[r] is not None}

    @property
    def complete(self):
        return all(self.roles[r] is not None for r in ROLES)

    def to_dict(self):
        return {'schema':self.VERSION,'slot':self.slot,
                'roles':dict(self.roles)}

    def to_json(self):
        return json.dumps(self.to_dict(),sort_keys=True,indent=2)

    def fingerprint(self):
        return hashlib.sha256(self.to_json().encode('utf-8')).hexdigest()

    @classmethod
    def from_json(cls,raw):
        try:
            data=json.loads(raw)
            if (type(data) is not dict or
                    set(data)!=set(('schema','slot','roles')) or
                    data['schema']!=cls.VERSION):
                raise CoreRosterError('Formato ruoli speciali sconosciuto')
            return cls(data['slot'],data['roles'])
        except (ValueError,TypeError,KeyError):
            raise CoreRosterError('Archivio ruoli speciali non valido')

def plan_change(current,role,student_id,enrolled_ids,eligible_for_job,
                verified_school_reg=True):
    """Return new roster, never alter existing one.

    student_id=None removes an appointment; no automatic replacement.
    enrolled_ids is the live roster; eligible_for_job(job_id,sim_id)
    is a CURRENT game age/species/filter check, not just an ID presence check.
    """
    if not isinstance(current,CoreRoleRoster) or role not in ROLE_TO_JOB:
        raise CoreRosterError('Ruolo scolastico non valido')
    if verified_school_reg is not True:
        raise CoreRosterError('Registro iscritti non verificato')
    proposed=dict(current.roles)
    if student_id is None:
        proposed[role]=None
    else:
        sid=_id(student_id)
        if not isinstance(enrolled_ids,(tuple,list,set,frozenset)):
            raise CoreRosterError('Elenco degli iscritti mancante')
        if sid not in set(_id(x) for x in enrolled_ids):
            raise CoreRosterError('Seleziona soltanto studenti iscritti')
        if not callable(eligible_for_job):
            raise CoreRosterError('Filtro EA non disponibile')
        try:
            if eligible_for_job(ROLE_TO_JOB[role],int(sid)) is not True:
                raise CoreRosterError('Studente non idoneo al ruolo EA')
        except CoreRosterError:
            raise
        except Exception:
            raise CoreRosterError('Verifica filtro EA fallita')
        if sid in [v for k,v in current.roles.items() if k!=role]:
            raise CoreRosterError('Studente gia assegnato a un ruolo')
        proposed[role]=sid
    return CoreRoleRoster(current.slot,proposed)

class CoreRoleStore(object):
    def __init__(self,folder):
        if not folder:
            raise CoreRosterError('Cartella MHS mancante')
        self.folder=os.path.abspath(folder)

    def path(self,slot):
        return os.path.join(self.folder,
            'MHS97_RuoliSpeciali_slot_{}.json'.format(_id(slot)))

    def load(self,slot):
        slot=_id(slot)
        name=self.path(slot)
        if not os.path.exists(name):
            return CoreRoleRoster(slot)
        try:
            with open(name,'r',encoding='utf-8') as stream:
                result=CoreRoleRoster.from_json(stream.read())
        except (OSError,UnicodeError):
            raise CoreRosterError('Archivio ruoli speciali illeggibile')
        if result.slot!=slot:
            raise CoreRosterError('Archivio ruoli speciali di altro salvataggio')
        return result

    def save(self,slot,planned,expected_fingerprint):
        """Optimistic concurrency: no stale UI action overwrites new roles."""
        slot=_id(slot)
        if not isinstance(planned,CoreRoleRoster) or planned.slot!=slot:
            raise CoreRosterError('Ruoli destinati ad altro salvataggio')
        current=self.load(slot)
        if expected_fingerprint!=current.fingerprint():
            raise CoreRosterError('Ruoli modificati: riaprire il menu')
        if planned.to_json()==current.to_json():
            return False
        os.makedirs(self.folder,exist_ok=True)
        temp=None
        try:
            fd,temp=tempfile.mkstemp(
                prefix='.mhs97_',suffix='.tmp',dir=self.folder)
            with os.fdopen(fd,'w',encoding='utf-8') as stream:
                stream.write(planned.to_json())
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temp,self.path(slot))
            temp=None
        finally:
            if temp is not None and os.path.exists(temp):
                os.unlink(temp)
        return True
