# Passo 53 — M48: una sola spunta conferma, X annulla (31 ottobre 2026)

## Decisione esplicita dell'utente

Dopo M45 (menu completo e visibilità verificati sul Mac), l'utente ha rifiutato il design M47 con due passaggi di conferma e tasto aggiuntivo Annulla. Ha deciso di mantenere lo schema già definito prima della M47:
1. MY HIGH SCHOOL -> Classe 1/2/3 -> Iscrivi studenti (in beta «Prepara iscrizione»)
2. Una finestra nativa di scelta adolescenti; è possibile selezionare più Sim (massimo 8 per classe)
3. **Spunta ✓ della finestra = iscrizione effettiva immediata** nel registro di prova
4. **X della finestra = chiusura senza modifica** del registro
5. Per modifiche successive, usare i comandi separati già presenti Rimuovi studenti e Trasferisci. Nessuna seconda finestra Conferma/Annulla.

## Implementazione M48

- `src/m48_enrollment/mhs48_single_picker.py`: genera `UiSimPicker` nativo con un picker di adolescenti, `max_selectable` configurato fino a 8, legge la selezione completa da `dialog.get_result_tags()` nel callback di accettazione; una singola esecuzione per apertura; su X ritorna senza qualsiasi commit.
- `src/m2_registry/mhs46_enrollment_transaction.py` continua a gestire controllo e scrittura, ma il callback della spunta invoca entrambe `preview_enrollment` (soltanto validazione in memoria) e `confirm_enrollment` (commit) consecutivamente. **Nessuna seconda interazione con l'utente.**
- Validazioni: slot originale, attivazione scuola, Classe 3 opzionale, adolescenti effettivi presenti nel salvataggio, da 1 a 8 ID univoci, esistenti nel picker, fingerprint del registro e limite 8 posti (compresi quelli già occupati), recheck immediatamente prima della scrittura.
- `tooling/build_m48_single_checkmark.py`: esegue la trasformazione sulla M45 verificata nel gioco; soltanto 3 tuning di iscrizione cambiano, **tutte e cinque le categorie e SimData** (da Lot51, con Parent corretto) restano identiche alla M45. Nessuna modifica a rimozioni, consultazioni o trasferimenti.
- La M47 con secondo dialogo è abbandonata e non va installata; M45 resta backup/fallback.
- I test offline `tests/test_m48_one_step_enrollment.py` simulano X, spunta, doppio callback, selezione invalida, commit fallito e preservazione DBPF.

### Stato

**Mac game test non ancora eseguito**, e `UiSimPicker` programmato da Python non è certificato nella versione di gioco 1.129.39.1230. Il fatto che M45 usasse un SimPickerInteraction EA già funzionante non è prova che il nuovo picker programmatico si apra. Testare prima su save TEST; non alterare partita principale o roster originale senza backup.

Solo il registro JSON esterno viene aggiornato (NON assegna gli studenti al liceo EA e NON sincronizza presenze/aule, lavoro successivo).

### Test Mac raccomandato, minimizzando il rischio

1. Con gioco chiuso fare copia della cartella `MY_HIGH_SCHOOL_M25_TEST_DATA` e della coppia M45. Rimuovere solo M45 e inserire un'unica coppia M48 in Mods; non disinstallare altre mod.
2. Aprire il salvataggio di prova, click cassetta -> MY HIGH SCHOOL -> Classe 1 -> Prepara iscrizione. Verificare che appaia un solo picker nativo con adolescenti.
3. Prima prova: selezionare un adolescente e premere **X**. Verificare che Classe 1 -> Consulta iscritti non abbia cambiato elenco.
4. Seconda prova dopo verifica di X: selezionare un adolescente di prova non iscritto e premere **✓**. Verificare notifica e consultazione della classe. Se necessario il salvataggio JSON di prova permette di verificare la scrittura; nessuna seconda finestra dovrebbe comparire.
5. Se il picker non si apre, compare Better Exceptions o il gioco si blocca, fermarsi, chiudere senza salvare e ripristinare M45; fare riferimento al rapporto invece di premere continuamente.
