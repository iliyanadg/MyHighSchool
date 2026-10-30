# Passo 13 — Revisione delle interazioni M1

**Esito:** struttura generale comparabile con Sonozaki, ma NON validata per avviare The Sims 4 1.129.39.1230. Nessun nuovo package.

## Confronti realmente effettuati
File originali dell'utente: Sonozaki High School Management 2.2.1 (`Choose_Classmates_Class1_SimPicker` e `Restore_All_Cheat_Interaction`), oltre ai tuning EA High School Years originali estratti dal gioco.

**Coincidono nei campi principali:** `SimPickerInteraction`, `actor_continuation`, `picker_dialog`, `sim_tests`, `test_globals`; conferma tramite `ImmediateSuperInteraction` con `outcome/single/actions/basic_extras/notification`.

**Tre punti da controllare prima della build:**
1. M1 usa `sim_info` + `who=PickedSim` per limitare la selezione agli adolescenti; Sonozaki usa invece `filter_test` personalizzato. Non sappiamo ancora se questo test sia supportato esattamente qui.
2. Nelle notifiche M1 compare `title` (`enabled`), non presente nell'esempio Sonozaki. Non dimostra un errore.
3. Nelle notifiche M1 compare `timing` (`at_beginning`), non presente nell'esempio Sonozaki. Non dimostra un errore.

Il builder Lot51 usato dall'utente mostra **TDESC 1.128.90**, mentre il gioco ha versione **1.129.39.1230**. Un confronto con uno schema TDESC aggiornato o un'esportazione/validazione da builder resta necessario.

Aggiunti: `tooling/m1_schema_review.py` e otto test offline. La revisione termina con `NOT_READY_FOR_GAME` apposta: un test statico che passa non è una mod verificata. Non abbiamo modificato la base funzionante v1.6, né incluso tuning EA o Sonozaki in GitHub.

**Prossima operazione:** con il builder e gli esempi EA, verificare questi tre tunable, correggere soltanto incompatibilità confermate e poi compilare una build da controllare prima di qualunque installazione.
