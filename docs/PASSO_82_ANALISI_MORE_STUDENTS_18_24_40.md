# Passo 82 — Analisi reale dei file ksuihuh More Students 18/24/40

**Data:** 1 novembre 2026. **File caricati dall'utente e analizzati in sola lettura:**
- `ksuihuh_HS_MoreStudents_18.zip`
- `ksuihuh_HS_MoreStudents_24.zip`
- `ksuihuh_HS_MoreStudents_40.zip`
- `ksuihuh_HS_SecondCafeteriaVendor.package`
- `Ksuihuh_HS_NoClubOutfitsForStudents.package`

Le tre ZIP contengono ciascuna 1 file `.package` e 1 `.ts4script`.
I package sono DBPF v2.1, tutte le 19 risorse per ciascuno sono state
estratte e confrontate come XML: **13 snippet tuning** (`0x7DF2169C`)
e **6 SituationJob** (`0x9C07855F`). Si tratta di risorse **EA
esistenti con lo stesso TGI** nelle tre versioni, NON di nuovi menu e
NON di filtri che selezionano i Sim esatti del registro.

## Differenze di capienza reali tra versioni

| Tuning e quantità | More Students 18 | More Students 24 | More Students 40 |
|---|---:|---:|---:|
| WeeklyScheduleDay `long_term_situations/count` (Main, FromVenue, FireDrill, CareerDay) | 13 | 19 | 35 |
| Student1 fase GoToClass1 `WithTrait` / `NoTrait` (max) | 9 | 12 | 20 |
| Student1 fase AttendClass1 `WithTrait` / `NoTrait` (max) | 9 | 12 | 20 |
| Background GoToClass Others — Student1 (max) | 9 | 12 | 20 |
| Background AttendClass Others — Student2 (max) | 9 | **8** | 20 |
| Background Morning/AfterSchool Student1 (max) | 5 | 6 | 15 |
| Background Morning/AfterSchool Student2 (max) | 8 | 8 | 8 |
| Background Morning/AfterSchool Student3 (max) | 6 | 6 | 6 |
| FireDrill NPC Student1 (min-max) | 9–18 | 16–24 | 30–40 |
| CareerDay Student auto-invite (per 3 job, min=max) | 3 | 4 | 10 |
| Prom teen auto-invite (min-max) | 11–14 | 15–25 | 25–35 |
| Graduation attendee auto-invite (min-max) | 6–10 | 8–10 | 10–15 |
| Graduation graduate auto-invite (min-max) | 10–13 | 12–17 | 20–30 |
| Script `ksuihuh_SimLimit.pyc` costante cap | **25** | **33** | **49** |

Questi sono **valori di tuning/configurazione**, non un test in-game:
un upper bound di 9 o 12 non certifica 9 o 12 Sim in aula.

**Osservazioni importanti:**
- Il conteggio 13/19/35 non equivale al numero totale nominale 18/24/40:
  il `WeeklyScheduleDay` coordina le situazioni EA e i job core distinti.
  Non impostare automaticamente il valore a 16 per ottenere 16 iscritti.
- **La versione 24 mantiene `Background_AttendClass_Others`
  Student2 a 8** nonostante le altre fasi vadano a 12; questo dato
  mostra che non è sufficiente modificare un unico parametro di capienza.
- La fase **Student3** di Morning/AfterSchool è una suddivisione EA
  di background, non prova di una terza aula fisica.
- Solo **40** cambia anche il minuto di due eventi di
  `weeklySchedule_HighSchool_Active_FromVenue` da 20 a 15; non
  trasferire questa modifica alla nostra configurazione senza necessità.

## TGI cruciali per gli 8+8

**Situazioni e fasi** da progettare con criterio:
- `277657`: WeeklySchedule_Main
- `279958`: WeeklySchedule_FromVenue
- `280917`: WeeklySchedule_FireDrill
- `282082`: WeeklySchedule_CareerDay
- `293642`, `293644`: NPC GoToClass1 WithTrait/NoTrait
- `304561`, `304563`: NPC AttendClass1 NoTrait/WithTrait
- `297773`: Background GoToClass Others
- `304570`: Background AttendClass Others
- `297171`: Background Morning
- `297583`: Background AfterSchool

Queste `WeeklyScheduleSituationData` **non invitano nuove persone
automaticamente solo perché aumenta il limite**: i loro job chiedono
Sim **già selezionati nelle Base situations EA**, fra cui
`277894` Base NPC Student e le squadre/scuola core.
Le fasi del primo gruppo usano `277919` (Student1),
quelle di Others usano `280777` (Student2).
Inoltre `trait_HighSchool_Active_Class1Student` `293779`
distingue una variante WithTrait/NoTrait: serve validare in-game il
mapping esatto tra registro C1/C2 e aula fisica.

