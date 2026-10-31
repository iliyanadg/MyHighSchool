# Passo 54 — M49: risolvere il blocco del SimPicker M48 (31 ottobre 2026)

## Errore reale fotografato sul Mac

Dopo l'installazione della M48 nel salvataggio di prova, aprendo `MY HIGH SCHOOL -> Classe ... -> Prepara iscrizione`, il gioco mostra una notifica blu:

```
MY HIGH SCHOOL - IMPOSSIBILE APRIRE
'ImmutableSlots' object has no attribute 'get_max_selectable'
```

**La notifica arriva dal nostro script**, che cattura l'eccezione al tentativo di `UiSimPicker.show_dialog()`. Non è stata provocata dalle altre mod, dal registro o dalla selezione degli adolescenti.

## Causa verificata nel sorgente

`src/m48_enrollment/mhs48_single_picker.py`, funzione `_max_selectable`, costruiva l'oggetto `max_selectable` via `sims4.collections.make_immutable_slots_class` (una tecnica usata in vecchi tutorial del 2015). Il client attuale tenta `max_selectable.get_max_selectable()`; `ImmutableSlots` non espone quel metodo.

Questo specifico `AttributeError` è stato riportato anche per mod aggiornate dopo patch del 2019, dove `ui_dialog_picker.py` chiama `get_max_selectable`: https://db.modthesims.info/showthread.php?chat=1&fromdownload=1&ht=0&page=23&pp=25&t=576053

## Modifica M49

- Usa una classe di strategia **EA nativa** `UiDialogObjectPicker._MaxSelectableUnlimited()` anziché il vecchio `ImmutableSlots`.
- Verifica che l'oggetto abbia il metodo `get_max_selectable`, prima di mostrare il picker.
- **Il limite di otto resta vincolante** nel callback e nei validatori M46/registro: se l'interfaccia EA, col suo strategia nativa `Unlimited`, lascia selezionare più di otto, la spunta rifiuta la selezione e non scrive nulla. Il controllo UI visuale di selezione massima a 8 è ancora da raffinare, usando eventualmente la vera variante EA `static_count` quando si sarà verificata la sua API sulla versione Mac, evitando un'altra struttura creata a tentativi.
- Il comportamento utente resta invariato: **una spunta ✓ = iscrizione**, **X = uscita senza scrivere**, nessun dialogo successivo Conferma/Annulla.
- Il `.package` della M49 è **byte-per-byte identico a M48**, quindi anche le 5 categorie e 5 SimData verificate in M45 sono identiche; solo lo script `.ts4script` è stato ricompilato.

## Verifica

Test `tests/test_m49_picker_strategy.py`: simula la strategia EA con `get_max_selectable`, verifica rifiuto delle varianti non compatibili, verifica che nove Sim scelti non scrivano il registro, verifica che il pacchetto non differisca da M48. Comprende tutti i test M45, M46 e M48.

Workflow: https://github.com/iliyanadg/MyHighSchool/actions/runs/41209647502

**Non dichiarare funzionalità in-game finché l'utente non ha provato la M49 su Mac.**

## Installazione / test

1. Chiudere The Sims 4, conservare copia della M45 funzionante e backup JSON `MY_HIGH_SCHOOL_M25_TEST_DATA`.
2. Rimuovere unicamente i due file M48 dalla cartella Mods; inserire soltanto la coppia M49. Non disinstallare le altre mod.
3. Nella partita di prova, aprire Classe 1 -> Prepara iscrizione.
4. Se si apre il picker, **premere X come prima prova**; controllare «Consulta iscritti» per assicurarsi che il registro non sia cambiato.
5. Poi, se X funziona, si può tentare l'iscrizione di un singolo adolescente *di prova* premendo ✓; la scrittura modifica JSON esterno, anche se non si salva la partita EA. Confermare con «Consulta iscritti».
6. Se compare nuova notifica d'errore, fermarsi, chiudere senza salvare e ripristinare M45; inviare lo screenshot dell'errore, senza fare altre selezioni.

Il registro di iscrizioni non controlla ancora la frequenza effettiva dei Sim presso il liceo di EA.
