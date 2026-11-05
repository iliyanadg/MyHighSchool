# MY HIGH SCHOOL — Collaudo mirato del personale EA (beta)

Questa revisione aggiunge una **proiezione degli inviti nativi**, non una
certificazione che EA abbia assunto i Sim. La build usa gli stessi menu M54,
lo stesso registro per salvataggio, lo stesso controller M148 e le stesse
lezioni collaudate per i sedici studenti. Tutti i test offline e il controllo
bytecode Python 3.7 devono passare prima dell'installazione.

## Collegamenti presenti nel codice

| Menu M53 | Situation EA | Situation Job | Stato |
| --- | --- | --- | --- |
| Professore Classe 1 | 298052 | 277895 | Invito esatto sperimentale |
| Professore Classe 2 | 298052 | 278963 | Invito esatto sperimentale |
| Preside | 298096 | 278223 | Invito esatto sperimentale |
| 1 o 2 bidelli | 298096 | 290196 | Inviti esatti sperimentali sullo stesso job |
| Un addetto mensa | 278011 | 278010 | Invito esatto sperimentale |

Il codice rilegge il registro alla nuova giornata, verifica che ogni Sim
esista e sia umano giovane adulto/adulto/anziano, e presenta la guest list
native soltanto prima della creazione delle situazioni scolastiche originali.
Il filtro Bouncer e limitato all'ID, situazione e job dell'invito. Non si
assegnano trait nascosti, non si creano situazioni aggiuntive e non si
cancellano situazioni in corso.

**Beta bidelli:** se nel registro vengono scelti esattamente due bidelli,
il controller può invitarli entrambi nella situazione Venue EA 298096
sullo stesso job 290196. Non crea un secondo job o una situazione inventata.
L'auto-invite del tuning EA ha limite 1; questo non dimostra un limite 1
agli inviti espliciti, ma nemmeno prova che EA assegni effettivamente due
lavoratori. Occorre osservare nel gioco **due job nativi contemporanei**
prima di dichiarare completata questa funzione.

**Correzione mensa dopo il primo collaudo reale (5 novembre 2026):**
in un salvataggio con 3 addetti selezionati, il controller precedente
bloccava TUTTI e tre con `NATIVE_JOB_MULTI_CAPACITY_NOT_VERIFIED`.
Il rapporto mostrava 0 addetti con job EA 278010 e 0 richieste di cibo
osservate fra i 13 studenti NPC (solo 1 NPC visto mangiare).
Per non lasciare il banco senza lavoratore, questa beta propone il **primo
addetto del registro**, sempre lo stesso, come unico vendor EA 278010.
Gli altri due restano nel registro e sono **esplicitamente segnalati**
come `EXTRA_CAFETERIA_WORKERS_PENDING_NATIVE_STATIONS`; non vengono
impiegati, non vengono alternati e non vengono rimossi.

Questo e un fallback **parziale**, non la soluzione ai 2–3 lavoratori
contemporanei, per la quale occorre un meccanismo verificato di
assegnazione a vere postazioni EA distinte. Il successo dell'invito
non garantisce presenza o servizio: verificarli durante il pranzo.

## Prima di provare su Mac

1. Non sostituire la coppia funzionante nella cartella Mods principale.
   Fai copia dei salvataggi e di `MY_HIGH_SCHOOL_M25_TEST_DATA`.
2. Lavora con una copia del salvataggio già collaudato, preferibilmente
   con una cartella Mods di prova che abbia **una sola** coppia MHS.
   Mantieni XML Injector e le altre mod nelle stesse condizioni del
   primo collaudo.
3. Per il primo controllo del personale scegli nel menu un preside,
   un professore per ciascuna aula attiva, **un bidello e un addetto
   alla mensa**. Se questa prova funziona, sul salvataggio di test
   scegli un **secondo bidello**, avvia una nuova giornata e confronta
   l'identità di entrambi i lavoratori nel job EA 290196. Se il registro
   contiene gia 2–3 addetti mensa, non serve eliminarli: un solo
   lavoratore principale sara invitato, mentre gli altri resteranno
   esplicitamente in sospeso. Non cancellare incarichi dal salvataggio
   originale.
4. Attiva/ricarica la gestione da casa e avvia una nuova giornata
   scolastica. Non installare lo script a scuola, a lezioni iniziate.

## Verifiche concrete

- In gioco, all'inizio della giornata, confronta il nome del preside e
  dei due professori effettivamente presenti con quelli del menu.
  Controlla poi il bidello e l'addetto mensa, compreso il comportamento
  lavorativo. Le persone devono svolgere il **job EA**, non solo
  trovarsi sul lotto.
- Conserva le due classi da 8 e verifica soltanto che la gestione
  studenti non abbia subito regressioni.
- Dopo le 15:00 esegui `mhs148.report` e salva una copia con nome
  `..._PERSONALE_GIORNO1.json`. Il file esportato normalmente usa
  `MHS_CLASSROOM_CONTROL_REPORT_COMPLETO.json`.
- Nel JSON, `school_staff.samples[*].comparison` mostra per ogni
  incarico l'identita scelta **all'inizio di quella giornata**, anche
  se il menu viene modificato in seguito, e l'identita osservata nel
  job EA. Un `matches: null` non prova successo o fallimento: la
  lettura e incompleta. `native_staff_projection_attempts` distingue
  un invito preparato dall'effettivo job osservato.
- `school_staff.cafeteria_native_primary` riporta l'ID dell'unico
  addetto mensa invitato; `school_staff.staff_pending_extra_workers`
  contiene gli altri addetti selezionati, ancora senza vero job EA.
  Il rapporto non dichiarera completa l'assegnazione di 3 lavoratori
  soltanto perche il primo e stato visto al banco.
- Il riepilogo `school_staff.native_job_shift_verdict` mostra
  `NATIVE_JOB_MATCH_OBSERVED`, `NATIVE_JOB_DIFFERENT_FROM_MENU`,
  `NATIVE_JOB_INCONSISTENT_ACROSS_SAMPLES` oppure l'incompletezza.
  Per due bidelli, `two_custodians_same_sample_confirmed=true`
  richiede che entrambi abbiano davvero il job EA 290196 nello stesso
  campione completo: **non** prova che lavorino l'intera giornata,
  né il funzionamento nei giorni successivi.
- Ripeti soltanto se la prima giornata non mostra problemi al gioco.
  Le scelte effettuate durante una giornata devono valere dal giorno
  successivo; non fare cambiamenti sul salvataggio originale.

## Criteri di accettazione

Il codice passa il collaudo in gioco **solo** se il job nativo letto
corrisponde ai Sim scelti, i loro comportamenti scolastici rimangono
corretti, tutti gli studenti continuano a frequentare e i nomi restano
stabili il giorno seguente. Il caso dei due bidelli passa solo se
entrambi sono osservati **nello stesso momento** con job EA 290196 e
svolgono davvero le mansioni; non basta una guest list contenente
due inviti. Un archivio Python valido, un test unitario verde o
`create_situation` con ID positivo non certificano questi risultati.
Per due o più lavoratori mensa occorre ancora un progetto verificabile
che supporti più postazioni.

Fonte: tuning EA gia verificati del repository,
`docs/PASSO_74_ANALISI_10_SITUATION_JOB_EA.md`, e analisi del
primo report `MHS_CLASSROOM_CONTROL_REPORT_COMPLETO.json`.
