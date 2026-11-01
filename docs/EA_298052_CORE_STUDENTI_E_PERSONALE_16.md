# EA 298052 — CoreClassNPCs: identità, conteggio e convocazione 16 studenti

Fonte: XML originale del gioco caricato dall'utente il 1 novembre 2026,
salvato in `assets/ea_2026_11_01/298052.xml`. Analisi esatta del tuning,
non validazione in gioco.

## Cosa definisce la situazione

La situazione 298052 è `CustomStatesSituation`, con
`max_participants=20`. La sua `default_job_and_roles` include:

| Job EA | Ruolo | Conteggiare nei 16 studenti? |
| --- | --- | --- |
| 277895 | Teacher1 | NO, personale |
| 278963 | Teacher2 | NO, personale |
| 278965 | CheerTeam | SÌ, solo se occupato da iscritto |
| 278966 | ChessTeam | SÌ, solo se occupato da iscritto |
| 278967 | FootballTeam | SÌ, solo se occupato da iscritto |
| 278968 | ComputerTeam | SÌ, solo se occupato da iscritto |
| 303765 | MeanSim | SÌ, solo se occupato da iscritto |

Il blocco `_situation_states / NoBehavior / job_and_role_changes`
include i due insegnanti e quattro ruoli studenti; MeanSim 303765
è nel default ma non in quell'elenco. **Non concludere** che EA
spawni sempre esattamente cinque studenti speciali o esattamente
due docenti: il tuning elenca ruoli, non prove di presenza.

## Regola vincolante 8 + 8 = 16

Per ciascun salvataggio e giornata scolastica, dopo aver verificato
identità degli occupanti EA dei ruoli:

`base_student_da_convocare = 16 - teen_giocabili_iscritti - teen_speciali_iscritti`

Tutti i gruppi devono essere disgiunti, tutti gli studenti speciali
presenti devono essere nel registro, nessun docente si conta come
studente. Se EA ha assegnato un ruolo speciale a un Sim NON iscritto,
non fingiamo che la scuola sia già corretta: stato BLOCKED.

Esempio **ipotetico**: 2 giocabili + 3 speciali verificati +
11 studenti ordinari = 16. Non è una misura del salvataggio reale.

`src/m92_full_roster/mhs92_atomic_16.py` ora gestisce e convalida
la mappa `core_role_jobs` di job EA -> Sim ID e produce
`base_invites_needed`; `src/m90_selection/mhs90_m89_bridge.py`
richiede `core_jobs_verified=True` e che la sessione escluda
correttamente core e giocabili **prima di installare l'hook**.
Non indovina automaticamente una mappa dal file XML.

## Ancora non risolto nel runtime

1. Determinare e controllare i ruoli reali di CoreClassNPCs
   **prima** che EA scelga NPC casuali: la prova statica non è sufficiente.
2. Verificare la zona e l'identità del salvataggio alla creazione
   della situazione EA Base prima del primo spawn (07:00).
3. Evitare che il `WeeklyScheduleDay` a max 16 crei richieste
   base supplementari dopo che gli iscritti NPC sono stati assegnati.
4. Confermare idoneità effettiva SimFilter e cap reale della zona.
5. Testare tutti 16 fisicamente presenti, aula assegnata e 10:00/14:00,
   senza prom e personale corrotti.

Il pacchetto M85+capienza compilato è **ancora beta non pronta per
sostituire M85**: gli override di capacità sono controllati offline,
ma lo script live di convocazione dei 16 non è integrato né validato.
