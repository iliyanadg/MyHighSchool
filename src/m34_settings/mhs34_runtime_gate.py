"""Write guard injected only into M34 bundled runtime, not legacy M33.

All roster updates (enrollment, removal, swap, cleanup, transfer)
flow through RosterStore.save, so checking at this shared boundary
prevents a write when custom register management is disabled.
"""
from mhs34_settings import SettingsStore, SettingsError


def validate_roster_write(folder,slot,before,after):
    config=SettingsStore(folder).require_management(slot)
    if (config.class_count==2 and after.class_members(3)):
        raise SettingsError('Classe 3 disattivata: non posso scrivere un registro che la utilizza')
    if before.slot!=after.slot:
        raise SettingsError('Salvataggio cambiato')
    return True
