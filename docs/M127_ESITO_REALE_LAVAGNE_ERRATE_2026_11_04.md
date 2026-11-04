# M127 — Risultato effettivo nel gioco (4 novembre 2026)

Fonte: `MHS_M127_ORARI_PERCORSI_EA.json` inviato dall'utente.

## Orari originali EA verificati

- 09:30:00 — tre chiamate di creazione preparazione: 293815, 304701, 297774. I due percorsi 293815/304701 sono alternativi della Classe 1, non due aule differenti.
- 10:00:00 — creazione lezioni EA 304565 (Classe 1) e 304567 (Classe 2).
- 09:40 e 09:55 — job lezione 0/16; alle 10:05 job lezione 16/16, corretti secondo il registro.

## Evidenza nuova: bersaglio errato della lavagna prima delle 10

**Lavagna A** (bersaglio di sette iscritti Classe 1): `568605179473013957`.

**Lavagna B** (bersaglio di cinque iscritti Classe 2): `568605179473014101`.

Due iscritti della **Classe 2** puntano invece alla **Lavagna A**, benché gli altri studenti Classe 2 puntino a B:

- SimID `568605179472946205`: 09:40, `super_HighSchool_Active_AttendClass_NPC`, bersaglio Lavagna A; 09:55, `mixer_HighSchool_Active_UsePhone`, bersaglio Lavagna A.
- SimID `568605179488204115`: 09:40, `super_HighSchool_Active_Whiteboard_Attend_Art`, bersaglio Lavagna A; 09:55 `mixer_HighSchool_Active_UsePhone`, bersaglio Lavagna A.

La classe del registro non determina ancora esclusivamente il bersaglio della lavagna. La lettura dei job 16/16 alle 10:05 non rileva questo errore.

## Posture e avvio della lezione

- 09:40: Classe 1 quattro `posture_Sit`, Classe 2 uno.
- 09:55: Classe 1 quattro `posture_Sit`, Classe 2 cinque.
- 10:05: Classe 1 otto `posture_Sit`, Classe 2 sette.

**Queste sono posture, non prove della seduta nel banco della classe corretta.** Uno studente della Classe 1 (`568605179485058376`) ha `sit_Passive`, bersaglio `object_chair_dining`, alle 09:40, 09:55 e 10:05. Uno della Classe 2 (`568605179484009778`) ha `stand_Passive` e `posture_Stand` a tutti e tre gli orari.

## Conclusione tecnica e prossimo intervento M128

La preparazione **esiste già dalle 09:30** e due studenti Classe 2 hanno una destinazione di lavagna diversa da quella usata dai compagni di classe. Prima di anticipare qualunque clock EA, intervenire sulla **scelta / test di bersaglio lavagna nelle interazioni native di preparazione**, con mappatura stabile lavagna Classe 1 / lavagna Classe 2, e gestire i tre adolescenti giocabili senza imporre routing su azioni protette. Non confondere posture `Sit` con banco corretto.

La M128 dovrà:
1. identificare l'API originale EA che sceglie il `target` per `super_HighSchool_Active_AttendClass_NPC`;
2. restringere solo i bersagli delle lavagne per gli iscritti, senza annullare l'interazione del Sim, alterare la timetable o riassegnare le situazioni;
3. mantenere fallback originale se non è possibile distinguere in modo affidabile le due lavagne;
4. registrare bersaglio e banco effettivo prima delle 10 e verificare fisicamente 8+8, assenza di errori e continuità nei giorni successivi.

Non dichiarare M127 correzione della puntualità o M128 già funzionante.
