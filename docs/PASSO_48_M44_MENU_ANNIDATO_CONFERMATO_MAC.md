# Passo 48 — M44 ANNNIDAMENTO FUNZIONANTE NEL GIOCO (31 ottobre 2026)

## Risultato confermato su The Sims 4 macOS

La creatrice ha installato `MHS_M44_MENU_ANNIDATO_LOT51_TEST.package` e `.ts4script` e ha fornito cinque screenshot del menu della cassetta postale alle 13:54-13:55.

Nelle schermate il ramo `MY HIGH SCHOOL...` mostra ora effettivamente **quattro sottomenu all'interno** della categoria radice, insieme a `Disattiva MY HIGH SCHOOL`:
- `Classe 1...`
- `Classe 2...`
- `Classe 3...`
- `Impostazioni...`

La navigazione nelle singole classi mostra:
- Classe 1: `Prepara iscrizione Classe 1`, `Consulta iscritti - Classe 1`, `Rimuovi studenti - Classe 1`, `Classe 1 - Trasferisci in Classe 2`, `Classe 1 - Trasferisci in Classe 3`.
- Classe 2: le quattro operazioni corrispondenti e i trasferimenti verso classi 1 e 3.
- Classe 3: le quattro operazioni corrispondenti e i trasferimenti verso classi 1 e 2.
- Impostazioni: `Disabilita Classe 3`, coerente con 3 classi attualmente abilitate.

Gli screenshot **non mostrano il loop di Better Exceptions** riscontrato nelle versioni precedenti. I popup visibili nell'ultimo test sono di avvio di altre mod (LLamafone, Iconic, Better Exceptions welcome), non segnalazioni di una nuova eccezione MHS. Non si può quindi dichiarare assenza assoluta di eccezioni nel log, ma il test visivo del menu ha avuto successo.

### Conferma della causa tecnica

La differenza cruciale fra M43 e M44 era nelle quattro SimData dei figli della radice: M43 inseriva manualmente `_parent` come uint64 little-endian nella metà BASSA, mentre le esportazioni reali di Lot51 usano una reference con valore nella metà ALTA del campo da 64 bit. M44 copia integralmente la SimData rigenerata di ciascuna categoria. La M44 dimostra nel client che quel differenziale è efficace: le categorie sono annidate correttamente.

**Non ricostruire né cambiare gli ID/category XML/SimData di M44 senza una regressione controllata.** Conservare M44 come baseline UI funzionante.

### Piccoli test restanti, solo sulla partita di prova e senza modificare gli iscritti

1. `Impostazioni -> Disabilita Classe 3`: la Classe 3 e tutti i trasferimenti con Classe 3 devono diventare invisibili. Poi `Abilita Classe 3` e verificare ripristino.
2. `Disattiva MY HIGH SCHOOL`: il menu deve offrire solo `Attiva`; poi riattivare. Verificare nel gioco e dopo riavvio che le opzioni seguano i JSON persistenti. Le impostazioni scrivono nei file esterni anche se il gioco non è salvato.
3. Mettere in pausa e selezionare `Consulta iscritti - Classe 1`. Verificare se il picker appare e se si completa in pausa: sappiamo dal codice che `ImmediateSuperInteraction` può non completare finché il tempo non scorre.

Non testare ancora rimozione/trasferimento di studenti senza backup. Se una prova cambia il registro, fare il confronto sul file JSON di prova; il salvataggio EA non controlla rollback del JSON.

### Separare correttamente gli obiettivi futuri

L'annidamento dei menu **è risolto e provato in-game**. La mod NON è ancora un gestore scolastico completo: restano selezione e conferma con UI nativa senza console/cheat, gestione dei comandi a gioco in pausa, iscrizioni persistenti in tutte le condizioni, e soprattutto controllo vero della frequenza e delle aule di High School Years. Non presentare il menu come prova che gli studenti compariranno autonomamente a scuola.

Risultati e diagnosi precedenti: `docs/PASSO_47_M44_BUILD_CON_EXPORT_REAL_LOT51.md`.
