# M116 — Confronto dei veri job Base/Core dopo gli inviti, 3 novembre 2026

## Problema risolto nel modello di controllo

Il file reale M111 mostrava solo 4/16 iscritti istanziati e
nessun adolescente nella classe MHS corretta. Non basta sostituire
la guest list EA durante create_situation: il ritorno positivo
dell'operazione NON attesta che il Bouncer abbia realmente assegnato
quell'identità.

M115 ha individuato nel file originale EA sim_filter_service.py
la costante nativa
filters.tunable.TunableSimFilter.BLANK_FILTER, ora risolta in sola
lettura nel codice del progetto. Rimane da verificare nel gioco
che la sua applicazione possa ammettere i 13 adolescenti iscritti
senza violare blacklist/capienza/exclusività.

## Nuovo codice M116

SchoolNativeGuestSession (M108) ora conserva per ciascuno dei
nove ticket originari un ID situazione EA positivo:
8 ticket Base (un adolescente ciascuno) e 1 Core
(5 ruoli studenti manualmente assegnati).
Non si tratta di un altro roster e non aggiunge altri NPC.

Il modulo
src/m116_admission/mhs116_native_guest_job_readback.py
usa soltanto API originali già osservate:
- SituationManager.get(situation_id);
- BaseSituation.all_jobs_gen();
- BaseSituation.all_sims_in_job_gen(job);
- BaseSituation.all_sims_in_situation_gen().

Controlla che:
1. Esistano tutti e nove gli ID originali distinti;
2. il flag EA _sim_assignment_complete sia stato osservato;
3. per ogni ticket Base il job 277894 contenga ESATTAMENTE
   l'ID NPC richiesto;
4. per il Core, i cinque job 278965, 278966, 278967,
   278968 e 303765 contengano i cinque ID scelti in M97;
5. non ci siano ID duplicati tra le situazioni, ruoli studente
   erroneamente associati a professori, job/situazioni sconosciute,
   membri inattesi o situazioni mancanti.

Al risultato viene dato il nome
NATIVE_GUEST_JOBS_MATCH_OBSERVED o
NATIVE_GUEST_JOBS_DIFFER. Il rapporto riporta le differenze.

Il modulo è **in sola lettura**. Nessuna installazione automatica,
nessun override del Bouncer, nessun aggiornamento al salvataggio.

## Limite e ordine corretto di attivazione

Il flag _sim_assignment_complete da solo non prova la
provenienza dal callback post-Bouncer. Il readback M116 deve
essere richiamato dopo che il callback EA originale
on_all_sims_spawned_during_zone_spin_up ha davvero terminato;
il modulo M108 spinup barrier identifica la posizione, ma
non è ancora cablato alla M113.

Il controllo 13 NPC Base/Core non certifica:
- che i 3 giocabili siano realmente presenti sul lotto;
- che tutti i 16 siano stati assegnati ai job delle due lezioni;
- che ciascun adolescente sia seduto nell'aula corretta;
- che le presenze restino fisse nei giorni successivi.

La futura attivazione deve essere progressiva:
1. a casa: congelare 16 iscritti, 3 giocabili e i 5 ruoli Core;
2. primo callback EA al liceo: preparare **solo** inviti,
   Bouncer, no-show e osservazione, con rollback;
3. dopo il callback: confrontare i 13 NPC nei nove job EA,
   controllando i 3 playable sul lotto;
4. solo dopo tale conferma attivare il sistema delle lezioni,
   senza fingere che una giornata intera sia già stata verificata;
5. controllare separatamente le due aule e la persistenza
   sul secondo giorno.

La vecchia M113 installava unified_lessons nel medesimo blocco
dell'ammissione mattutina. La M116 ha individuato la necessità
di separare queste due fasi: non sostituire un gate mancante con
un dizionario di True per forzare l'installazione.

## Validazione

- tests/test_m116_native_guest_job_readback.py: 10 casi
  (13 NPC corretti, sostituti, job errati, duplicati, situazioni
  mancanti, flag Bouncer falso e sessione incompleta).
- Rilanciate le regressioni inviti M108 / M112.
- Workflow Python3.7:
  https://github.com/iliyanadg/MyHighSchool/actions/runs/41687855452

Questi test sono sintetici, NON giocati su Mac.
NON esiste una .ts4script M116 da installare.
Ramo sperimentale; main non modificato.
