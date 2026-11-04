# M115 — Il vero BLANK_FILTER di The Sims 4, 3 novembre 2026

## Fonte originale EA, non ipotesi

Nel file EA `sim_filter_service.py` caricato il 2 novembre 2026
la funzione `_SimFilterRequest.__init__` usa:

```python
if sim_filter is None:
    sim_filter = filters.tunable.TunableSimFilter.BLANK_FILTER
```

In `bouncer.py` dello stesso gruppo di sorgenti originali,
le chiamate a `SimFilterService.submit_matching_filter`
passano `request._sim_filter`, `sim_constraints`,
`request._continue_if_constraints_fail`, blacklist e
`request.get_additional_filter_terms()` separatamente.
Questo conferma la compatibilità di interfaccia con un oggetto
filter nativo. **NON** prova che tutti i 13 NPC richiesti
possano superare ogni blacklist, esclusività, soft cap o job.

La ricerca di un filtro EA generico con GUID inventato è
abbandonata: il motore ha già la costante nativa.

## Cosa abbiamo implementato davvero

`src/m115_filter/mhs115_native_blank_filter.py` carica solo a
runtime `filters.tunable.TunableSimFilter.BLANK_FILTER`
e controlla che sia un oggetto reale con:
- `get_filter_terms()` vuoto;
- `get_additional_conform_terms()` vuoto;
- `is_aggregate_filter() is False`;
- flag `repurpose_game_breaker` di tipo booleano.

In caso di attributi mancanti o struttura inattesa il lettore
blocca l'operazione. Non crea filtri personalizzati, oggetti
tuning o situazioni scolastiche; non cambia la costante EA.

`src/m115_filter/mhs115_native_bouncer_assembly.py` legge anche
l'owner EA `situations.bouncer.bouncer_request.BouncerRequest`
tramite il resolver M114 e prepara una coppia condivisa
`SchoolFilterScope + SchoolNoShowGuard` con l'oggetto EA
nativo. Restituisce uno stato ESPLICITO
`EA_BOUNCER_PAIR_PREPARED_NOT_ACTIVATED`.

Questa preparazione è **sola lettura**: NON chiama gli install
M109/M114, NON installa hook, NON abilita una mod attiva.

## Prove offline

`tests/test_m115_native_blank_filter.py`: sette test.
`tests/test_m115_native_bouncer_assembly.py`: cinque test.
In più regressioni M114/M108.

CI Python3.7 completata con successo:
https://github.com/iliyanadg/MyHighSchool/actions/runs/41686713737

Questi test emulano gli import del gioco. Non sono una prova
del funzionamento reale del motore EA alla prossima patch.

## Gate rimanenti per una beta CORRETTIVA

Il filtro nativo era uno dei blocchi, non l'intera soluzione.
Prima di attivare il controller:
1. Controllare concretamente la provenienza
   richiesta EA `BouncerRequest` e la validità del contesto
   salvataggio/giorno/lotto, prima di ogni modifica.
2. Stabilire la sequenza mattutina a parte dal controllo delle
   lezioni: la richiesta preesistente
   `full_16_school_day_ea_membership_verified` nel modulo
   `mhs108_unified_lessons` è una prova che non può esserci
   PRIMA della convocazione degli NPC. Non aggirarla con True.
3. Installare solo con gate LIVE verificati i moduli
   `native_precreate`, filtro/no-show e
   `post_bouncer_observer`. Registrare rollback EA prima
   di ogni installazione.
4. Dopo l'assegnazione EA leggere i job effettivi dei 13 NPC e
   verificare i 3 adolescenti giocabili. Solo con
   quella ricevuta sbloccare separatamente lezioni e routing.
5. Verificare realmente capienza NPC e blackboard delle
   due classi da 8, senza inventare disponibilità o ruoli.

**Nessuna M115 .ts4script da installare.** `main` resta
inalterato. Tutto su `feature/m55-presenze-studente-test`.
