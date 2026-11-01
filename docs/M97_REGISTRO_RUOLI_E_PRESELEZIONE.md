# M97 — Registro dei cinque ruoli EA e pre-selezione degli iscritti

**Data:** 1 novembre 2026. È stato implementato codice puro
Python 3.7 e test offline nel branch
`feature/m55-presenze-studente-test`. **Non è una release da
installare nel gioco.** M94 rimane la build diagnostica sicura.

## Sorgenti implementate

- `src/m97_core_reservations/mhs97_core_role_store.py`:
  archivio JSON per save-slot `MHS97_RuoliSpeciali_slot_<id>.json`.
  Gestisce cinque assegnazioni manuali `cheer/chess/football/computer/mean`
  con scrittura atomica, controllo versione/fingerprint per modifiche
  concorrenti e nessun rimpiazzo automatico.
- `src/m97_core_reservations/mhs97_early_role_plan.py`:
  blocca il piano quando le due classi non contengono otto Sim
  distinti, uno dei cinque ruoli manca, uno studente non è
  iscritto/idoneo al filtro EA, uno è giocabile nella situazione
  NPC, oppure uno studente ricopre due ruoli.
  Restituisce il conteggio degli NPC Base ancora necessari.
  **Non si auto-attribuisce la qualità di prenotazione EA confermata.**
- `src/m97_core_reservations/mhs97_core_filter_policy.py`:
  traduce i cinque SimFilter EA in un solo ID riservato per ruolo;
  se una richiesta EA esclude quello studente, la politica
  restituisce BLOCK e non una scelta casuale. In casa o in un
  salvataggio non verificato non deve modificare alcun filtro.

## Mappatura verificata dall'utente tramite M94 sul Mac

| Ruolo | EA SituationJob | EA SimFilter |
| --- | --- | --- |
| Cheer | 278965 | 276592 |
| Chess | 278966 | **276596** |
| Football | 278967 | **276594** |
| Computer | 278968 | 276595 |
| Mean Sim | 303765 | 303766 |

EA prevede anche il filtro degli studenti normali:
job `277894` → filter `280516`.
Due insegnanti `277895,278963` **non** sono studenti.

## Esempio rigorosamente illustrativo

Due classi da otto; se due Sim giocabili sono iscritti e
cinque adolescenti distinti del registro vengono selezionati
ed effettivamente prenotati sui cinque ruoli EA,
restano `16 - 2 - 5 = 9` inviti normali.
Non è una misurazione dell'occupazione del save reale.

## Limitazioni prima di una build funzionante

1. Collegare le assegnazioni M97 al menu Sim, con scelta dei cinque
   iscritti e verifica delle loro effettive eligibility in-game.
   Il nuovo archivio **non viene ancora scritto dal gioco**.
2. Installare il vincolo M97 sui filtri SimFilterService **prima**
   dell'avvio mattutino CoreClassNPCs, e bloccare sicuri fallback EA.
3. Produrre un piano di prenotazione atomico per M96, con
   verifica zona reale/slot/giornata/capienza fisica.
4. Coordinare M89/M90 con le restanti richieste Base,
   senza i teenager non iscritti osservati alle 10:03.
5. Verificare in-game 16 presenti e 8 seduti in ciascuna aula,
   senza duplicati, NPC aggiuntivi, o problemi ai prom.

**Questi componenti non vengono installati dalla M94 e
non dichiarano ancora il problema risolto.**
