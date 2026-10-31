"""MY HIGH SCHOOL M34 — isolated, per-save configuration (Python 3.7).

This is NOT an EA attendance controller. Disabling the prototype prevents
custom register writes only when all writers use require_management.
The original saved game and the separately stored class roster are not edited.
"""
import json
import os
import tempfile
from mhs_m2_roster import canonical_save_slot, SchoolRoster


class SettingsError(ValueError):
    pass


class SchoolSettings(object):
    VERSION=1

    def __init__(self, slot, active=False, class_count=2):
        self.slot=canonical_save_slot(slot)
        if type(active) is not bool:
            raise SettingsError('Attivazione non valida')
        if type(class_count) is not int or class_count not in (2,3):
            raise SettingsError('Numero di classi non valido')
        self.active=active
        self.class_count=class_count

    def to_dict(self):
        return {'schema':self.VERSION,'slot':self.slot,
                'active':self.active,'class_count':self.class_count}

    def to_json(self):
        return json.dumps(self.to_dict(),sort_keys=True,indent=2)

    @classmethod
    def from_json(cls,content):
        try:
            obj=json.loads(content)
            if type(obj) is not dict or set(obj)!={
                    'schema','slot','active','class_count'} or type(obj['schema']) is not int or obj['schema']!=cls.VERSION:
                raise SettingsError('Struttura impostazioni non valida')
            return cls(obj['slot'],obj['active'],obj['class_count'])
        except (KeyError, ValueError, TypeError) as exc:
            raise SettingsError('Impostazioni danneggiate o non supportate')


class SettingsStore(object):
    def __init__(self,folder):
        if not folder:
            raise SettingsError('Percorso impostazioni non disponibile')
        self.folder=os.path.abspath(folder)

    def path(self,slot):
        return os.path.join(self.folder,'Impostazioni_slot_{}.json'.format(
            canonical_save_slot(slot)))

    def load(self,slot):
        slot=canonical_save_slot(slot)
        name=self.path(slot)
        if not os.path.isfile(name):
            # First setup is explicitly inactive; classroom 3 opt-in.
            return SchoolSettings(slot)
        try:
            with open(name,'r',encoding='utf-8') as fh:
                value=SchoolSettings.from_json(fh.read())
        except (OSError, UnicodeError) as exc:
            raise SettingsError('Impossibile leggere le impostazioni')
        if value.slot!=slot:
            raise SettingsError('Impostazioni appartenenti a un altro salvataggio')
        return value

    def save(self,settings):
        if not isinstance(settings,SchoolSettings):
            raise SettingsError('Impostazioni non valide')
        old=self.load(settings.slot)
        if old.to_json()==settings.to_json() and os.path.isfile(self.path(settings.slot)):
            return False
        try:
            if not os.path.isdir(self.folder):
                os.makedirs(self.folder)
            fd,temp=tempfile.mkstemp(dir=self.folder,prefix='.mhs34_',suffix='.tmp')
            try:
                with os.fdopen(fd,'w',encoding='utf-8') as handle:
                    handle.write(settings.to_json())
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(temp,self.path(settings.slot))
            finally:
                if os.path.exists(temp):
                    os.unlink(temp)
        except OSError:
            raise SettingsError('Impostazioni non salvate: errore disco')
        return True

    def set_active(self,slot,active):
        if type(active) is not bool:
            raise SettingsError('Attivazione non valida')
        state=self.load(slot)
        updated=SchoolSettings(slot,active,state.class_count)
        self.save(updated)
        return updated

    def set_class_count(self,slot,count,roster):
        if not isinstance(roster,SchoolRoster) or roster.slot!=canonical_save_slot(slot):
            raise SettingsError('Il registro appartiene a un altro salvataggio')
        if type(count) is not int or count not in (2,3):
            raise SettingsError('Scegli 2 o 3 classi')
        if count==2 and roster.class_members(3):
            raise SettingsError('Classe 3 contiene {} studenti: trasferiscili o ritirali prima di passare a 2 classi'.format(
                len(roster.class_members(3))))
        state=self.load(slot)
        updated=SchoolSettings(slot,state.active,count)
        self.save(updated)
        return updated

    def require_management(self,slot,klass=None):
        settings=self.load(slot)
        if not settings.active:
            raise SettingsError('MY HIGH SCHOOL disattivata. Attivala nelle impostazioni')
        if klass is not None:
            if type(klass) is not int or klass not in (1,2,3):
                raise SettingsError('Classe non valida')
            if klass>settings.class_count:
                raise SettingsError('Classe 3 disattivata. Scegli 3 classi nelle impostazioni')
        return settings


def require_m34_management(folder,slot,klass=None):
    return SettingsStore(folder).require_management(slot,klass)