## La parte script

Tutte le versioni hanno un file `.ts4script` ZIP con:
- `ksuihuh_injector.pyc` (1047 byte, identico tra versioni)
- `ksuihuh_SimLimit.pyc` (1528 byte, identico salvo data/ora
  di compilazione e costante numerica 25/33/49).

Entrambi compilati per Python **3.7** (magic `42 0d 0d 0a`).
I nomi simbolici contenuti nel secondo modulo includono
`SimSpawnerService`, `_spawn_next_sim`,
`get_maximum_sims_in_zone`, `set_npc_soft_cap_overrider`,
`MCCC_get_maximum_sims`, `mc_settings`, `HIGH_SCHOOL`,
`AUDITORIUM`. **Inferenza tecnica:** il modulo interviene
sul limite di spawn/presenze del lotto e può coordinarsi/interferire
con un'altra mod che intervenga sulla stessa API. Non è stata
decompilata la logica completa, né provato un conflitto specifico.

## Componenti accessori

### SecondCafeteriaVendor
Una sola risorsa `0x9C07855F:00000035:278010`:
`situationJob_MarketStalls_Vendor_CafeteriaStation_HighSchool`.
`sim_auto_invite` min=max **2**; filtro mensa `300743`.
**Non modifica la selezione degli studenti**; eventuale supporto a più
personale mensa MHS è questione separata.

### NoClubOutfitsForStudents
Sei override `SituationJob` per Base NPC Student (277894)
e ruoli Cheer (278965), Chess (278966), Football (278967),
Computer (278968), Mean Sim (303765). I valori
`sim_auto_invite` qui rimangono **1 per job**.
Cambia comportamento/tuning dei job legati ai vestiti,
**non costruisce né amplia le classi e non sceglie Sim del registro**.
Va controllato con attenzione per futuri conflitti TGI se MHS
modifica gli stessi `SituationJob`.

## Cosa questa analisi RISOLVE e cosa NO

**Risolto tecnicamente:** individuati i GUID di capienza/timetable
che More Students modifica, i job delle fasi (Student1/2), la presenza
di cap runtime e di cambiamenti ai prom/graduation job.

**Ancora non risolto:** selezione dei nomi iscritti MHS, disponibilità
reale dei Sim nei job Base, scelta esatta tra aula 1 e aula 2,
compatibilità con altre mod nel Mac, prom e lezioni alle 14:00.

Il test M79 della build di isolamento ha già dimostrato che EA può
far sedere gli NPC casuali alle 10:00, **non** i 16 selezionati:
non confondere nuova capienza con assegnazione identità.

## Decisione per MY HIGH SCHOOL (prossimo sviluppo)

1. **Fissare la baseline funzionante:** Actions
   [41257486408](https://github.com/iliyanadg/MyHighSchool/actions/runs/41257486408).
   No More Students 18/24/40 installati in parallelo, no override
   indiscriminati dei filtri `SimFilterService` M57/M60.
2. **Capienza originale e minima per C1=8 e C2=8**: confrontare
   la variante 18 (limiti per fase 9/9) con i tuning EA verificati
   e creare un set originale di tuning mirato a 8/8. Distinguere il
   numero di NPC (non giocabili), core e playable: il registro 16
   non equivale a 16 nuovi NPC. Evitare per ora gli override dei
   job prom/graduation e delle fasi non necessarie.
3. **Identità persistenti:** usare registro MHS come fonte unica e
   orientare la selezione **prima** che EA assegni i job base. Il pattern
   Sonozaki Elementary (marcatori di eligibility + injection selettiva)
   è un riferimento concettuale, NON lo stesso filtro Zerbu; i
   GUID del liceo sono altri. Evitare di copiare codice di terzi.
4. **Distribuzione classi:** mappare le fasi job, `293779` e
   i `WithTrait/NoTrait` per assicurare gli stessi Sim
   in Classe 1/2 e non assegnati a caso. Preservare
   insegnanti/principal, eventi EA, lunch e prom.
5. **Prove di non regressione in-game:** prima 10:00 seduti,
   poi C1/C2 roster completo, 14:00, mensa, prom.
   Se il test si rompe, rollback alla M58 isolamento.

**Nessuna build nuova installabile è stata generata da questi file.
Non promettere 16/16 senza verifica in-game.**