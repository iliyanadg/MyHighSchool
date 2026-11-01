# MHS SCUOLA.zip — verifica dei SituationJob EA originali

Provenienza: ZIP caricato dall'utente il 1 novembre 2026.
Cartelle principali presenti: `Sim Data/` (4 XML) e
`Situation Job Tuning/` (**4 XML veri**, prefisso `9C07855F`).
I file macOS `__MACOSX/` sono metadati, non tuning.

## Tuning validi ricevuti

| Job | Ruolo | Filtro EA esatto | sim_auto_invite min-max | allow instanced |
| --- | --- | --- | --- | --- |
| 277894 | Studente Base | 280516 | 1–1 | True |
| 278965 | Cheer | 276592 | 1–1 | True |
| 278968 | Computer | 276595 | 1–1 | True |
| 303765 | MeanSim | 303766 | 1–1 | True |

Verificato tramite parsing dei quattro XML `SituationJob`,
non inferito dalla vicinanza dei numeri o dalla SimData.
Il file `src/m93_core/mhs93_verified_jobs.py` salva tali
valori e lascia INDETERMINATI gli altri due filtri.

## Mancano solo due veri Tuning

- **278966**: `situation_job/job_HighSchool_Active_Base_NPC_Student_ChessTeam`.
- **278967**: `situation_job/job_HighSchool_Active_Base_NPC_Student_FootballTeam`.

Per esportarli: aprire Sims 4 Studio > Tools > Extract Tuning,
selezionare i due risultati con questi nomi e usare Export
con **Use Subfolders** attivo. Inviare SOLO i due XML nella
cartella `Situation Job Tuning` con prefisso `9C07855F!`;
quelli `545AC67A!` sono SimData già analizzati.

## Interpretazione tecnica

Per ciascuno dei quattro job EA, il minimo e il massimo degli
inviti automatici sono entrambi 1. Questo **non** dimostra quali
Sim concreti vengano selezionati né quanti membri dei 16
risultino presenti: la scelta passa per il filtro EA del job.

Non dobbiamo disabilitare senza prova le funzionalità EA di
sport/club, né avviare situazioni aggiuntive per riempire
i 16 posti. Il problema che rimane è sostituire in sicurezza
la selezione dei Sim per le situazioni EA *esistenti*, rispettando
questi filtri, il salvataggio, le presenze giocabili e il limite
fisico di popolazione.

**Nessuna build M85 installata è stata cambiata in questa verifica.**
Questi quattro tuning non autorizzano dichiarazioni di successo
in-game delle 16 presenze o delle due aule.
