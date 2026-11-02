# M101 — Primo esperimento con UNO slot studente originale EA

## Perché non ripetere M61/M99

M99 sul salvataggio 11 ha registrato **14 misurazioni**:
una situazione EA Base 277733 rimaneva attiva e con
**Baby Ariel nella guest list**, ma Baby Ariel non veniva
materializzata sul lotto. La richiesta era stata fatta
a lezione già iniziata, con una **situazione aggiuntiva**.

Nel vero codice EA `weekly_schedule_zone_director.py`,
`WeeklyScheduleDay.start_long_term_situation` crea le
situazioni studenti originali con guest list vuota ma
**`spawn_sims_during_zone_spin_up=True`**, e trasmette
anche `duration_override` e `creation_source`.
Questi attributi NON erano presenti nel comando M61 aggiuntivo.

## Strategia M101 (beta sperimentale, NON ancora testata in-game)

- Non crea **alcuna situazione aggiuntiva**.
- Richiede un esplicito `mhs101.arm`, eseguito **prima**
  di viaggiare al liceo in un nuovo giorno scolastico.
- Riconosce solo le chiamate originali
  `WeeklyScheduleDay.start_long_term_situation` per EA
  Situation **277733**, con guest list vuota, opzioni di
  spin-up originali e `user_facing=False`.
- Legge il **salvataggio corrente** e due classi da 8,
  escludendo Rosario, Sandro e Sofia quando giocabili.
- Consulta il servizio EA `submit_filter`, usando soltanto
  il filtro Base Student **280516**, limitato agli NPC
  già iscritti. Accetta solo risultati reali con `SimInfo`
  e punteggio filtro positivo; se l'API è incompatibile,
  non restituisce candidati e NON modifica EA.
- Usa la M100 per scegliere **al massimo un** candidato
  eleggibile, non ancora sul lotto. La M89 modifica solo
  la guest list della **STESSA** chiamata originale EA,
  senza modificare `spawn_sims_during_zone_spin_up`,
  `duration_override` o altri argomenti.
- Tutto è opt-in e volatile: l'arma non sopravvive al
  riavvio e non parte in altri salvataggi, zone, o giorni.
- Report stato:
  `MY_HIGH_SCHOOL_M25_TEST_DATA/MHS_M101_UNO_SLOT_EA.json`.
- Comandi `mhs101.arm` e `mhs101.check`.

### Istruzioni SOLO dopo verifica build Mac

1. Usare una **copia del salvataggio**.
2. Chiudere il gioco e togliere i due file M99; installare
   soltanto la nuova coppia `MHS_M101_UNO_SLOT_EA_MAC_TEST`
   di .package e .ts4script.
3. Aprire la famiglia **a casa**, la mattina di una
   nuova giornata scolastica, prima di accompagnare
   i giocabili a Copperdale.
4. Console: `mhs101.arm`. Se compare `BLOCCATA`,
   fermarsi; non provare comandi di spawn.
5. Viaggiare normalmente al liceo con i giocabili
   nella **stessa** giornata scolastica.
6. Dopo l'inizio della lezione:
   `mhs101.check`; salvare il report.
7. Mandare `MHS_M101_UNO_SLOT_EA.json` e il nuovo
   `MHS_M85_PRESENZE_RUOLI_EA.json`, per confrontare
   il candidato con le presenze reali.

**Limiti importanti:**
- La M101 non è ancora provata nel gioco; la disponibilità
  e la risposta di `SimFilterService.submit_filter` sono
  specifiche della build installata. Se non restituisce
  risultati positivi, il programma lascia agire EA.
- Il sorgente `mhs101_original_slot_runtime.py` deve
  essere importato prima delle creazioni EA del nuovo
  giorno, e l'armamento deve rimanere valido durante
  il viaggio. In caso contrario, niente override.
- Essere nella guest list di una situazione non prova
  partecipazione, arrivo o presenza in aula.
- Un esperimento con un posto originale non garantisce
  un sistema di **16 studenti presenti, 8 per classe**.
- Il salvataggio normale va mantenuto al sicuro,
  e la M99 rimane quella da usare finché non si
  dispone di una build M101 verificata.

## Sorgenti

- `src/m101_original_slot/mhs101_original_slot_gate.py`
- `src/m101_original_slot/mhs101_original_slot_runtime.py`
- `src/m100_precreate/mhs100_one_slot_policy.py`
- `src/m89_selection/mhs89_precreate_hook.py`
- `tooling/build_mhs101_one_slot.py`
