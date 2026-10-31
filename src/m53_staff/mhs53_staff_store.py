"""MY HIGH SCHOOL M53 — persistent, per-save TEST staff registry (Python 3.7).

Principal: exactly zero/one; teachers: zero/one per Class 1,2,3.
Cafeteria: zero to three; custodians: zero to two.
Only existing, adult Sims selected by the player can be appointed.
No Sim can occupy two staff roles simultaneously. No EA careers, saves,
school attendance, staff NPC services or actors are modified.

This is an EXTERNAL JSON registry and will not follow rollback of EA saves.
"""
import hashlib
import json
import os
import tempfile

from mhs_m2_roster import canonical_save_slot,canonical_sim_id


class StaffError(ValueError):
    pass


KEYS=('principal','teacher1','teacher2','teacher3','cafeteria','custodians')
SINGLE=('principal','teacher1','teacher2','teacher3')
CAP={'principal':1,'teacher1':1,'teacher2':1,'teacher3':1,
     'cafeteria':3,'custodians':2}


def _blank():
    return {'principal':None,'teacher1':None,'teacher2':None,
            'teacher3':None,'cafeteria':[],'custodians':[]}


class StaffRoster(object):
    VERSION=1

    def __init__(self,slot,roles=None):
        self.slot=canonical_save_slot(slot)
        self.roles=_blank()
        if roles is not None:
            if type(roles) is not dict or set(roles)!=set(KEYS):
                raise StaffError('Registro personale incompatibile')
            seen=set()
            for role in KEYS:
                value=roles[role]
                if role in SINGLE:
                    if value is not None:
                        value=canonical_sim_id(value)
                        if value in seen:
                            raise StaffError('Il Sim ha gia un altro ruolo')
                        seen.add(value)
                    self.roles[role]=value
                else:
                    if type(value) is not list or len(value)>CAP[role]:
                        raise StaffError('Numero addetti non valido per '+role)
                    data=[canonical_sim_id(v) for v in value]
                    if len(set(data))!=len(data) or any(v in seen for v in data):
                        raise StaffError('Personale duplicato')
                    seen.update(data)
                    self.roles[role]=data

    def members(self,role):
        if role not in KEYS:
            raise StaffError('Ruolo inesistente')
        value=self.roles[role]
        return (() if value is None else (value,)) if role in SINGLE else tuple(value)

    def all_ids(self):
        return {sim_id for role in KEYS for sim_id in self.members(role)}

    def fingerprint(self):
        return hashlib.sha256(self.to_json().encode('utf-8')).hexdigest()

    def to_dict(self):
        return {'schema':self.VERSION,'slot':self.slot,
                'roles':{role:(list(self.roles[role]) if role not in SINGLE
                               else self.roles[role]) for role in KEYS}}

    def to_json(self):
        return json.dumps(self.to_dict(),sort_keys=True,indent=2)

    @classmethod
    def from_json(cls,blob):
        try:
            parsed=json.loads(blob)
            if (type(parsed) is not dict
                    or set(parsed)!={'schema','slot','roles'}
                    or parsed['schema']!=cls.VERSION):
                raise StaffError('Formato personale sconosciuto')
            return cls(parsed['slot'],parsed['roles'])
        except (KeyError,ValueError,TypeError):
            raise StaffError('Registro personale JSON non valido')


def plan_staff(roster,role,operation,selected,adult_check):
    """Compute an atomic assignment or removal with no input mutation."""
    if not isinstance(roster,StaffRoster) or role not in KEYS:
        raise StaffError('Registro o ruolo non valido')
    if operation not in ('assign','remove'):
        raise StaffError('Operazione personale sconosciuta')
    if type(selected) not in (list,tuple):
        raise StaffError('Selezione non valida')
    ids=tuple(canonical_sim_id(item) for item in selected)
    if not ids or len(ids)!=len(set(ids)):
        raise StaffError('Scegli almeno un Sim, senza duplicati')
    if role in SINGLE and len(ids)!=1:
        raise StaffError('Solo un Sim per questo ruolo')
    before=roster.members(role)
    assignments=roster.to_dict()['roles']
    if operation=='remove':
        if any(item not in before for item in ids):
            raise StaffError('Personale scelto non assegnato al ruolo')
        if role in SINGLE:
            assignments[role]=None
        else:
            assignments[role]=[x for x in assignments[role] if x not in ids]
    else:
        if len(ids)>CAP[role]- (0 if role in SINGLE else len(before)):
            raise StaffError('Limite personale superato per '+role)
        occupied=roster.all_ids()-set(before)
        if any(item in occupied for item in ids):
            raise StaffError('Un Sim scelto ha gia un altro incarico')
        if not callable(adult_check):
            raise StaffError('Verifica eta del Sim indisponibile')
        for sid in ids:
            try:
                if adult_check(sid) is not True:
                    raise StaffError('Seleziona soltanto adulti idonei')
            except StaffError:
                raise
            except Exception:
                raise StaffError('Eta del Sim non verificabile')
        if role in SINGLE:
            assignments[role]=ids[0]
        else:
            assignments[role]=list(before)+list(ids)
    updated=StaffRoster(roster.slot,assignments)
    return updated,{'role':role,'operation':operation,'changed':len(ids),
                    'count':len(updated.members(role)),'limit':CAP[role]}


class StaffStore(object):
    def __init__(self,folder):
        if not folder:
            raise StaffError('Cartella dati personale mancante')
        self.folder=os.path.abspath(folder)

    def path(self,slot):
        return os.path.join(self.folder,
                            'Personale_slot_{}.json'.format(canonical_save_slot(slot)))

    def load(self,slot):
        slot=canonical_save_slot(slot)
        name=self.path(slot)
        if not os.path.exists(name):
            return StaffRoster(slot)
        try:
            with open(name,'r',encoding='utf-8') as f:
                roster=StaffRoster.from_json(f.read())
        except (OSError,UnicodeError):
            raise StaffError('Registro personale illeggibile')
        if roster.slot!=slot:
            raise StaffError('Registro personale di un altro salvataggio')
        return roster

    def save(self,slot,roster):
        slot=canonical_save_slot(slot)
        if not isinstance(roster,StaffRoster) or roster.slot!=slot:
            raise StaffError('Salvataggio personale non valido')
        if self.load(slot).to_json()==roster.to_json():
            return False
        if not os.path.isdir(self.folder):
            os.makedirs(self.folder)
        temp=None
        try:
            fd,temp=tempfile.mkstemp(prefix='.mhs53_',suffix='.tmp',dir=self.folder)
            with os.fdopen(fd,'w',encoding='utf-8') as stream:
                stream.write(roster.to_json())
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temp,self.path(slot))
            temp=None
        finally:
            if temp is not None and os.path.exists(temp):
                os.unlink(temp)
        return True

    def apply(self,slot,role,operation,selected,adult_check,snapshot):
        slot=canonical_save_slot(slot)
        before=self.load(slot)
        if before.fingerprint()!=snapshot:
            raise StaffError('Personale modificato: riapri il menu')
        next_roster,stats=plan_staff(before,role,operation,selected,adult_check)
        self.save(slot,next_roster)
        return stats
