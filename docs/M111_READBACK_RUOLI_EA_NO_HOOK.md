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
gioco**: l'integrazione col manifest del salvataggio e con un contesto
di fase realmente verificato resta da collegare.

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

1. Leggere il `SchoolManifest` effettivo del salvataggio attraverso
   `current_slot(allow_travel=True)`, `RosterStore`, `StaffStore`
   e `SettingsStore` di M54/M57; bloccare i salvataggi con meno di 16
   iscritti senza inventare i mancanti.
2. Verificare tramite EA che ci si trovi realmente al liceo e nella fase
   della lezione, non utilizzare booleane passate a mano nei test.
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

Test offline `tests/test_m111_school_job_readback.py` in Python3.7/3.11;
questi test sono sintetici e non dimostrano che gli NPC siano entrati
realmente a lezione.
