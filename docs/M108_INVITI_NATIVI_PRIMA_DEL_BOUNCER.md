# M108 — inviti nativi EA prima del Bouncer (prototipo offline)

**Stato: codice + test inviati a GitHub, CI in attesa di verifica; NON build installabile.**
**Ramo:** `feature/m55-presenze-studente-test`. `main` NON modificato.

## Obiettivo immutabile della giocatrice

- Esattamente **16 adolescenti selezionati**, in due classi da 8.
- **3 giocabili** della famiglia attiva, **13 NPC iscritti**.
- Gli NPC: **5 ruoli speciali EA** assegnati manualmente + **8 ruoli Base**.
- Non rimuovere, riassegnare o sostituire Sim iscritti.
- Non modificare tratti/persona dei Sim per farli rientrare in un filtro.
- Studenti identici ogni giorno; insegnanti, mensa e custode originali
  non devono essere eliminati per ottenere il roster.
- Nessun comportamento casuale in caso di errore o posto esaurito.

## Nuovo codice

`src/m108_native_roster/mhs108_native_invitation.py`:
- `prepare_fixed_manifest` convalida ID, classi, 3 playable,
  5 Core confermati, 8 Base, salvataggio, giorno e zona.
- NON usa né considera autorizzativi i sei filtri scolastici EA:
  M105/M106 hanno provato che i filtri originali respingono alcuni
  iscritti del salvataggio vero.
- `SchoolNativeGuestSession.preview` prepara nuove
  `SituationGuestList(invite_only=True)` con ID espliciti usando
  la API `SituationGuestInfo.construct_from_purpose(INVITED)`,
  **senza modificare le liste EA originali**.
- Per la situazione EA Base 277733, ogni invito contiene esattamente
  un iscritto fra gli 8 Base non giocabili.
- Per la situazione EA Core 298052, l'invito contiene
  precisamente i 5 Sim dei rispettivi SituationJob,
  conservando qualsiasi eventuale guest preesistente che sia
  inequivocabilmente un docente EA.
- Qualsiasi guest studente sconosciuto o job non previsto
  fa rifiutare la preparazione. I lavori staff non vengono
  rimpiazzati e le situazioni esterne non sono gestite.
- Richiede un contesto di chiamata originale EA
  *verificato fuori dal modulo*: `native_origin_verified`,
  scuola, schedule, salvataggio, giorno, zona.
  **Un testo `creation_source` non è una prova di origine**.
- `acknowledge_created` registra soltanto un ID positivo di
  situazione creata, e offre `cancel` per tentativi falliti.
  Un ID di situazione non conferma presenza né ruolo del Sim.
- NON installa alcun hook, non avvia situazioni, non tocca i
  salvataggi, non modifica tuning o filtri globali.

## Nuova verifica incrociata con XML originali EA

`tests/test_m108_native_school_tunings.py` usa **i veri XML**
già estratti dalla versione EA della giocatrice:

- `277657.xml` e `279958.xml` creano prima le
  situazioni **Base** (277733), poi la **Core** (298052).
  Il prototipo M108 iniziale presumeva Core prima di Base;
  questa supposizione è stata rimossa e i test delle 8
  richieste sono stati riscritti in ordine **Base → Core**.
- Entrambi i calendari hanno un conteggio vanilla Base di
  **6–6 prima dei modificatori**.
- `293642.xml`, `293644.xml`, `304561.xml`,
  `304563.xml`: limite EA del job fase Classe 1 **6**.
- `304570.xml`: limite del job fase Classe 2 **8**.
  Non sono prove della presenza o dell'effettiva disposizione
  dei Sim nell'aula.

`tests/test_m108_native_invitation.py` verifica:
- 16 iscritti senza duplicati; 3 giocabili; 5 Core; 8 Base;
- nessuna riscrittura di guest list con un invito EA sconosciuto;
- conservazione di guest teacher e dei flag del guest list;
- nessuna invocazione fuori da scuola, save, giorno o schedule;
- un solo invito per ogni Base e nessun diciassettesimo NPC;
- rollback di richieste non create, rifiuto di ID situazione duplicati;
- conferme di creazione sempre distinte da presenze e lezioni.

CI: entrambi i test sono inclusi anche nel job Python 3.7
`capacity_mac_beta`, oltre al job generico `roster`.
Non interpretare la compilazione o un test offline verde
come successo in gioco.

