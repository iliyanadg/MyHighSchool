# Passo 68 — M56 confermata in gioco: slot stabile, scuola rilevata, primo batch

## Evidenza Mac: 31 ottobre 2026, circa 19:45

L'utente ha installato la coppia **M56** compilata con successo da GitHub Actions e ha aperto la partita di prova partendo da casa e poi accompagnando gli adolescenti al liceo di Copperdale.

La finestra "MY HIGH SCHOOL — PRESENZE AUTOMATICHE" mostra (trascritto dallo screenshot originale):

```
Automazione M55: installato
Controlli eseguiti: 17 | SCUOLA_RILEVATA: Piano presenze attivo
Fonte slot: verified_zone_travel | slot verificato: 11 | guid ancorato: si | nucleo ancorato: si
Registro slot 11: C1 8/8, C2 8/8.
Giocabili adolescenti della famiglia: 3.
Non iscritti: 3: Sofia Ogliari, Rosario Lanzafame, Sandro Paoletti
Ultimo evento: GIORNATA_INIZIATA: Iscritti idonei 16 / non idonei 0
Slot 11 / Giorno Sim 10
Iscritti previsti: 16 / convocazioni richieste: 3
Gia in situazione EA: 0 / giocabili: 0
Non idonei: 0 / non trovati: 0 / falliti: 0 / da elaborare: 13
Il gioco EA puo comunque aggiungere NPC suoi. Una richiesta non garantisce che lo studente sia fisicamente presente.
```

Lo screenshot mostra **IN PAUSA** alle circa 8:31, dunque il batch collettivo non è ancora terminato.

## Interpretazione verificata

- **Bug dell'identità slot 0 risolto in M56 per questa partita e questo viaggio**: sorgente `verified_zone_travel`, slot 11, stesso GUID e nucleo. Questo è il primo riscontro reale dal Mac che conferma la lettura del registro corretta sul lotto del liceo.
- **La giornata scolastica viene riconosciuta** dal gate automatico e il planner congela correttamente 16 ID, tutti idonei.
- **Tre richieste inviate** sono chiamate `create_situation` tentate e accettate con un ID EA, **non prova di tre NPC fisicamente arrivati** e nemmeno del loro collocamento nell'aula giusta.
- 13 studenti ancora da elaborare perché il planner esegue batch da 3 per ogni allarme ogni 5 minuti Sim; per completare servono diversi intervalli di gioco effettivamente non in pausa.
- **Tre teen giocabili non iscritti**: Sofia Ogliari, Rosario Lanzafame, Sandro Paoletti. Nessuno viene auto-iscritto; per farli partecipare alle classi controllate occorrono posti entro il limite di 8 TOTALI in ciascuna aula. Se entrano in elenco il gioco li gestisce come playable, non si deve creare una situazione NPC duplicata.
- Non è ancora verificata la presenza fisica di 16 studenti e personale scelto; EA conserva i filtri e ruoli originali.

## Verifica immediata nel salvataggio TEST

1. Togliere la pausa, lasciare scorrere circa 25–35 minuti Sim con velocità normale, senza cambiare nucleo o lotto. Interrompere se il gioco si blocca, causa duplicati, o produce eccezioni.
2. Riaprire il diagnostico: atteso `da elaborare: 0` se il planner riesce a completare. Leggere richieste, presenti, falliti e non idonei; non fare equivalere questi numeri all'arrivo fisico.
3. Contare separatamente gli iscritti visibili nei corridoi o nelle due classi e confrontare con i nomi del registro; raccogliere esempi di non iscritti spontanei EA.
4. Per la M57, intervenire sulla **selezione originale EA prima dello spawn**, non sullo spam di `create_situation`. Filtro già identificato nell'analisi Sonozaki: `filter_HighSchool_Active_Student`, tuning 280516; includere i cinque core roles e il personale.
5. Non modificare ancora i registri o il personale: i dati esistenti sono preservati. Restare in branch separato; M54 su main rimane rollback.

## Stato

`M56_SAVE_IDENTITY_AND_SCHOOL_GATE_CONFIRMED_IN_GAME`; `M56_SCHOOL_ATTENDANCE_NOT_YET_CONFIRMED`; `M57_EA_SELECTION_CONTROLLER_NOT_IMPLEMENTED`.
