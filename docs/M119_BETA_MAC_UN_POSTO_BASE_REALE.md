# M119 — Prima beta Mac che modifica una convocazione EA originale

## Cosa cambia rispetto a M110–M118

Questa è la prima beta di test che MODIFICA IN TEMPO REALE una
convocazione scolastica, non una diagnostica di sola lettura.
È **volutamente limitata a UN SOLO NPC iscritto alla Classe 1**,
su UNA SITUAZIONE BASE EA `277733`. Non modifica le altre
situazioni, nessun docente, evento, lezione, ruolo Core o roster
salvato. Non promette 16 studenti presenti.

- `src/m119_live_trial/mhs119_one_base_live_trial.py`:
  attivazione manuale `mhs119.arm` da casa. Legge il salvataggio
  già esistente con **due classi di 8** e **tre teenager giocabili
  iscritti**, prende il primo **NPC umano adolescente** della
  Classe 1 (in ordine di iscrizione), mostra il suo SimID
  e installa quattro wrapper EA reversibili.
- Al primo `SituationManager.create_situation` del liceo
  con SituationGUID `277733` e un'originale `guest_list`
  compatibile, copia la lista mantenendo eventuali insegnanti,
  sostituisce il SOLO studente Base random con il SimID scelto
  dal registro, `accept_alternate_sim=False`, e chiama il
  metodo nativo EA esattamente una volta. Se la lista
  contiene un job inatteso, due Base o è incompatibile,
  passa l'originale SENZA modificarla.
- Il SOLO `BouncerRequest` per lo stesso ID/ruolo/situazione
  e con constraint esatto `{SimID}`, proveniente dalla
  zona scuola e salvataggio della sessione, usa in modo
  temporaneo `TunableSimFilter.BLANK_FILTER`. Le richieste
  EA non riconosciute restano originali.
- `clone_for_replace` viene bloccato solo per questa
  richiesta verificata; le altre richieste EA sono originali.
- `mhs119.status` riporta gli inviti e il lavoro dei filtri.
  Inoltre usa `SituationManager.get(situation_id)` e
  `all_sims_in_job_gen` per leggere se il SIM preciso è
  effettivamente nel job Base di quel momento. Distingue
  `EA_ruolo=SI_TARGET_PRESENTE`,
  `NO_SIM_DIVERSO`, `NO_RUOLO_VUOTO` o situazione
  non trovata. La sola creazione non basta per una prova di arrivo.
- `mhs119.stop` ripristina i quattro metodi EA originali e
  i filtri di richieste ancora vive. Non sovrascrive
  modifiche di altre mod introdotte dopo l'attivazione:
  segnala il conflitto e richiede un riavvio pulito.

## Come provare su Mac (solo copia salvataggio)

1. Salvare una COPIA del salvataggio che contiene il registro MHS.
   NON usare mai il proprio salvataggio principale.
2. Chiudere completamente The Sims 4. Rimuovere da Mods le beta
   M109, M110, M111 e altri controller EA sperimentali; lasciare
   soltanto la mod stabile MHS per la gestione del menu, se
   necessaria al salvataggio, e il file di prova.
3. Dal workflow della M119 scaricare l'artefatto
   `MHS_M119_SINGLE_BASE_MAC_EXPERIMENTAL`. Estrarre SOLO
   `MHS_M119_UN_POSTO_BASE_MAC_BETA.ts4script` in Mods.
4. Abilitare le mod script e aprire la copia del salvataggio.
   A casa, prima di partire, aprire console:
   `mhs119.arm`. Deve mostrare `M119 PRONTA`
   e il SimID preso dal registro Classe 1.
5. Accompagnare i teen al liceo. Dopo arrivo,
   eseguire `mhs119.status`. Mostra 1 tentativo o 0
   (nel caso EA non abbia presentato una lista compatibile),
   ID situazione, filtro applicato e appartenenza al job.
6. Inviare **uno screenshot** di questa risposta, e verificare
   se il Sim indicato risulta visibile nel lotto. Non è
   necessario ripetere tutta la giornata M110.
7. Eseguire `mhs119.stop`, poi chiudere il gioco.
   Nessuna modifica a roster o ruoli MHS.

## Cosa ci dice il primo test

- `attempts=0`: il primo callback EA non aveva una guest list
  originale compatibile, oppure è stato ignorato per sicurezza.
  Non significa che EA non gestisca la classe; esamineremo
  ESATTAMENTE il punto d'ingresso senza test casuali.
- `attempts=1, EA_situation > 0`: EA ha creato una
  situazione utilizzando la lista clonata. NON prova
  che il Sim sia già sul lotto.
- `EA_ruolo=SI_TARGET_PRESENTE`: EA ha assegnato l'NPC scelto
  al ruolo Base nella situazione e nell'istante osservato.
  NON prova ancora la classe, la seduta o il giorno intero.
- `NO_SIM_DIVERSO`: EA ha usato un altro Sim; servirà
  correggere Bouncer/constraints per quel caso specifico.
- `NO_RUOLO_VUOTO`: non risulta nessun Sim assegnato;
  distinguere tempo di spawn e filtro non soddisfatto.

## Stato tecnico

Build con Python 3.7; test automatici su gestori EA simulati:
https://github.com/iliyanadg/MyHighSchool/actions/workflows/m119-one-base-mac-beta.yml
Non è ancora testata dentro The Sims 4 e può non funzionare
su una configurazione di mod/gioco incompatibile.
Non modifica `main`, il controller definitivo MHS o i
salvataggi direttamente. La prova è reversibile soltanto
per i metodi hook installati: i Sim già convocati rimangono
nel gioco fino al normale termine delle situazioni EA.