## Blocchi tecnici effettivi per l'aggancio M108 LIVE

1. **Prenotazioni anticipatissime dei 5 Core:** i 6
   inviti Base originali possono arrivare *prima* della
   creazione della situazione Core. Serve un gate di
   prenotazione dei ruoli prima che inizi lo spin-up,
   non il controllo tardivo dell'attuale membership.
2. **Filtro scolastico ristretto ai 16 iscritti:** gli
   ID richiesti restano soggetti al `SimFilterService`
   nativo e ai termini aggiuntivi del `SituationJob`.
   Nessuna prova che l'override scuola-only li faccia
   entrare. Non sostituire indiscriminatamente i filtri.
3. **No-show e died/left:** `BaseSituation` può
   creare una nuova richiesta SENZA l'ID specifico.
   Serve bloccare questo fallback *solo* per gli studenti
   scolastici mentre si preservano i rimpiazzi del personale.
4. **Numero Base:** modificare in modo verificato il
   calendario 6→8, con trattamento dei modificatori
   playable e rollback.
5. **Lezioni e posti fisici:** due fasi giornaliere
   Classe 1/Classe 2 da 8 e capacità di ospitare almeno
   16 studenti + staff senza espulsioni del Bouncer.
6. **Integrazione effettiva:** collegare questa policy
   al `SituationManager.create_situation` *già esistente*
   senza introdurre situazioni EA aggiuntive e senza
   invocare due volte `original` in caso di errore.

## Prossimo passo tecnico

Implementare e testare una **riserva precoce dei 5 job Core
prima del conteggio Base** con prove di non collisione e
nessuna mutazione EA se il piano è incompleto. Solo dopo
collegare la selezione al punto d'aggancio M89 esistente.
La beta Mac resterà sospesa sino ai sei gate sopra.

**Non chiedere nuovi test nel gioco né un cambio di Sim/trait.**

## Avanzamento M108 — prenotazioni locali Core e adattatore pre-create

**Modifiche aggiunte il 2 novembre; test GitHub Actions eseguiti in CI ma
il loro risultato deve essere verificato prima di dichiararli verdi.**

1. In `mhs108_native_invitation.py`,
   `reserve_core_before_schedule(context)` prenota
   *internamente alla mod* gli ID dei cinque titolari dei job Core,
   **prima della prima richiesta Base**. Valida
   salvataggio/giorno/zona/calendario, la dichiarazione esplicita
   `before_school_schedule_verified` e `ea_schedule_not_started`,
   più l'assenza di collisioni con playable o gli otto Base.
   `preview` ora non emette nessun invito Base/Core se questa
   riserva non è stata stabilita. È un controllo di **piano**,
   NON ancora una vera `SimReservationRequest` registrata nel
   Bouncer EA. `snapshot.actual_ea_core_reservations_verified`
   rimane **False**.
2. `src/m108_native_roster/mhs108_native_precreate.py`
   implementa uno **stub di integrazione solo offline** su
   `SituationManager.create_situation`. Riutilizza il punto
   nativo di M89, ma include le situazioni Core e Base nello stesso
   piano, senza installare M89 contemporaneamente.
   - Il wrapper conserva i parametri EA, usa una lista clonata
     `invite_only=True`, chiama `original` **al massimo una volta**
     e non fa retry dopo eccezioni.
   - Se il contesto scolastico non è verificato, lascia EA invariato.
   - Una volta provati TUTTI i gate runtime, se la richiesta
     scolastica è verificata ma non ha un candidato preciso,
     restituisce `None` anziché lasciar spuntare NPC casuali.
   - Non modifica feste, situazioni non scolastiche o le liste originali.
   - Non può neppure essere installato senza nove flag runtime
     `REQUIRED_LIVE_GATES` dichiarati tutti `True`.
     **I flag True sintetici nei test non provano nulla del gioco.**
3. `tests/test_m108_native_precreate.py` simula
   otto chiamate Base prima della Core, rifiuto della nona,
   conservazione insegnanti, contesto non scolastico,
   uninstaller, fallimento dell'originale senza retry.
   `tests/test_m108_native_invitation.py` verifica che
   la prenotazione preliminare sia obbligatoria.
