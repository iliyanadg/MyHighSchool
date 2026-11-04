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
| Un bidello | 298096 | 290196 | Invito esatto sperimentale |
| Un addetto mensa | 278011 | 278010 | Invito esatto sperimentale |

Il codice rilegge il registro alla nuova giornata, verifica che ogni Sim
esista e sia umano giovane adulto/adulto/anziano, e presenta la guest list
native soltanto prima della creazione delle situazioni scolastiche originali.
Il filtro Bouncer e limitato all'ID, situazione e job dell'invito. Non si
assegnano trait nascosti, non si creano situazioni aggiuntive e non si
cancellano situazioni in corso.

**Limite importante:** la selezione contemporanea di 2 bidelli, 2 o 3
addetti mensa è ancora memorizzata nel registro, ma i posti multipli non
sono implementati in questa revisione. Il tentativo native per quel ruolo
viene omesso con codice `NATIVE_JOB_MULTI_CAPACITY_NOT_VERIFIED`: EA
mantiene le regole originali, dunque potrebbe comparire il suo NPC.
Questa revisione non deve essere presentata come soluzione completa.

## Prima di provare su Mac

1. Non sostituire la coppia funzionante nella cartella Mods principale.
   Fai copia dei salvataggi e di `MY_HIGH_SCHOOL_M25_TEST_DATA`.
2. Lavora con una copia del salvataggio già collaudato, preferibilmente
   con una cartella Mods di prova che abbia **una sola** coppia MHS.
   Mantieni XML Injector e le altre mod nelle stesse condizioni del
   primo collaudo.
3. Per la prova dell'assegnazione nativa scegli nel menu esattamente
   un preside, un professore per ciascuna aula attiva, **un solo bidello
   e un solo addetto alla mensa**. Non cancellare gli altri incarichi
   dal tuo salvataggio originale: questa limitazione vale solo per
   il test della build beta.
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
  incarico l'identita scelta e quella osservata nel job EA; un
  `matches: null` non prova successo o fallimento: significa che la
  lettura e incompleta. `native_staff_projection_attempts` distingue
  un invito preparato dall'effettivo job osservato.
- Ripeti soltanto se la prima giornata non mostra problemi al gioco.
  Le scelte effettuate durante una giornata devono valere dal giorno
  successivo; non fare cambiamenti sul salvataggio originale.

## Criteri di accettazione

Il codice passa il collaudo in gioco **solo** se il job nativo letto
corrisponde ai Sim scelti, i loro comportamenti scolastici rimangono
corretti, tutti gli studenti continuano a frequentare e i nomi restano
stabili il giorno seguente. Un archivio Python valido, un test unitario
verde o `create_situation` con ID positivo non certificano questi
risultati. Per due o piu lavoratori della stessa categoria serve una
successiva soluzione testata, non una promessa di capienza nativa.

Fonte: tuning EA gia verificati del repository,
`docs/PASSO_74_ANALISI_10_SITUATION_JOB_EA.md`, e analisi del
primo report `MHS_CLASSROOM_CONTROL_REPORT_COMPLETO.json`.
