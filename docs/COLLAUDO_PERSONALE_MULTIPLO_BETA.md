# MY HIGH SCHOOL — Secondo bidello e piu addetti mensa (beta)

**Base reale:** nel report del 6 novembre erano presenti 16 studenti, 2
professori, preside, Agnes Crumplebottom e 13 NPC osservati mentre mangiavano.
Soltanto Gianluca Ferraro risultava nel job EA custode; Bjorn Bjergsen era
invitato ma assente dal job. Agnes era l'unica addetta mensa attiva; Alex
Moyer e Alessia Sanna restavano nel registro ma non erano ancora convocati.

## Cosa cambia

- **Bidello:** quando un solo bidello selezionato e gia presente in un vero
  job custode EA (290196), MHS puo tentare **una sola** seconda situazione
  EA 298096 con invito esatto del bidello mancante, senza un altro preside
  esplicitamente invitato. Le due situazioni non sono considerate due
  custodi realmente presenti finche la lettura nativa non li conferma.
- **Mensa:** Agnes resta primaria nell'originale situazione EA 278011.
  Gli altri addetti scelti possono ottenere una situazione EA 278011
  aggiuntiva ciascuno, con un ID Sim esatto e distinto, solo se MHS
  riconosce il numero necessario di **banconi mensa scolastici veri**.
  Nessun NPC casuale deve sostituire il personale scelto.
- **Orario inviti aggiuntivi:** 10:30–11:29 dell'orologio di simulazione,
  dopo che il personale principale e stato osservato nei job EA.
- **Fail-safe:** situazione/banco non riconosciuti, addetto non disponibile,
  EA che rifiuta l'incarico o forma API sconosciuta non devono alterare
  il personale, le lezioni o gli studenti gia presenti.

## Un solo collaudo in gioco

1. Lavora su una **copia del salvataggio**; conserva la build precedente.
   Non cancellare `saves` o `MY_HIGH_SCHOOL_M25_TEST_DATA`.
2. Se vuoi **3 addetti mensa contemporaneamente**, colloca **3 banconi
   mensa scolastici complessivi**, uno per addetto, prima dell'inizio della
   giornata. Per provarne 2 bastano 2 banconi. Assicurati che possano
   essere raggiunti e che abbiano spazio sufficiente per gli studenti.
3. Installa esclusivamente la coppia `MHS_CLASSROOM_CONTROL.package`
   e `MHS_CLASSROOM_CONTROL.ts4script` dell'Artifact di **questa PR**,
   non una vecchia coppia e non altre mod che aumentano i vendor.
4. Attiva da casa con `mhs148.arm`; osserva una giornata alle 10:30,
   11:15 (pausa) e 14:00. Non forzare gli NPC a lavorare.
5. Alle 15:00 esegui `mhs148.report` e invia
   `MHS_CLASSROOM_CONTROL_REPORT_COMPLETO.json`.

## Prova richiesta nel rapporto

- `school_staff.supplemental_staff_requests`: solo tentativi di
  creazione delle situazioni EA, **non prove di impiego**.
- `school_staff.supplemental_staff_last_status`: motivo di eventuale
  blocco (per esempio `ADDITIONAL_CAFETERIA_STATION_REQUIRED`).
- `school_staff.samples[].observed_staff` e
  `school_staff.native_job_shift_verdict`: persone realmente
  osservate nei job di preside, insegnante, custode e mensa.
- Verifica visivamente che gli addetti mensa servano ciascuno il proprio
  bancone e che entrambi i bidelli svolgano l'attivita prevista da EA.
  Non inferire il lavoro dalla sola presenza sul lotto.

**Stato:** codice e test offline non equivalgono a gameplay verificato.
Non dichiarare completato il supporto multiplo prima del rapporto in gioco.
