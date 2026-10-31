"""M46 preview/commit engine for a future native enrollment confirmation dialog.

This module is game-independent and intentionally does not show dialogs,
call cheats, or modify the official EA school attendance. It guards the
external test JSON and will be called only AFTER a real user confirms a
specific preview in a future UI integration.

No write on preview/cancel; save only on a second, explicitly confirmed
call with the same class, selection, active save slot and roster fingerprint.
"""
import hashlib
from mhs_m2_roster import canonical_save_slot, RosterError


class EnrollmentTransactionError(ValueError):
    pass


def roster_fingerprint(roster):
    return hashlib.sha256(roster.to_json().encode('utf-8')).hexdigest()


def preview_enrollment(store, settings, slot, klass, selected, is_teen, only_new=False):
    """Validate the entire batch and calculate a read-only confirmation summary."""
    slot=canonical_save_slot(slot)
    settings.require_management(slot,klass)
    roster=store.load(slot)
    if only_new:
        from mhs_m2_roster import canonical_sim_id
        if any(canonical_sim_id(sim_id) in roster.assignments
               for sim_id in selected):
            raise EnrollmentTransactionError(
                'Uno studente risulta gia iscritto: usa Rimuovi o Trasferisci')
    updated,stats=roster.assign_many(klass,selected,is_teen)
    chosen=tuple(sorted((str(sim_id) for sim_id in selected),key=int))
    return {
        'slot':slot,
        'only_new':bool(only_new),
        'class':klass,
        'selected':chosen,
        'snapshot':roster_fingerprint(roster),
        'selected_count':stats['selected'],
        'changed':stats['changed'],
        'moved':stats['moved'],
        'already_in_class':stats['already_in_class'],
        'class_size':stats['class_size'],
        'remaining':8-stats['class_size'],
    }


def confirm_enrollment(store,settings,slot,plan,is_teen):
    """Commit only when user accepted a freshly validated preview.

    The UI must invoke this exclusively from the accepted callback of a
    native Yes/No dialog; opening a picker or dialog is not permission.
    """
    slot=canonical_save_slot(slot)
    if not isinstance(plan,dict):
        raise EnrollmentTransactionError('Conferma mancante')
    if plan.get('slot')!=slot:
        raise EnrollmentTransactionError('La partita e cambiata: nessuna iscrizione')
    klass=plan.get('class')
    selected=plan.get('selected')
    if type(klass) is not int or klass not in (1,2,3):
        raise EnrollmentTransactionError('Classe non valida')
    if not isinstance(selected,tuple) or not 1<=len(selected)<=8:
        raise EnrollmentTransactionError('Selezione non valida')
    settings.require_management(slot,klass)
    roster=store.load(slot)
    if roster_fingerprint(roster)!=plan.get('snapshot'):
        raise EnrollmentTransactionError('Registro modificato dopo anteprima: ripeti selezione')
    if plan.get('only_new',False):
        from mhs_m2_roster import canonical_sim_id
        if any(canonical_sim_id(sim_id) in roster.assignments
               for sim_id in selected):
            raise EnrollmentTransactionError(
                'Studente iscritto nel frattempo: nessuna modifica')
    proposed,stats=roster.assign_many(klass,selected,is_teen)
    # Do not trust UI state or a stale preview. The full preflight counts
    # must be the same immediately before the write.
    keys=('selected_count','changed','moved','already_in_class','class_size')
    values=(stats['selected'],stats['changed'],stats['moved'],
            stats['already_in_class'],stats['class_size'])
    if any(plan.get(key)!=value for key,value in zip(keys,values)):
        raise EnrollmentTransactionError('Anteprima scaduta: ripeti selezione')
    if stats['changed']:
        store.save(slot,proposed)
    return {
        'slot':slot,
        'class':klass,
        'changed':stats['changed'],
        'moved':stats['moved'],
        'class_size':stats['class_size'],
        'selected':stats['selected'],
        'written':bool(stats['changed']),
    }
