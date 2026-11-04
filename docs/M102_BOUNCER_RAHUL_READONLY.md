# M102 — Invito accettato, Sim non apparso: esame Bouncer in sola lettura

## Prove già ottenute, non ripetere le versioni precedenti

M99: Baby Ariel invitata in una situazione aggiuntiva EA e non
comparsa sul lotto.

M101d: una situazione **originale** del calendario EA (tuning
277733, ID `81653491850477856`) è stata creata con **Rahul Chopra**
della Classe 1, da una lista di **12 risultati EA verificati** dei 13
NPC iscritti. La guest list EA include Rahul, ma:
- `situation_lookup=FOUND`;
- `situation_active=true`;
- `on_lot=false` anche verso le 10:53;
- `situation_member_ids=null`;
- `in_school_situation=null`.

Non confondere `situation_member_ids=null` con una lista vuota:
significa che l'API di lettura usata dalla M99 non era disponibile.
**L'invito e la presenza in situazione sono due cose distinte.**

## Perché M102

M101d ha verificato il filtro, la guest list e la creazione EA. Non
ha ancora verificato la consegna della richiesta al **Bouncer**,
che coordina richieste di partecipazione, assegnazioni e comparsa
fisica dei Sims. Non sappiamo se la causa sia un conflitto di
richieste, un limite del lotto, lo stato del Sim o altro.

M102 conserva tutto il comportamento opt-in di M101d:
- NON aggiunge alcuna situazione e NON cambia i filtri;
- NON forza la comparsa di Sim e non modifica richieste Bouncer;
- mantiene un solo tentativo su una chiamata originale EA, attivato
  manualmente con `mhs101.arm` prima del viaggio a scuola;
- sostituisce soltanto il diagnostico quando si esegue
  `mhs101.check`, aggiungendo `latest_verification.bouncer_probe`
  al file `MHS_M101_UNO_SLOT_EA.json`.

Il probe prova a osservare attributi di richiesta e stato della
situazione, del SituationManager e, **solo se esposto dalle API
della versione del gioco**, del Bouncer. Registra gli attributi
effettivamente visibili e un campione limitato di richieste.
**UNKNOWN** significa che il dato non è leggibile: NON dimostra
che non esistano richieste.

## Prova su copia di salvataggio, SOLO dopo build Mac verificata

1. Terminare The Sims 4, conservare una copia della partita.
2. Sostituire entrambi i file M101d nella cartella Mods con i due
   file `MHS_M102_BOUNCER_READONLY_MAC_TEST`. Non usare le
   diverse versioni contemporaneamente.
3. Al mattino nel gioco, a casa, in un nuovo giorno scolastico:
   `mhs101.arm`. Nessun altro comando.
4. Accompagnare Rosario, Sandro e Sofia al liceo.
5. Dopo l'inizio delle lezioni, eseguire una sola volta
   `mhs101.check` e fornire
   `MY_HIGH_SCHOOL_M25_TEST_DATA/MHS_M101_UNO_SLOT_EA.json`.

**L'obiettivo di questo test NON è far arrivare già tutti e 16.**
Dobbiamo determinare se la richiesta di uno studente viene
elaborata/assegnata dal Bouncer. Un codice di diagnostica da solo
non è una correzione di capienza o presenza.
