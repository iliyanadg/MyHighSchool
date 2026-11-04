# M117 + M118 — Da inviti creati a 13 NPC effettivamente assegnati

## Perché abbiamo separato le due fasi

La M111 ha osservato alle 10:33 solo 4 dei 16 adolescenti iscritti sul
lotto e nessuno nel job dell'aula MHS corretta. Le M112–M116 preparano
i veri inviti, il filtro EA originale e la verifica degli ID inseriti
nei nove job Base/Core. Tuttavia **la creazione della situazione non è
l'assegnazione del Sim**.

La M113 iniziale includeva `unified_lessons` nello stesso blocco
dell'ammissione mattutina; `mhs108_unified_lessons` richiede invece
`full_16_school_day_ea_membership_verified`, impossibile da fornire
in modo onesto prima che il Bouncer chiami i Sim.

## M117: callback originale EA di completamento spin-up

`src/m117_spinup/mhs117_post_spinup_admission.py` prepara un observer
reversibile per
`situations.situation_manager.SituationManager.
on_all_sims_spawned_during_zone_spin_up`.

L'originale EA è chiamato **una sola volta, prima di leggere** e
senza modificare il risultato o nascondere eccezioni. Con contesto
live verificato di save/day/zone/schedule e l'originale flag
`_sim_assignment_complete=True`, esegue la lettura M116 di tutti
i nove originali EA situation IDs e confronta i 13 NPC esatti con i
job Base/Core previsti. Una sola lettura per istanza manager, senza
richiamare eventi o generare NPC.

Il rapporto distingue:
- appartenenza corretta ai job Base/Core di mattina;
- inviti mancanti o situazione EA inesistente;
- Sim sbagliati/duplicati/ruolo errato;
- prova che il callback originale EA è stato eseguito in quell'istanza.

**Non** prova Bouncer lezioni delle 10/14, banchi, giorno intero,
tre Sim giocabili, né che il controller possa essere armato.

Test M117 Python 3.7 (10 nuovi test, più regressioni M116/M108):
https://github.com/iliyanadg/MyHighSchool/actions/runs/41688829370
Risultato: success.

## M118: gate 13 NPC + 3 playable prima delle lezioni

`src/m118_controller/mhs118_admission_before_lessons.py`
introduce un grafo mattutino di **quattro** interventi, senza
`unified_lessons`:
1. `native_precreate`: usare gli ID di invito nativi;
2. `school_filter_scope`: usare M115 BLANK_FILTER solo su inviti
   esatti autorizzati;
3. `no_show_guard`: evitare la sostituzione casuale degli stessi;
4. `post_bouncer_observer`: richiamare M117 dopo lo spin-up EA.

L'installazione di questi quattro interventi non è ancora cablata
a una mod installabile e richiederà i gate live indipendenti e il
rollback atomico.

Il gate `inspect_lesson_admission_gate` confronta il report M117
originale, i 13 job NPC assegnati e un elenco di 3 ID giocabili
**già istanziati sul lotto scolastico** con provenienza verificata
dallo SimInfoManager corrente e identità save/day/zone corrispondente.
Non utilizza tre nomi dal solo registro come prova di presenza.

Anche se tutti i dati combaciano, il gate non imposta
`lesson_stage_install_authorized=True`: i controlli aggiuntivi
delle lezioni EA, il percorso doppio di Classe 1 e il post-Bouncer
del cambio fase restano ancora da verificare. Non dichiara
`16 presenti e seduti`.

## Test e stato

- M117 original EA callback: success, Python3.7.
- M118 grafo mattutino vs lezioni e fail-closed: workflow
  https://github.com/iliyanadg/MyHighSchool/actions/runs/41689270169.
- Nessun file .ts4script creato per M117 o M118, nessun hook attivo
  nel gioco e nessuna modifica a main.
- Per una beta correttiva serve completare il provider runtime
  indipendente, i gate reali Bouncer, i quattro stage atomici,
  il controllo dei giocabili dalla zona EA, e successivamente
  l'attivazione separata delle lezioni.

**Obiettivo invariato:** tredici NPC fissati dal registro più tre
adolescenti giocabili, due classi con otto, nessun sostituto casuale.
