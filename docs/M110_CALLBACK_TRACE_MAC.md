# M110 — tracciamento opzionale dei callback EA (Mac, NON controller scolastico)

**Stato:** prototipo di diagnostica; test Python offline, gioco ancora NON verificato.
**Ramo:** `feature/m55-presenze-studente-test`. Nessuna modifica a `main`.

## Perché dopo la M109
Il rapporto reale M109 ha confermato 15/15 metodi e sei owner EA. Non ha
misurato QUANDO il gioco chiama i metodi o se le situazioni vengono create.
La M110 osserva tre callback nativi in sequenza: 
- `WeeklyScheduleDay.get_long_term_situation_count`
- `WeeklyScheduleSituationData.try_start`
- `SituationManager.create_situation`.

M110 **non è puramente read-only** come M109: dopo il comando manuale
`mhs110.start` installa temporaneamente **tre wrapper pass-through** in
memoria. Ogni originale EA riceve gli stessi argomenti, viene chiamato una
sola volta e il valore restituito o l'eccezione viene preservato.
`mhs110.stop` ripristina i descrittori originali **solo se i wrapper
M110 sono ancora presenti**, senza sovrascrivere wrapper estranei.
Se EA non permette un'installazione completa, tenta il rollback.
Non prova compatibilità con altre mod script senza marker riconosciuti.

## Limiti e sicurezza
- Avvio solo con comando esplicito; nessun auto-hook caricando il modulo
- Nessun file `.package`, nessuna modifica al registro, agli studenti,
  alle situazioni già esistenti o ai tuning EA
- Il wrapper altera TEMPORANEAMENTE il codice Python in memoria
- Al massimo 256 eventi dettagliati (contatori continuano)
- GUID delle situazioni e conteggi EA, nessun SimID o nome
- Un registro di callback NON dimostra che 16 studenti siano stati assegnati
  né che frequentino lezioni in aule separate
- Eseguire SOLO su COPIA del salvataggio e senza altre beta MHS
- Se il ripristino non è confermato, non fare altri test sulla sessione:
  chiudere il gioco senza salvare e rimuovere lo script

## Compilazione Mac
Job indipendente `m110-native-callback-trace.yml` con Python 3.7:
`python -m unittest tests.test_m110_trace_core tests.test_m110_game_trace -v`
poi `python -m tooling.build_mhs110_trace dist_m110/`. Produzione
`MHS_M110_EA_CALLBACK_TRACE_MAC_TEST.ts4script` con esattamente due
moduli Python 3.7 e istruzioni. Questo esito è SOLO un gate statico.

## Procedura di prova dopo una compilazione verde
1. Eseguire un backup del salvataggio test. Sostituire eventuali script MHS
   sperimentali con il SOLO `.ts4script` M110, nella cartella Mods
2. Partire da casa PRIMA del nuovo giorno scolastico. Aprire la console e
   digitare `mhs110.start`. Se risponde che è bloccato, non proseguire
3. Accompagnare normalmente i Sim a scuola. M110 osserva i tre callback
   senza cambiare gli invitati o i loro job
4. A fine scuola usare `mhs110.stop`. Se il ripristino non viene confermato,
   chiudere il gioco senza salvare
5. Inviare `Documents/Electronic Arts/The Sims 4/
   MY_HIGH_SCHOOL_M25_TEST_DATA/MHS_M110_NATIVE_EA_CALL_TRACE.json`.

Il rapporto deve permettere di capire se e in quale ordine la partita
chiama conteggio delle situazioni, avvio delle lezioni e creazione delle
situazioni. Se un metodo non appare, NON dedurre che il gioco non lo usi
in assoluto: la registrazione potrebbe essere stata avviata troppo tardi.

**Obiettivo successivo:** dopo questa prova, confrontare le richieste
Base/Core e la vera assegnazione Bouncer, mantenendo distinta la semplice
creazione dalla presenza effettiva e dai posti a sedere.
