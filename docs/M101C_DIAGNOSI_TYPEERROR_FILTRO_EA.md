# M101c — errore reale del filtro scolastico EA

## Osservazione del 2 novembre 2026, salva slot 11
Nel test M101b alle 10:16, il comando `mhs101.check` ha restituito
`SKIPPED_NO_VERIFIED_EA_BASE_FILTER_MATCH`, con il JSON:

```json
{
  "phase":"SKIPPED_NO_VERIFIED_EA_BASE_FILTER_MATCH",
  "filter_guid":280516,
  "filter_diagnostic":{
    "phase":"EA_FILTER_QUERY_EXCEPTION",
    "exception_type":"TypeError",
    "candidate_count":13,
    "eligible_count":0,
    "requested_filter_guid":280516
  },
  "full_roster_controlled":false
}
```

**Un `TypeError` non indica che tutti i 13 studenti siano esclusi.**
Significa che il codice ha sollevato un'eccezione durante la chiamata
all'API EA. Non è possibile stabilire da quel report quale keyword,
tipo di dato o chiamata interna abbia causato l'eccezione.

## Correzione diagnostica M101c

- Mantiene solo l'aggancio a uno slot originale del calendario
  `WeeklyScheduleDay`; non genera situazioni aggiuntive.
- Il report `MHS_M101_UNO_SLOT_EA.json`, nel campo
  `filter_diagnostic`, registra adesso:
  - `exception_message`: il testo sintetico dell'eccezione, max 300 caratteri;
  - `exception_location`: nome file, funzione e riga dell'ultimo frame;
  - `method_signature` (se Python la rende leggibile);
  - `method_name`, `method_module` e `service_type`.
- Se il filtro non restituisce candidati verificati, il codice
  lascia inalterata la convocazione EA.
- Al massimo una interrogazione sperimentale del filtro per
  armamento/giornata, anche quando EA crea più situazioni.
- Mantiene il registro da due classi, 8+8, con 3 giocabili
  e 13 NPC; **non** garantisce ancora la presenza dei 13 NPC.
- Ogni versione si installa **in alternativa** alle altre:
  non usare M101c insieme a M101, M101b, M99 o M94.

## Prova su copia del salvataggio
1. Chiudere The Sims 4, conservare una copia del salvataggio.
2. Sostituire la coppia precedente con i soli due file M101c
   `.package` e `.ts4script`.
3. Nuovo giorno scolastico, a casa: `mhs101.arm`.
4. Viaggiare al liceo con Rosario, Sandro e Sofia.
5. Alle 10:00: `mhs101.check`.
6. Inviare `MHS_M101_UNO_SLOT_EA.json`, dal percorso
   `Documents/Electronic Arts/The Sims 4/MY_HIGH_SCHOOL_M25_TEST_DATA/`.

Con l'esatto testo del TypeError si potrà correggere
l'argomento dell'API, senza supposizioni sul contenuto
del filtro, e verificare con EA il successivo candidato.
