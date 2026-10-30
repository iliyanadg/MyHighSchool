# Passo 14 — Risolti i tre dubbi sui pattern XML (senza build)

**Risultato:** tutti e tre i pattern M1 discussi nel Passo 13 sono presenti
in esempi reali recuperati dall'utente. Non erano errori dimostrati e
**non li modifichiamo per imitazione**.

## 1. Test adolescente `sim_info + who=PickedSim`

Nel package Sonozaki 2.2.1 analizzato è presente **in sette**
interazioni `SimPickerInteraction` distinte per rimuovere studenti da
classe, scacchi, informatica, football e altre attività.

Esempio identificabile: `SonozakiSisters_Remove_Classmates_Class1_SimPicker`,
estratto dall'archivio dell'utente come
`067_E882D22F_96A485BF53CA73F8.xml`.

Struttura: `<V t="sim_info"><U n="sim_info">...`
con `ages: TEEN` e `<E n="who">PickedSim</E>`.

Questo è **un pattern realmente usato in un SimPicker**, non una soluzione
inventata per M1. Non garantisce tuttavia che il picker mostri ogni teen
giocabile: ciò richiede prova separata.

## 2. Titolo della notifica

Nel tuning EA 1.129
`immediate_HighSchool_Active_CheckClassSchedule.InteractionTuning.xml`
(instance `0x475A1`) è presente `notification/dialog/single/literal/title`
con `t="enabled"`. Anche M1 imposta questo campo nella notifica.

## 3. Tempistica della notifica

Nel tuning EA 1.129
`mixer_Social_Fight_HighSchool_Active_SchoolFight.InteractionTuning.xml`
(instance `0x45105`) è presente
`notification/timing` con `t="at_beginning"`. Anche M1 imposta questo
campo nella notifica.

## Materiale conservato e limiti

I riferimenti sono stati verificati nei **file originali forniti dall'utente**
(`MY_HIGH_SCHOOL_PROGETTO.zip` e `SONOZAKI_ANALISI.zip`), senza
ricopiare tuning EA o Sonozaki su GitHub.

I test aggiornati in `tooling/m1_schema_review.py` richiedono la presenza
di questi tre pattern nei nostri XML.

Il sito Lot51 Tuning Builder mostrava TDESC **1.128.90** per un gioco
**1.129.39.1230**. Non abbiamo ancora verificato tutti gli altri
tunable dei picker/conferme, la lista reale dei candidati, l'iniezione nella
cassetta postale e l'avvio del gioco.

**Stato:** `PATTERNS_SUPPORTED_NOT_GAME_VALIDATED`; nessun nuovo file
da installare, nessuna modifica alla v1.6.

**Prossimo passo:** creare e controllare offline una build completa e
isolata che contenga categoria/SimData di Lot51, due interazioni picker,
conferme, STBL e injector, con blocco di rilascio se mancano risorse o
si verificano collegamenti errati. Nessuna installazione automatica.
