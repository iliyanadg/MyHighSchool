# M95 — Evidenza dalla prova reale in liceo, ore 10:03

**Fonte:** screenshot e tre JSON esportati dall'utente al liceo
(1 novembre 2026; mercoledì in-game alle 10:03).

## Misure acquisite

- **MHS registro:** 16 iscritti (2 classi da 8).
- **M85 presenti sul lotto:** 3 iscritti, distribuiti 1 in C1 e 2 in C2.
- **M85 in situazioni scolastiche EA:** 3 iscritti, **8 teen non iscritti**
  in situazioni scolastiche; 11 teen totali, non 16 registrati.
- **M58 create_situation osservato:** 3 chiamate per il Base Student
  EA situazione 277733, una per CoreClassNPCs 298052, una
  venue-staff 298096 e una cafeteria 278011. **Nessun guest esplicito**
  nelle guest lists di tali richieste. `error=none`.
- **M59 osserva chiamate ad alcuni filtri scolastici**
  (`280516=6`, ogni filtro core=2); questo NON equivale al numero
  di Sim spawnati e NON attribuisce uno specifico ruolo a un Sim.
- **M94 tuning:** tutti e sei i filtri EA letti (Chess 276596,
  Football 276594, non invertire).
- La seduta nell'aula corretta non è verificata.

**Interpretazione:** i log dimostrano che le richieste originali EA non
trasportano le identità degli iscritti MHS e che il salvataggio osservato
ha 13 studenti registrati assenti e 8 teen estranei nella scuola.
NON dimostrano che i 3 registrati presenti siano tutti giocabili,
né che siano sempre 5 i Core occupant effettivi: la guest-list
Core 298052 parte vuota, e le identità vengono assegnate dopo
la chiamata di creazione.

## Correzione protocollo M89/M90 (non ancora integrata nel gioco)

Dopo la verifica completa del lotto, slot, giornaliera, eleggibilità,
capienza e ruoli:
- Con una richiesta Base 277733 vuota, assegnare un Sim registrato
  idoneo nel **medesimo** `create_situation`, non creare situazioni extra.
- Se non rimane alcun iscritto Base idoneo, il dispatcher verificato
  blocca la richiesta Base priva di guest invece di delegare una
  convocazione casuale a EA. L'opzione `on_exhausted` è rigorosamente
  opt-in e non usata dalla M94.
- Anche questo non può creare 16 presenze quando EA ha emesso
  solo 3 situazioni Base: la programmazione di quante richieste
  ammettere è un problema distinto.
- Le cinque posizioni core dei team/MeanSim devono essere
  attribuite ad iscritti univoci **prima** della selezione EA.
  Senza prova della loro eleggibilità e della capienza in gioco,
  il dispatcher deve rimanere disattivato.
- Non è verificato se un `None` del manager venga tollerato da
  tutte le chiamate del `WeeklyScheduleDay`: questa politica
  è per ora sottoposta a **soli test offline**.

## Condizioni per un reale rilascio 8+8

1. Prova di tutte le 16 identità del registro, inclusi core e giocabili.
2. Numero deterministico di inviti Base necessario per arrivare a 16,
   coordinato con Core e giocabili, senza fallback casuale.
3. Assegnazione alle classi: 8 presenti in C1, 8 in C2, entrambi
   docenti assegnati e lezioni effettive.
4. Nessuna persona in più nelle situazioni scolastiche tra gli adolescenti.
5. Test di nessuna regressione con mensa, eventi e prom.
6. Uso solo su copia di salvataggio fino alla verifica in game.

**La M94 è read-only, nulla è stato alterato nel salvataggio
dell'utente da questa analisi.**
