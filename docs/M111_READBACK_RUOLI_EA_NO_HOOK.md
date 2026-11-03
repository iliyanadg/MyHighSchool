# M111 — lettura dei job EA, senza nuovi hook

**Fonte:** tracciato reale M110 del 3 novembre 2026, 356/356 eventi,
`get_situations_sim_is_in(sim)` del manager EA già studiato in M105,
`BaseSituation.get_current_job_for_sim(sim)` trovato in M109 (15/15).

## Risultato implementato

`src/m111_bouncer/mhs111_school_job_readback.py` aggiunge
`observe_school_job_memberships(manifest, manager, sim_infos, teen_age,
human_species, phase)`, una funzione **di sola lettura** che:

- carica la selezione completa di **2 classi da 8**, senza aggiungere
  automaticamente adolescenti giocabili ai 16 posti;
- osserva ogni adolescente umano istanziato (non gli animali o adulti);
- legge le situazioni EA originali di cui è membro tramite
  `get_situations_sim_is_in` (non crea nessuna situazione);
- legge l'attuale `SituationJob` usando
  `get_current_job_for_sim` e il suo `guid64`;
- tratta le vie WithTrait e NoTrait come **una sola Classe 1**;
- interpreta il job 277919 della preparazione Classe 2 per GUID
  situazione, non come Classe 1;
- individua membri mancanti, NPC estranei, classi sbagliate,
  job incompatibili, doppi ingressi, errori API e campioni incompleti;
- restituisce un rapporto utilizzabile dalla riconciliazione M108,
  ma mantiene `post_bouncer_barrier_verified=false`,
  `exact_16_native_membership_verified=false`,
  `two_classroom_seating_verified=false`.

La funzione non modifica il lotto, non muove i Sim, non chiama i
filtri EA e non attiva patch automatiche. **Non è ancora un comando nel
gioco**.

Aggiunto anche `src/m111_bouncer/mhs111_live_school_bridge.py`:
`inspect_current_school_ea_jobs(phase)` rilegge il registro, il personale
e le impostazioni dal salvataggio reale (`current_slot(allow_travel=True)`),
verifica le due classi complete, il calendario EA
`277657` o `279958` del lotto e passa il vero
`SituationManager` a M111. Rifiuta gli altri lotti e i registri
incompleti prima di cercare i job.

Il nuovo ponte è un modulo di integrazione, **non ancora incluso in una
beta installabile**. La fase `prepare`/`lesson` deve essere letta e
verificata dal chiamante prima di considerarne attendibile il risultato:
un input artificiale non dimostra che il gioco sia in quella fase.
Nessuna modifica alla partita, nessuna chiamata al Bouncer per forzare
nuovi Sim.

## Contratto native situation / student job

| Situation EA | Fase | Classe MHS | Job studente |
|---|---|---|---|
| 293815 | prepare | 1 WithTrait | 277919 |
| 304701 | prepare | 1 NoTrait | 277919 |
| 297774 | prepare | 2 | 277919 |
| 304565 | lesson | 1 WithTrait | 277919 |
| 304703 | lesson | 1 NoTrait | 277919 |
| 304567 | lesson | 2 | 280777 |

Base 277733 e Core 298052 sono osservati separatamente e non sono
automaticamente contati come studenti seduti in una classe.

## Limiti da risolvere per l'integrazione reale

1. **Implementato nel bridge, da validare in gioco:** leggere il
   `SchoolManifest` effettivo tramite `current_slot(allow_travel=True)`,
   `RosterStore`, `StaffStore`, `SettingsStore` e verificare il
   calendario originale del liceo. Registri incompleti sono bloccati.
2. **Manca:** ricavare e verificare automaticamente la finestra
   prepare/lesson del giorno reale, non fidarsi di una stringa fittizia.
3. Eseguire il readback **dopo** una barriera Bouncer indipendente:
   `on_all_sims_spawned_during_zone_spin_up` vale solo al caricamento
   del lotto, non garantisce l'assegnazione tardiva delle lezioni.
4. Solo dopo confrontare il risultato con `mhs108_post_bouncer_audit`
   e `mhs108_16_student_reconciliation` per autorizzare le presenze.
5. L'appartenenza EA a una SituationJob **non** verifica il routing a un
   banco o la seduta in aula.

Non chiedere di ripetere M110: la sua prova sul calendario e sulle
chiamate `create_situation` è già conclusa. La prossima prova nel
gioco, quando necessaria, deve mirare esclusivamente al readback di
membership/ruoli EA, non ai callback del calendario.

Test offline `tests/test_m111_school_job_readback.py` e
`tests/test_m111_live_school_bridge.py` in Python3.7/3.11;
questi test sono sintetici e non dimostrano che gli NPC siano entrati
realmente a lezione.

## Prima diagnostica M111 installabile (solo lettura, nessun .package)

È stato preparato un **artefatto separato e opt-in** per Python 3.7
che include i dieci moduli necessari (registro M54/M57, personale,
identità slot, lettura dei veri job EA). Il file si chiamerà
`MHS_M111_EA_JOB_READ_ONLY_MAC_TEST.ts4script`.

Comandi:
- `mhs111.arm` da casa prima di andare al liceo: ancora slot e giorno,
  nessuna modifica ai metodi EA.
- `mhs111.check` al liceo durante una lezione: confronta i Sim
  effettivamente istanziati, i job EA e le due classi da otto; crea
  `MHS_M111_NATIVE_SCHOOL_JOB_READBACK.json` dentro
  `MY_HIGH_SCHOOL_M25_TEST_DATA`.
- `mhs111.status` per leggere solo lo stato, senza effetto sul gioco.

Non esiste comando stop: nessun wrapper viene installato.
Non installare altre beta MHS nello stesso test. Usare solo una
**copia del salvataggio** e non cancellare i vecchi registri M54
con gli iscritti. I rapporti contengono gli ID dei Sim scelti:
condividere solo se desiderato.

**Importantissimo:** il comando controlla l'appartenenza ad una
SituationJob, non la seduta a un banco. La fase `lesson` viene
indicata dall'utente eseguendo `check`, non da una prova esterna
che il Bouncer abbia finito la transizione. Il report ha sempre
`post_bouncer_barrier_verified=false` e
`exact_16_native_membership_verified=false`, anche se tutte le
identità e job letti combaciano.

Il bridge registra inoltre soltanto lo stato osservato del flag
EA `SituationManager._sim_assignment_complete` dopo lo spin-up:
un valore true non prova che siano conclusi gli assegnamenti delle
lezioni delle 10 o 14.

La build Mac è affidata al workflow
`.github/workflows/m111-native-ea-jobs-readonly.yml`.
**Superare i test automatici non equivale a un test nel gioco**.
Non installare fino a build confermata.
