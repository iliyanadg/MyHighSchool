# Passo 74 — Analisi 10 Situation Job originali EA esportati dall'utente (31/10/2026)

## Provenienza e metodo
Archivio `Archivio(1).zip` inviato dall'utente tramite Sims 4 Studio per la sua versione Mac del gioco (GameVersion 1.129.39.1230).
Contiene **10 XML SituationJobTuning** e **10 SimData XML** originali corrispondenti; presenti inoltre 20 file accessori `__MACOSX/._*` (metadata Finder, da ignorare).
La matrice sotto è stata estratta leggendo gli XML effettivamente forniti, senza inventare filtri o considerare l'archivio prova di un'API Python chiamata.

## Collegamenti Situation Job → SimFilter

| Situation Job | ID job | ID filtro | Auto-invite | Gestione assente / morte |
|---|---:|---:|---|---|
| Base NPC Student | 277894 | 280516 | 1–1 | non dichiarata nel job |
| Teacher1 | 277895 | 296396 | 1–1 | REPLACE_THEM / REPLACE_THEM |
| Teacher2 | 278963 | 300741 | 1–1 | REPLACE_THEM / REPLACE_THEM |
| Principal | 278223 | 300742 | 1–1 | REPLACE_THEM / REPLACE_THEM |
| Janitor | 290196 | 300744 | 1–1 | REPLACE_THEM / REPLACE_THEM |
| Cheer Team | 278965 | 276592 | 1–1 | non dichiarata |
| Chess Team | 278966 | 276596 | 1–1 | non dichiarata |
| Football Team | 278967 | 276594 | 1–1 | non dichiarata |
| Computer Team | 278968 | 276595 | 1–1 | non dichiarata |
| Mean Sim | 303765 | 303766 | 1–1 | non dichiarata |

`sim_auto_invite.lower_bound=1` e `upper_bound=1` compare in **tutti e dieci** i job: è un limite del singolo job nella sua situazione, NON il totale di studenti che EA può ospitare in classe o sul lotto. L'auto-invite del job di studenti ordinari **non** significa che il liceo intero inviti un solo studente: occorre studiare quante istanze/contesti creino la situazione.

Negli incarichi Teacher1, Teacher2, Principal, Janitor compare anche `sim_auto_invite_allow_priority=VENUE_REQUIRED`, oltre a `no_show_action=REPLACE_THEM` e `died_or_left_action=REPLACE_THEM`: il comportamento di replacement EA può introdurre soggetti diversi dal registro quando i candidati selezionati non risultano disponibili/idonei. Tutti e dieci gli XML indicano `sim_auto_invite_allow_instanced_sim=True` e condividono gli stessi 3 riferimenti location-based `260612, 290171, 203033`.

## Incrocio con 3 situazioni già fornite
- `situation_HighSchool_Active_NPC_Base_Student` (277733) assegna il job 277894.
- `situation_HighSchool_Active_NPC_Base_CoreClassNPCs` (298052) assegna due docenti e cinque role speciali (Mean, Cheer, Chess, Football, Computer).
- `situation_HighSchool_Active_NPC_Base_VenueNPCs` (298096) assegna preside e janitor.
- Ognuna delle tre situazioni ha `max_participants=20`; **non sommare** come se garantisse 60 Sims.
- La **mensa non è presente** tra questi dieci job e non compare nelle tre situazioni: non inventarne il job ID.

## Incrocio con 7 filtri già forniti
- Filtro docente 296396 valuta `trait_Hidden_HighSchool_NPC_Teacher1` (300380).
- Filtro preside 300742 valuta `trait_Hidden_HighSchool_NPC_Principle` (300487).
- Filtro janitor 300744 valuta `trait_Hidden_HighSchool_NPC_Janitor` (300488).
- Filtro mensa 300743 valuta `trait_Hidden_HighSchool_NPC_CafWorker` (300519).
- Filtro generico faculty 280457 non contiene un tratto specifico di ruolo.
- L'età minima dei filtri faculty è YOUNGADULT.
- Gli eventuali Sim selezionati nel registro MHS non ricevono automaticamente quei trait né ricoprono automaticamente i Situation Job: impostare il solo filtro con un ID può non bastare. Non assegnare trait nascosti indiscriminatamente in una patch sperimentale.

## Conclusione tecnica e passaggio richiesto
M57d ha mostrato 21 invocazioni di filtri liceo ma 0 vincoli applicati; ciò non identifica ancora **la situazione o il momento in cui EA crea l'intera popolazione**. Il job XML dimostra filter/job e replacement, non dice quale hook Python sia sempre chiamato prima dello spawn.

**Prima di cambiare logica M57** richiedere i tuning EA:
1. `situation_HighSchool_Active_Player_Main` 276686
2. `situation_HighSchool_Active_Player_AttendClass` 276681
3. Cercare in Extract Tuning `Cafeteria` / `HighSchool_Active_Cafeteria` per identificare il job reale della mensa (se presente).
Se i primi due ID non restituiscono situazioni, chiedere screenshot della ricerca invece di indovinare.

Nessun codice di terzi copiato; nessuna nuova build M57 o modifica a registri. Mantieni la M57d come diagnostica e M56 come fallback.
