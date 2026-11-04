# M120 — Otto NPC Base scelti, primo intervento Mac 8 posti

## Risultato reale precedente

Nel salvataggio Mac di prova il 3 novembre 2026, la M119 ha dato
`attempts=1`, `EA_ruolo=SI_TARGET_PRESENTE`,
`filter=1`, `error=none` sia alle 8:13 sia alle 10:32.
Questo dimostra l'assegnazione di UN NPC scelto al ruolo originale EA
Base 277894 nella situazione Base 277733. Non prova lezioni o seduta.

## Cosa contiene la M120

`src/m120_base/mhs120_eight_base_live_trial.py`:

- usa il registro esistente nel save: due classi attive da 8;
- identifica i 3 teen giocabili e i 5 Core NPC
  **esplicitamente assegnati dall'utente nel registro M97**;
- gli 8 NPC rimanenti sono i soli `Base`, ordinati nel registro;
- da casa `mhs120.arm` installa temporaneamente gli originali
  `SituationManager.create_situation`,
  `BouncerRequest.__init__`,
  `BouncerRequest.get_additional_filter_terms`,
  `BouncerRequest.clone_for_replace` e
  `WeeklyScheduleDay.get_long_term_situation_count`;
- al liceo, SOLO quando l'originale EA calendario Base torna
  `(3,3)`, prima dei nove inviti, propone `(8,8)`.
  Non inventa la causa del conteggio (3,3).
- sostituisce via guest list originale EA fino a OTTO inviti
  Base distinti con i SimID NPC iscritti. Le guest list originali
  restano immutate e eventuali docenti rimangono intatti.
- usa il filtro nativo TunableSimFilter.BLANK_FILTER soltanto
  sulle request con quello specifico SimID/Base e constraint esatto;
  non cambia tuning EA o trait degli studenti;
- dopo il viaggio `mhs120.status` misura il numero di ID
  situazione Base creati e quante delle otto situazioni contengono
  l'NPC desiderato nel job EA 277894 in quell'istante;
- `mhs120.stop` ripristina tutti i cinque metodi originali EA.

**Il controller NON modifica le situazioni Core 298052**, le lezioni
o i posti a sedere. Non crea altri NPC, non salva modifiche al roster.

## Come installare solo su copia del salvataggio

1. Chiudere The Sims 4 e fare backup del salvataggio MHS.
2. Eliminare da Mods M119, M111 e tutte le beta EA precedenti;
   la mod stabile di menu e registro può rimanere.
3. Aprire la run CI M120 e scaricare l'artefatto
   `MHS_M120_EIGHT_BASE_MAC_EXPERIMENTAL`, estrarre il solo
   `MHS_M120_OTTO_BASE_MAC_BETA.ts4script` in Mods.
4. Le classi MHS devono avere 8 iscritti ciascuna, con i 3
   adolescenti della famiglia iscritti; il registro M97 deve
   avere 5 Core scelti manualmente tra i 13 NPC iscritti.
   Senza M97 la M120 **BLOCCA l'armamento**, non inventa ruoli.
5. A casa prima della scuola: `mhs120.arm` →
   `M120 PRONTA: 8 NPC Base fissi`.
6. Al liceo: `mhs120.status` subito dopo arrivo e alle 10:30.
   Guardare `EA_base_created`, `EA_base_present`,
   `count_override`, `native_count`, `missing`.
7. Dopo la prova, `mhs120.stop`, quindi chiudere il gioco.

## Limiti onesti

Il codice è stato compilato per Python 3.7 e ha superato test
di metodi EA simulati. **Non è ancora validato nella partita Mac**.
Il sistema dei 5 Core non è ancora stato sovrascritto o garantito,
la capienza reale sul lotto non è dimostrata e i 3 playable
non sono ancora verificati nel ruolo di lezione. Anche con
`EA_base_present=8/8` non avremmo provato 16 seduti in 2 aule.
Se non ci sono 8 situazioni originali, il report potrà indicare
meno di 8 senza fingere successo.

Workflow:
https://github.com/iliyanadg/MyHighSchool/actions/runs/41704539892

Non toccare il branch main stabile.