4. Entrambi sono stati aggiunti al job CI Python 3.7
   `capacity_mac_beta`; il job generale `roster`
   usa già `unittest discover`.

**Problemi ancora reali, NON risolti:** la riserva Core
è soltanto nel registro MHS; non nel Bouncer.
Mancano i nove gate sul gioco vero (filtro compatibile,
no-show, conteggio Base 8, classi 8+8, cap NPC, staff,
verifica origine EA). Non esiste ancora una beta M108
giocabile, e il ramo `main` non è stato modificato.

### Prossima verifica senza gameplay

Progettare il meccanismo per ammettere i soli studenti
iscritti ai loro SituationJob durante entrambi i percorsi
`zone_spin_up` e `spawn_sim_for_next_request`, senza
cambiare i filtri globali di tutto il gioco. Anche questa
modifica dovrà rifiutare qualunque fallback casuale se
i vincoli originali non possono essere dimostrati.

## Avanzamento M108 — filtri per richiesta Bouncer, NON globali

Sorgenti EA originali verificati insieme (caricati dalla giocatrice):
`bouncer.py`, `bouncer_request.py`, `sim_filter_service.py`,
`situation_job.py`, `base_situation.py`.

**Scoperta tecnica confermata dal codice originale:**
`BouncerRequest.__init__` salva `_sim_filter=job_type.filter`
e `_constrained_sim_ids={requested_sim_id}`.
Il Bouncer consulta lo stesso `request._sim_filter` e
`request.get_additional_filter_terms()` in **quattro punti**
distinti: selezione dei Sim già presenti,
selezione dei Sim già istanziati che cercano altri lavori,
`_spawn_all_during_zone_spin_up` e
`_spawn_sim_for_next_request`.
Cambiare soltanto `SimFilterService.submit_matching_filter` non
copre tutti questi punti. Cambiare il `SituationJob.filter` globale
è pericoloso perché può influire su altri lotti e situazioni.

**Codice aggiunto:**
`src/m108_native_roster/mhs108_school_filter_scope.py`.
È una prova architetturale **solo offline**:
- richiede un piano di iscritti 3+5+8 e i cinque Core già
  prenotati *internamente alla mod* prima del calendario;
- ammette soltanto richieste con Sim ID ESPLICITO e vincolo
  esattamente di un ID, senza `continue_if_constraints_fail`;
- verifica situazione EA originale Base/Core, **SituationJob corretto**,
  adulto escluso, specie umana, età adolescente, Sim NPC
  non selezionabile, stessa zona/giorno/save;
- non modifica dati Sim, tratti, `SituationJob.filter`, blacklist,
  esclusività o lavoro del Sim;
- **soltanto sulla singola richiesta** può sostituire
  temporaneamente `_sim_filter` con un filtro vuoto
  pre-verificato e disabilitare i termini aggiuntivi del job
  per quella medesima richiesta;
- rifiuta gli NPC casuali, i playable, le richieste tardive
  del salvataggio, gli studenti di altri ruoli, situazioni
  estranee e contesto non verificato;
- ripristina il filtro originale a uninstall o se il contesto
  scuola/save/day risulta diverso;
- espone solo `requests_proposed`, **mai conferma presenze**.

`tests/test_m108_school_filter_scope.py` verifica i casi
positivi/negativi, l'isolamento degli altri job, il ripristino
e l'installazione negata se manca anche un solo gate.

**AVVERTENZE REALI:**
1. `install_offline_only` non è importato da nessuna build del
   gioco; i `REQUIRED_FILTER_PROOF` di CI sono sintetici.
   Non esiste ancora una fonte runtime verificata che
   autorizzi tutti i flag.
2. Il filtro vuoto non garantisce, da solo, spawn o accettazione:
   restano blacklist, job test, incompatibilità delle situazioni,
   cap Sim del lotto, RoleState, e callback Bouncer.
3. Il controllo `SituationJob.can_sim_be_given_job`
   esegue ancora il filtro nativo originale quando il job stesso
   non è stato cambiato. `BaseSituation` sembra proseguire
   in un punto dopo un warn, ma bisogna verificare il percorso
   completo fino al ruolo e alla lezione.
4. `BaseSituation.submit_replace_request` e
   `on_failed_to_spawn_sim_for_request` possono invocare
   `BouncerRequest.clone_for_replace()`, che **omette l'ID**:
   un sim fuori elenco può ancora essere convocato dopo no-show
   o abbandono. **Blocco no-show non ancora installato.**
