# Passo 76 — Mappa dei tuning EA originali (Archivio(2).zip, 31/10/2026)

## Fonte
L'utente ha esportato tramite Sims 4 Studio **1067 XML effettivi** associati a `HighSchool_Active` nel proprio The Sims 4 Mac v`1.129.39.1230`. L'archivio contiene inoltre **1067 file `__MACOSX/._*`** (metadati Mac, non risorse EA): sono stati ignorati. L'archivio include `zoneDirector`, `weeklySchedule`, `situationSet`, `situationData`, `SituationTuning`, `SituationJobTuning`, ruoli e test. Non servono ulteriori esportazioni generali del liceo per questa fase.

## Struttura verificata: chi avvia la giornata
- `zoneDirector_HighSchool_Active_School_FromCareerEvent` **277656** seleziona la `weeklySchedule_HighSchool_Active_Main` **277657** (e varianti Fire Drill, Career Day).
- `zoneDirector_HighSchool_Active_School_FromVenue` **278623** seleziona `weeklySchedule_HighSchool_Active_FromVenue` **279958**.
- **Entrambi i WeeklySchedule** definiscono queste situazioni di lunga durata, ciascuna dalle **7:00 alle 18:00**:
  - `situation_HighSchool_Active_NPC_Base_Student` **277733**, con `count.lower_bound=6` e `count.upper_bound=6` **per il numero di situazioni** e modificatori legati ai sim della famiglia/alla carriera scolastica: non significa garantire esattamente 6 NPC visibili.
  - `situation_HighSchool_Active_NPC_Base_CoreClassNPCs` **298052**, contiene jobs di due insegnanti + cheer/chess/football/computer/mean.
  - `situation_HighSchool_Active_NPC_Base_VenueNPCs` **298096**, contiene preside e bidello.
  - **La mensa è trovata**: `situation_Vendor_CafeteriaStation_HighSchool` **278011**, menzionata direttamente dal WeeklySchedule. Il suo XML non compare nel presente archivio perché il nome non contiene la stringa `HighSchool_Active`; **non cercare più invano un `job_HighSchool_Active_Cafeteria`**.

## Sequenza normale del programma da Zone Director
I due schedule differiscono in alcune varianti (`FromVenue` ha anche avvio mattutino 8:00). Questi sono i passaggi chiave comuni:
- 09:30 `situationSet_HighSchool_Active_GetReadyForClass` **284553**;
- 10:00 `situationSet_HighSchool_Active_AttendClass` **277899** oppure `AttendClass_FromVenue` **285610**;
- 11:00 `situationSet_HighSchool_Active_Lunch` **277901** oppure `Lunch_FromVenue` **285614**;
- 13:30 preparazione alla seconda lezione;
- 14:00 lezione pomeridiana;
- 14:55 attività finali (condizionali).

## Assegnazioni ai job di fase (non auto-invite)
I 5 job documentati nel passo 75 hanno tutti `filter=15940` (vuoto) e `sim_auto_invite=0–0`; **sono assegnati via `situationData` della pianificazione**, non servono a creare nuovi alunni:
- `situationData_HighSchool_Active_NPC_AttendClass1_WithTrait` **304563**: `job=277919`, `sim_count=0..6`, seleziona chi è già in uno fra i sei Base Student/Core jobs **e** ha il trait **293779** `Class1Student`. Riduzione capienza per `Player_AttendClass` **276681**.
- `situationData_HighSchool_Active_NPC_AttendClass1_NoTrait` **304561**: seleziona quei Base/Core jobs senza obbligo del trait, `sim_count=0..6`, con riduzioni per giocabili e per gli iscritti già assegnati alla prima situazione.
- `situationData_HighSchool_Active_Background_AttendClass_Others` **304570**: `job=280777` studenti `sim_count=0..8`, `job=277918` insegnanti `sim_count=0..2`, più preside; verifica preventivamente Base Student/Core jobs e Base Teacher jobs, quindi **riutilizza personaggi già coinvolti nelle situazioni base**.
- `situationData_HighSchool_Active_NPC_GoToClass1_WithTrait` **293642** e `_NoTrait` **293644** hanno schema analogo `0..6` per studenti esistenti, con eventuale tratto Class1Student.
- `situationData_HighSchool_Active_Background_GoToClass_Others` **297773** ha studenti `0..8` e docenti `0..2`.
- `situationData_HighSchool_Active_Background_Morning` **297171** usa **tre job di fase** per studenti: Student1 **0..2**, Student2 **0..3**, Student3 **0..2**; questi sono gruppi di comportamento mattutino, **NON tre aule fisiche**. Consente anche docenti e preside provenienti dalle situazioni base.
- `situation_HighSchool_Active_Background_AttendClass1` **304565** attribuisce a Student1 il role state **276361**; `situation_HighSchool_Active_Background_AttendClass_Others` **304567** attribuisce a Student2 il role **304569**, a Teacher1 il role **295881** e al preside **295880**.
- La separazione dei giocabili già confermata: `situation_HighSchool_Active_Player_Main` **276686** e `Player_AttendClass` **276681**.

## Cosa spiega per MY HIGH SCHOOL
1. **La M57d con 35.653 chiamate SimFilter, 21 scolastiche e 0 vincoli applicati non interviene nel vero percorso completo di selezione/assegnazione**, almeno nella prova corrente. Il filtro `280516` è un input di un Base Student Job; assegnare un SimID al registro non aggiunge automaticamente le **situazioni base** necessarie, né lo assegna alle fasi.
2. **La selezione degli studenti non è un singolo filtro**: il WeeklySchedule crea fino a 6 situazioni base (soggette a modificatori), una core, una venue e una mensa; le situazioni delle fasi riusano i job base e impongono propri massimi 0..6, 0..8. Questo spiega perché una classe da otto nel nostro registro non corrisponde automaticamente a un'aula realmente popolata da otto NPC.
3. **Student3 non è la terza classe**: esiste nei gruppi comportamentali del mattino con `0..2`; non usarlo per provare una terza lavagna/aula.
4. **La mensa è stata trovata** nel `WeeklySchedule` con ID 278011; eventuale studio futuro del vendor va richiesto separatamente per nome esatto, ma non blocca la mappa della classe.
5. Il trait Class1Student in fase è usato come selettore; non attribuirlo indiscriminatamente ai giocabili o NPC perché può rompere altri comportamenti; la scelta della classe MHS deve essere integrata nel routing delle fasi e negli stati delle lavagne.
6. La chiave tecnica per una M58 è passare dal solo hook `SimFilterService` alla progettazione **Schedule → situazione base → job originario → situazioneData della fase → role state / lavagna**, con preservazione dei 5 ruoli Core, dei giocabili, dell'orario vanilla e del tetto 8 iscritti per aula **senza presumere che EA supporti 16 NPC con un solo cambio di count**.
7. L'implementazione richiede prove graduate, safety guard e rollback e **non è stata ancora scritta**; la presente fase è solo analisi del tuning esportato dal gioco. Conservare `main` M54 e M57d di diagnostica sul ramo prova.

## Nuovo materiale da chiedere?
**Nessuno**, per ora. L'archivio è sufficiente per progettare il prossimo intervento senza ulteriori esportazioni generaliste. Se nel codice si rilevano riferimenti non presenti in `Archivio(2).zip`, chiedere **un solo nome/ID esatto** alla volta, dopo aver completato la mappa dei 1067 file.
