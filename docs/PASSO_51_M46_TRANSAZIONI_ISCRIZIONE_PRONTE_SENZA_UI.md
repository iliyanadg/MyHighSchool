# Passo 51 — M46, motore di iscrizioni con conferma a due fasi (31 ottobre 2026)

## Stato di avanzamento

Il menu M45 è stato verificato funzionante sul Mac, con classi 1/2, 3 opzionale, attivazione e disattivazione. **M45 è la baseline installata e non deve essere sostituita per questo passo.**

È stato aggiunto il nuovo modulo **indipendente dalla UI**:
- `src/m2_registry/mhs46_enrollment_transaction.py`

In attesa di una finestra di conferma nativa, questo modulo implementa due operazioni esplicite:
- `preview_enrollment(store,settings,slot,klass,selected,is_teen)` prepara e verifica l'anteprima senza scrivere su disco;
- `confirm_enrollment(store,settings,slot,plan,is_teen)` salva soltanto dopo una seconda chiamata della futura finestra con consenso esplicito, ricontrollando identità del salvataggio, stato attivo, classe abilitata, fingerprint del registro, identità e idoneità degli adolescenti, capacità di massimo otto.

Controlli: annullamento = nessuna scrittura; scelta non valida = rifiuto; cambio di salvataggio = rifiuto; cambio registro mentre la finestra è aperta = rifiuto; disattivazione di gestione/Classe 3 = rifiuto; 9° studente = rifiuto. Nessuna modifica per una selezione che non cambia iscrizioni. Quando si salva, il file JSON esterno rimane atomico con journal di annullamento dal motore M2.

### Test
- `tests/test_m46_enrollment_transaction.py`: 10 nuovi test.
- GitHub Actions: https://github.com/iliyanadg/MyHighSchool/actions/runs/41206178275 — **success**, suite completa.
- Questa non è una build installabile e non è stata testata all'interno di The Sims 4.

### Lavoro ancora da svolgere prima di chiedere test utente

1. Collegare l'attuale selezione `Prepara iscrizione Classe N` allo stage e a una finestra EA `UiDialogOkCancel` in cui la persona vede quantità e occupazione classe, con due pulsanti Conferma / Annulla e feedback sul risultato.
2. Verificare che l'evento di conferma del SimPicker rappresenti tutto il batch (se la continuazione è una per Sim, non scrivere batch incompleti). Il codice esistente `mhs_m2_selection_probe.py` segnala esplicitamente questa incertezza.
3. Senza modificare categorie, Parent SimData, visibilità M45 o salvataggi esistenti, compilare package + ts4script come coppia sperimentale e fare una prova Mac su save TEST, non sul salvataggio principale.
4. Selezione e salvataggio mentre il gioco è in pausa: verificarlo separatamente; la sola apertura del picker in pausa è già confermata, ma non il commit.

**Alla persona non serve fare nulla adesso.** Conservare M45 e gli attuali file del registro; non premere conferme console finché la versione GUI non è validata.

Non confondere registro JSON esterno con controllo presenze del liceo EA: quello è un lavoro successivo.