5. Il carico di nove situazioni native (8 Base e 1 Core)
   e il cambio delle fasi Class1 6→8 non sono risolti.
6. Il codice EA decompilato rimane nei caricamenti della
   conversazione e NON viene ripubblicato nel repository.

**Decisione:** il prossimo intervento necessario prima
di una beta è una protezione *school-only* contro la
`clone_for_replace` che elimina l'ID richiesto, oltre alla
verifica del conteggio EA Base e della capienza scolastica.
Non chiedere alcuna prova in gioco adesso. `main` resta intatto.

## Avanzamento M108 — protezione sostituzioni per no-show e abbandono

**Sorgenti decompilati EA esaminati nel workspace locale:**
`base_situation.py` e `bouncer_request.py` forniti dalla giocatrice.
Non pubblicare l'implementazione EA proprietaria in GitHub.

Percorsi originali confermati:

- `BaseSituation.on_failed_to_spawn_sim_for_request(request)`:
  per job con `no_show_action == REPLACE_THEM` chiama
  `request.clone_for_replace(only_if_explicit=True)`,
  quindi invia il clone al Bouncer.
- `BaseSituation.on_sim_unassigned_from_request(sim,request)`:
  per `died_or_left_action == REPLACE_THEM` chiama
  `submit_replace_request(sim,request,job)`; questa funzione
  **rimuove prima il vecchio Sim dalla situazione**,
  poi chiama `request.clone_for_replace()`, invia
  il clone al Bouncer se non è None.
- `BouncerRequest.clone_for_replace` costruisce un
  nuovo `BouncerRequest` **senza passing
  `requested_sim_id`**; il default è 0 e il clone
  perde il vincolo del Sim originario. Questa è una
  causa plausibile degli NPC sostitutivi.
- La factory può restituire None se la richiesta
  non era esplicita con `only_if_explicit=True`;
  non dedurre che tutti i job sostituiscano sempre.

**Nuovo modulo NON installato:**
`src/m108_native_roster/mhs108_no_show_guard.py`.

L'adattatore intercetta **soltanto**
`BouncerRequest.clone_for_replace` e restituisce None
per richieste che sono ancora attivamente riconosciute da
`SchoolFilterScope.is_tracked(request)`, con l'ID preciso,
`sim_constraints={requested_id}`, senza fallback di
constraints, stessa zona scolastica/giorno/save/ruolo.
Tutte le richieste non monitorate, incluso lo staff EA,
mantengono il metodo originale. Non modifica
`BaseSituation.on_sim_unassigned_from_request`, quindi
la rimozione del Sim assente/partito rimane EA originale.

Sono richiesti cinque flag runtime di verifica esterna
prima dell'installazione, ma **non esiste alcun chiamante
nella mod rilasciata che li soddisfi**. Nessuna beta.
Un test offline che imposta tali flag artificialmente
verifica il comportamento dello stub, non la compatibilità
con la versione corrente di The Sims.

`tests/test_m108_no_show_guard.py` copre:
- no-show studente Base iscritto (senza clone casuale);
- abbandono dello studente con rimozione dal fake situation
  ma senza reinvito di un NPC;
- tutti e cinque gli ID Core scelti in entrambi i percorsi;
- docenti, NPC esterni, auto-fill senza ID, richieste errate,
  scuola o giorno diversi lasciati invariati;
- doppia installazione rifiutata, uninstall ripristina
  il comportamento originario;
- nessuna pretesa di successo in-game.

Il file di test è incluso nel job GitHub Actions Python 3.7
`capacity_mac_beta` e in `roster`; verificare lo stato CI.

**Punto non risolto:** proteggiamo soltanto i cloni
dei request *già tracciati*. Se un invito non entra nel
`SchoolFilterScope`, se EA genera un AUTO_FILL a monte,
o se lo fa passare da un altro percorso, questa protezione
non basta. Restano il filtro native reale, il conteggio
Base 6→8, i job delle due classi e il cap NPC.

**Prossima implementazione sensata:** gate anti-AUTO_FILL
sulle situazioni Core/Base e misurazione esatta dei
`WeeklyScheduleDay` per poter programmare 8 chiamate
Base EA originali senza creare nuove situazioni manuali.

## Avanzamento M108 — conteggio Base EA 6 → 8, senza nuove situazioni manuali

### Prova dal tuning originale EA

I file `assets/ea_2026_11_01/277657.xml` (calendario liceo Main)
e `assets/ea_2026_11_01/279958.xml` (FromVenue) impostano
`situation_HighSchool_Active_NPC_Base_Student` (277733)
con `count.lower_bound=6`, `upper_bound=6`.
La Core 298052 viene dopo la Base nel calendario.
I `count_modifiers` possono influenzare il valore che il
metodo `WeeklyScheduleDay.get_long_term_situation_count`
restituisce nella specifica partita e non vanno ignorati.

### Nuovo codice scritto

`src/m108_native_roster/mhs108_native_base_count.py`:

- Riutilizza **lo stesso classmethod EA** individuato
  dalla M96 (`get_long_term_situation_count`); non
  crea situazioni esterne, non aggiunge nuovi controller
  al calendario e non installa mod nel gioco.
- La `propose_native_base_count` può restituire
  `(8,8)` per le sole situazioni Base 277733
  dei due calendari 277657 e 279958.
- Richiede il **piano esatto 3 giocabili + 5 Core + 8 Base**,
  i cinque ID Core trattenuti prima della prima
  richiesta EA, nessun tentativo di invito già
  emesso e nessun duplicato.
- Contesto richiesto: stessa zona/save/giorno/scuola,
  origine calendario verificata, attuazione prima
  dell'inizio del calendario, corrispondenza ESATTA
  fra il GUID del calendario ricevuto dal classmethod
  e quello del contesto.
- Non impone ciecamente `(8,8)` a ogni originale.
  Occorre una prova esterna del numero di modificatori
  playable effettivamente già applicati: solo se
  `original==(6 - modifier,6 - modifier)`,
  con modifier intero 0..3 esplicitamente verificato,
  il nuovo valore viene proposto. In caso contrario
  il ritorno originale EA è preservato.
- `install_offline_only` è **disabilitato dalla build**
  ed esige 8 gate runtime che non sono ancora verificati.
  Rifiuta l'installazione contemporanea degli hook
  `_mhs96_count_hook`, `_mhs105_schedule_audit`
  e di un secondo `_mhs108_count_hook`.
- Il classmethod originale è chiamato una volta sola
  e il wrapper offre `uninstall` senza lasciare
  la modifica attiva su altri calendari.

**Test:** `tests/test_m108_native_base_count.py`
prova il calcolo 6→8, i modifier 0,2,3,
l'assenza di esterni e duplicati, contesti incoerenti
Main/FromVenue, fallimento provider, precedenti hook
M96/M105, classe ereditata, rollback e verifica che
la richiesta 8 non sia scambiata per presenze 8/8.
Il file è aggiunto alla CI `capacity_mac_beta`
(Python 3.7) e al `unittest discover` generale.

### Stato corretto

Questo è **codice di proposta e unit test**, non
una modifica di tuning EA applicata al salvataggio.
La proposta `(8,8)` non prova che EA abbia davvero
creato le 8 situazioni e non risolve il limite di
6 per la fase di Classe 1 né il cap del lotto.
Il prossimo passo utile sarà un'**integrazione
atomica del calendario con la pre-create guest list**
e una verifica esplicita delle situazioni effettivamente
create. Poi occorre risolvere la distribuzione
nelle due aule; solo allora valutare una beta Mac.

**Nessuna installazione o test nel gioco richiesti ora.**
`main` e i salvataggi restano invariati.

### Test integrato finale del conteggio (offline)

È stato aggiunto anche un test che avvia insieme
`mhs108_native_base_count.install_offline_only` e
`mhs108_native_precreate.install` su mock EA:
il primo restituisce esattamente otto chiamate Base,
il secondo assegna ID ai loro otto guest list native,
rifiuta la nona chiamata random, poi crea la situazione
Core con gli altri cinque ID. Convalida 13/13 ID
distinti e preserva lo stesso tipo di situazione EA.
È un **contratto di codice simulato**, NON una prova
che il motore EA accetti o faccia apparire 13 NPC.
La CI GitHub dell'ultimo commit risultava **queued**
al momento della verifica (non superata).
