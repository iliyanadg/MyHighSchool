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

## Avanzamento M108 — smistamento dei 16 iscritti nelle lezioni (SOLO offline)

**Nuovo modulo:** `src/m108_native_roster/mhs108_lesson_phase_policy.py`.

Analizzati i sei dati originali `WeeklyScheduleSituationData` in
`assets/ea_2026_11_01`:

| Dato EA | Momento | Classe MHS | Situation EA | Job alunno | Max NPC tuning |
|---|---|---|---|---|---|
| 293642 | Vai in classe, con trait | 1 | 293815 | 277919 | 6 |
| 293644 | Vai in classe, senza trait | 1 | 304701 | 277919 | 6 |
| 297773 | Vai in classe, altri | 2 | 297774 | **277919** | 8 |
| 304561 | Lezione, senza trait | 1 | 304703 | 277919 | 6 |
| 304563 | Lezione, con trait | 1 | 304565 | 277919 | 6 |
| 304570 | Lezione, altri | 2 | 304567 | **280777** | 8 |

**Punto nuovo fondamentale:** nella fase *Vai in classe*, anche
la situation "Others" usa il job **277919**. Il Job ID da solo
NON determina l'aula. Serve la combinazione
`phase_data_guid + situation_guid + job_guid + SimID iscritto`.
Le due varianti Classe 1 con/senza trait nascosto **sono lo
stesso gruppo MHS**, non due classi diverse. Non assegnare
il trait EA 293779 a caso.

La fase "Others" Lezione 304570 include anche **job docente
277918** e **preside 278224**. La policy isola soltanto
il job studente 280777, non altera il personale.

**Finestre EA mantenute:** 09:30 "Vai in classe",
10:00 Lezione, 13:30 "Vai in classe", 14:00 Lezione.
La policy è applicabile solo a queste finestre e ai due
calendari liceo verificati 277657/279958.

**Conteggio autentico per classe (non 8 NPC ciascuna):**
`need_npc_class = 8 - enrolled_playable_in_class`.
Esempio: 1 giocabile Classe 1 significa 7 NPC Classe 1;
2 giocabili Classe 2 significa 6 NPC Classe 2.
La vecchia Classe 1 con limite 6 ha quindi **almeno un posto
mancante** nel tuning nominale (oltre ai modificatori EA, che
possono ridurre ulteriormente). In un gruppo senza giocabili
la Classe 1 può richiedere **8 NPC**: mancano fino a due posti.
Non è dimostrato che una semplice modifica del cap
porti 8 alunni a lezione.

**Nuove funzioni della policy:**
- `propose_phase_students` convalida tutto il
  manifesto 3 giocabili/5 Core/8 Base senza modificarlo;
  legge registrazione 8+8, save, giorno, zona, calendario,
  fase, native situation e job; esige come input liste
  **osservate in-game** di Sim presenti, partecipanti
  effettivi a EA school situation ed eleggibilità dei
  test di fase. Propone solo NPC della classe scelta.
- Indica specificamente `REGISTERED_STUDENT_ABSENT`,
  `EA_SCHOOL_ROLE_MISMATCH`,
  `NATIVE_PHASE_ELIGIBILITY_BLOCKED`,
  `NATIVE_PHASE_CAPACITY_BLOCKED`,
  `PROPOSED_NOT_EA_ASSIGNED`. Non inventa NPC
  sostitutivi e non sposta uno studente di classe.
- `assess_native_phase_result` distingue appartenenza
  ai job di fase EA da **alunni seduti davvero**.
  Richiede liste di job realmente osservate, aggregate
  sulle due varianti Class1 WithTrait/NoTrait;
  una proposta senza osservazione non passa.
- Si tratta di una **politica Python priva di effetti**:
  non chiama EA `try_start`, non scrive tuning, non crea
  situazioni e non porta Sims in aula.

**Test aggiunti:** `tests/test_m108_lesson_phase_policy.py`:
- confronta GUID, job, situations e limiti di **tutti e 6
  gli XML originali EA**, non soltanto fake;
- prova tutte le quattro finestre e le distribuzioni
  playable 1+2, 2+1, 0+3 (senza cambiare i cinque
  ruoli Core scelti);
- esclude gruppi/salvataggi/ore sbagliati, extra casuali,
  studenti mancanti, trait scambiati per iscrizione,
  personale e manifesti modificati;
- separa appartenenza native EA, presenza e verifiche dei
  posti realmente occupati.

**Limite attuale da NON occultare:** la policy identifica
il punto di blocco ma non è ancora un hook capace di
superare i test trait/upper bound di
`WeeklyScheduleSituationData.try_start`.
Prima della prossima beta serve una soluzione che agisca
**all'interno dell'assegnazione EA** per i soli SimID
della classe e preservi i due job del personale.
Dopo di ciò, occorre un test integrato unico
prima di reclamare le presenze 16/16.

GitHub Actions dell'ultimo commit va controllato:
**nessun test M108 viene dichiarato superato soltanto
perché è stato inviato**. `main` e il gioco restano intatti.

### Punto d'aggancio EA delle lezioni: codice originale recuperato dalla Library

Recuperato **senza chiedere nuovi file all'utente** il suo
`weekly_schedule_zone_director.py` dalla Library: metodo
`WeeklyScheduleSituationData.try_start(cls, sims, sim_info,
duration, additional_sim_ids, situation_job_count)`.

Comportamento originale verificato nel sorgente EA:
1. Calcola un `modified_upper_bounds` per job,
   sottraendo i conteggi delle situazioni e dei job
   indicati dagli `upper_bound_count_modifiers`.
2. Scorre i Sim istanziati nell'insieme `sims`, e **per ogni Sim** valuta prima i job che non hanno ancora raggiunto il requisito minimo, poi quelli con minimo già raggiunto.
   Per ogni Sim usa `DoubleSimResolver` ed esegue
   `job_entry.tests.run_tests(resolver)` della fase EA.
3. Crea **una sola** `SituationGuestList(invite_only=True)`
   con gli ID selezionati e la passa al
   `SituationManager.create_situation(...,
   spawn_sims_during_zone_spin_up=True)`.
4. **Solo se** `situation_id is not None` esegue
   `sims.difference_update(assigned_sims)` e aggiorna
   `situation_job_count`.
5. Per `304570` non si può eliminare il personale
   dalla lista delle candidature, perché la stessa
   situazione contiene job dei professori e del preside.

**Nuovo modulo disattivato:**
`src/m108_native_roster/mhs108_ea_phase_adapter.py`.
Intercetta solo il classmethod EA `try_start` e solo
per i sei `phase_data_guid` scolastici già verificati.
Su contesto attivo e validato:
- convalida GUID situazione+job del tuning runtime;
- richiede osservazioni di 16 iscritti presenti, ruoli
  EA, idoneità di fase e staff;
- seleziona in un **set locale** soltanto gli NPC
  iscritti alla specifica classe, e aggiunge gli ID
  staff verificati SOLO nelle fasi "Others" che
  possiedono job del personale;
- chiama il metodo EA originale **una volta sola**;
- se EA ritorna una situation ID, propaga al set
  originale soltanto le rimozioni effettivamente
  eseguite dal metodo nativo; altrimenti lascia
  il set originale intatto;
- se gli otto iscritti o i requisiti non sono
  verificati, non crea situazioni scolastiche
  casuali né modifica tratti; restituisce None
  per quella fase verificata ma non autorizzata;
- su evento non scolastico, o mod MHS non attiva,
  il comportamento EA rimane originale.

`tests/test_m108_ea_phase_adapter.py` testa il
percorso EA simulato, l'ordine corretto dei candidati,
il personale, l'isolamento degli altri eventi,
l'assenza di rimozione dei Sim senza creazione,
il blocco per Classe 1 con richiesta 7/6,
il contesto inattivo, gli errori di tuning,
la doppia installazione e il ripristino.

**NON è ancora una release.** I flag runtime
`REQUIRED_LIVE_GATES` sono una simulazione nei test
e non hanno ancora un provider verificato nel gioco.
Il metodo originale usa ancora i test con trait
e i modificatori: per le varianti Classe 1 bisogna
coordinare entrambe le istanze e risolvere il
cap 6 senza spostare NPC o cambiare personalità.
Non affermare che gli otto studenti siano seduti
perché una situazione EA è stata creata.

Il prossimo controllo necessario è far combaciare
le due varianti `WithTrait/NoTrait` con un budget
totale di Classe 1 e proteggere i job docente
durante la selezione, quindi la validazione di
capienza fisica NPC e delle presenze nel salvataggio.

## M108 — capienza Classe 1 e percorsi EA WithTrait / NoTrait

**Intervento codice completato (offline); nessuna nuova beta da installare.**

Fonte EA effettiva già fornita dall'utente:
`venues/weekly_schedule_zone_director.py` della sua Library,
e tuning XML `293642, 293644, 304563, 304561`
in `assets/ea_2026_11_01`.

### Scoperta decisiva verificata sul sorgente originale

`WeeklyScheduleSituationData.try_start` applica
`modified_upper_bounds` sottraendo i conteggi già
presenti in `situation_job_count`. La Classe 1 ha
**DUE percorsi per un'unica aula MHS**:
- **GoToClass1 WithTrait 293642**, sit 293815, job
  277919, massimo tuning 6; sottrae il numero nel
  player job `(284555,278117)`.
- **GoToClass1 NoTrait 293644**, sit 304701, stesso
  student job 277919 e limite 6; sottrae player
  `(284555,278117)` **e** gli NPC del WithTrait
  `(293815,277919)`.
- **AttendClass1 WithTrait 304563**, sit 304565,
  massimo 6; sottrae player `(276681,278117)`.
- **AttendClass1 NoTrait 304561**, sit 304703,
  massimo 6; sottrae player `(276681,278117)` e
  NPC del WithTrait `(304565,277919)`.

La corrispondenza di questi quattro insiemi di
modificatori è ora verificata da test che leggono
gli **XML EA reali**.

**Non confondere i tre playable della famiglia con il numero di
playable della Classe 1.** Il job EA player-phase
può includere i Sim giocabili di entrambe le aule.
Quindi sostituire un `upper_bound` 6 con 8
senza guardare i modificatori è sbagliato.

### Nuovo contatore a ID fissi

`src/m108_native_roster/mhs108_class1_dual_route_budget.py`:

- Ricostruisce e verifica il manifesto immutabile
  **16 iscritti / 3 playable / 5 Core / 8 Base**;
- per una sola delle quattro finestre EA (09:30,
  10:00, 13:30, 14:00) verifica 16 ID sul lotto e
  nelle situazioni scolastiche e gli ID dei
  playable attualmente nella fase player EA;
- per il percorso richiesto legge *i conteggi veri*
  di player job e WithTrait job, e gli ID che
  superano i veri test del percorso EA;
- prenota nel piano solo gli NPC non ancora presi
  dall'altro percorso della stessa aula, senza
  cambiare il tratto nascosto `293779`;
- propone una **capienza specifica per questa singola
  chiamata**, non un nuovo limite globale:
  `upper_proposto = playable_gia_contati_da_EA
    + with_trait_precedenti_se_NoTrait
    + NPC_idonei_rimasti_per_questa_chiamata`.
  I modificatori EA, sottratti dall'originale,
  lasciano esattamente i posti richiesti;
- registra il risultato solo dopo il ritorno
  positivo della situazione EA **e un riscontro
  dei singoli ID**, senza chiamarlo presenza;
  su risultato parziale/sbagliato o errore
  blocca il resto della fase, non sostituisce;
- consente che un percorso non abbia alcun
  candidato, ma non considera completa la
  classe finché entrambi sono terminati e il
  gruppo assegnato coincide con tutti gli NPC
  previsti dall'iscrizione;
- non assume quale percorso venga primo:
  i `WeeklyScheduleSituationSet` specifici
  non sono ancora stati verificati per l'ordine.

**Esempio concreto**: 1 playable in Classe 1,
2 in Classe 2; devono entrare **7 NPC Classe 1**.
Se il primo percorso prende 2 NPC, con 3
playable globali già contati:
- WithTrait: `upper` proposto **5** − 3 = **2 NPC**;
- NoTrait: `upper` proposto **10** − 3 − 2
  precedenti = **5 NPC**;
- totale 2+5 NPC + 1 playable Classe 1 = **8**
  iscritti della Classe 1, senza duplicati.
Questo è un calcolo di capienza, **non** la prova
che EA abbia eseguito le due situazioni.

### Proiezione per-call senza modifiche globali

`src/m108_native_roster/mhs108_class1_shadow_cap.py`
genera una classe Python temporanea e separata
che riprende il job, il SimFilter test di fase,
le references ai modificatori, la situation
EA e l'identità testuale di `creation_source`,
ma usa il `upper_bound` calcolato per una
singola chiamata. **Non cambia il tuning EA in
memoria, nel package o nel save.**

Il suo utilizzo effettivo con il metodo EA
`WeeklyScheduleSituationData.try_start` è
**ancora una tecnica da verificare sul runtime**:
il proxy non è la vera classe con metaclass
`HashedTunedInstanceMetaclass`; un unit test verde
NON conferma la compatibilità nativa.
Non installare il proxy nel gioco prima della
verifica del tipo e delle condizioni d'invocazione.

### Test e stato della release

- `tests/test_m108_class1_dual_route_budget.py`
  verifica i quattro tuning originali, numero
  playable in Classe 1 = **0 / 1 / 2**, l'assenza
  di alunni con trait, entrambi gli ordini dei
  percorsi, contatori EA incoerenti, roster
  manipolato/invalidato, nessun riempimento casuale.
- `tests/test_m108_class1_shadow_cap.py`
  verifica che la proiezione conservi gli oggetti
  di test, situation, job e modificatori EA,
  che il cap calcolato differisca dall'originale,
  che l'originale rimanga intatto e che tuning
  diversi o cambiati vengano rifiutati.
- I test sono iscritti alla job
  `capacity_mac_beta` in Python 3.7 e al
  `unittest discover` generale. La CI
  dell'ultimo commit risultava **queued**:
  non dichiarare alcun PASS ancora.

**Limite residuo:** i moduli di calcolo e di
proiezione non sono ancora invocati dal
`mhs108_ea_phase_adapter.py` nella versione
installabile, né abbiamo dimostrato che EA
accetti lo shadow tuning. Il vecchio adapter
blocca correttamente la Classe 1 7/6, invece
di inventare un superamento del cap.

**Prossimo passo tecnico:** unire in modo
sperimentale (solo offline) il calcolo condiviso
con `try_start`, leggendo il `situation_job_count`
EA e le reali idoneità per percorso, con copia
temporanea non globale dei `job_assignments`.
Poi servirà anche la prova di capienza del lotto,
dei 16 partecipanti, e delle posizioni in aula.
Solo dopo si valuterà una beta Mac.

`main` e il save della giocatrice restano intatti.

## M108 — collegamento sperimentale Classe 1 8 posti al metodo EA try_start

**Codice aggiunto al ramo sperimentale; NON una build del gioco.**

`src/m108_native_roster/mhs108_class1_try_start_bridge.py`:
- Intercetta ESCLUSIVAMENTE il classmethod nativo
  `WeeklyScheduleSituationData.try_start` per i quattro
  data GUID di Classe 1: 293642/293644 (09:30 o 13:30)
  e 304563/304561 (10:00 o 14:00).
- L'integrazione rifiuta automaticamente di sovrapporsi
  all'altro hook `_mhs108_exact_phase`; la protezione
  è stata aggiunta anche nell'altro verso a
  `mhs108_ea_phase_adapter.py`. Non creare due controller
  paralleli su `try_start`.
- Usa lo STESSO `ClassOneDualRouteBudget` per entrambi
  i percorsi della medesima finestra; un'istanza nuova per
  ogni finestra oraria (09:30, 10:00, 13:30, 14:00).
  Il controller deve validare save/giorno/zona.
- Legge i conteggi usando gli OGGETTI EA originali
  `(modifier.situation, modifier.job)` dal vero
  `situation_job_count`, SENZA creare nuove voci
  nel `defaultdict`: usa `.get(key,0)`.
  Solo dopo converte le coppie in GUID numerici
  per confrontarle col planner. 
- Usa `budget.prepare(...)` con gli ID che passano i
  TEST ORIGINALI della specifica route (trait o
  no-trait) per scegliere esattamente i rimanenti NPC
  della Classe 1; controlla i modificatori dei playable
  e i job precedentemente assegnati.
- Crea una VISTA temporanea tramite
  `project_class1_tuning`, mai un nuovo tuning EA
  registrato, mantenendo test/ruoli/stato EA originali,
  ma col `upper_bound` adatto a quella sola chiamata.
- Filtra una COPIA del set Sim condiviso ai SOLI ID
  previsti; passa questa copia e la vista al metodo
  ORIGINALE `try_start` una volta sola.
- Se EA assegna esattamente tutti gli ID richiesti e
  incrementa di quel numero il conteggio nativo del
  SituationJob specifico, `budget.confirm` registra
  la route e il wrapper rimuove gli assegnati anche
  dal set condiviso. Non asserisce che essi siano
  veramente seduti in aula.
- Route con ZERO candidati: nessuna situazione EA
  viene creata. Fallimento o risultato incompleto:
  il budget blocca le route successive, nessun
  nuovo invito casuale viene preparato.
  Se una situazione EA è già stata creata con
  risultato parziale, il wrapper restituisce
  il suo ID per non indurre ulteriori tentativi
  del motore, senza fingere di poter annullare
  gli effetti già avvenuti.
- Nessun codice runtime chiama
  `install_offline_only`; nove gate esterni sono
  tutti ancora non dimostrati. Non dichiarare
  "Classe 1 funzionante" senza prova reale.

**Test aggiunti:**
`tests/test_m108_class1_try_start_bridge.py`
simula il vero ordine del method/classmethod EA:
- prima WithTrait 2 Sim e poi NoTrait 5 Sim →
  tutti i 7 NPC della Classe 1 iscritti e nessun doppione;
- route NoTrait per prima, successiva WithTrait vuota;
- nessuno dei 7 passa WithTrait, tutti passano NoTrait;
- due giocabili nella Classe 1 → solo 6 NPC richiesti;
- situazione EA già creata ma con risultati parziali
  → blocco, nessuna rimozione fittizia dal set
  condiviso e nessuna seconda chiamata EA;
- rifiuto dei modificatori player incoerenti,
  fallimento creazione senza retry, isolamento
  degli altri eventi e uninstall;
- hook generico M108 e hook dual-route NON
  devono potersi installare insieme.

La CI Mac Python 3.7 include il nuovo file di test;
verificare l'ultimo run del ramo in GitHub Actions.
Il job `roster` lo include tramite `unittest discover`.

**Blocchi runtime ancora aperti:** verificare con
l'EA originale che la classe temporanea possa
essere passata a `try_start` senza violare i
requisiti della sua metaclasse; garantire
le osservazioni reali delle eligibilità/filtri e
dei conteggi dei job; verificare la capienza
fisica del lotto; contare 16 NPC+playable realmente
assegnati e seduti nelle due aule.
La Classe 2 resta gestita dall'altro adapter
solo nei test: serve un controller unico di
installazione che scelga un solo wrapper per
entrambe le classi, senza doppie patch al
metodo nativo. Nessuna beta installabile ancora.

`main` e il salvataggio sono rimasti intatti.

## M108 — unico controller delle lezioni Classe 1 e Classe 2

**Codice scritto; SOLO test offline. Nessun hook installato in The Sims 4.**

Nuovo modulo:
`src/m108_native_roster/mhs108_unified_lessons.py`.
Nuovi test: `tests/test_m108_unified_lessons.py`, presenti
anche nel job Mac Python 3.7 `capacity_mac_beta` e nel
`unittest discover` generale.

**Un solo wrapper EA** su
`WeeklyScheduleSituationData.try_start`, non due controller
in competizione. Rifiuta installazione se sono già
presenti `_mhs108_exact_phase` (vecchio adapter),
`_mhs108_class1_bridge` (prototipo Classe 1) o un'altra
istanza `_mhs108_unified_lessons`. Sono tre *strategie
alternative*, non da abilitare contemporaneamente.

Percorsi gestiti:
- Classe 1 WithTrait e NoTrait, 09:30/13:30
  (293642/293644), 10:00/14:00 (304563/304561):
  riutilizza lo stesso `ClassOneDualRouteBudget` per
  entrambi i percorsi e proietta il cap per chiamata
  con `project_class1_tuning`.
- Classe 2 preparazione 297773 e lezione 304570:
  usa il job studente originale 277919 per
  preparazione e 280777 per lezione;
  non modifica il suo limite nativo 8.
- Non tocca richieste estranee a quei sei snippet
  EA, senza creare situazioni, rinominare classi,
  distribuire tratti o cambiare EA schedule.

**Protezione staff:** la fase "Others" richiede
l'esatto layout di job EA e gli ID del personale
certificati per *ciascun* job:
`277918` insegnanti (massimo due) e, nella
fase 304570, `278224` preside (uno).
Niente generica whitelist di staff usata anche
per altri ruoli.

**Nuovo requisito fondamentale dopo original EA:**
il risultato `situation_id` non basta. Occorre
che un provider leggibile dal motore reale produca
un riscontro nativo `ids_by_job` legato alla
specifica situazione appena creata, da confrontare
con gli ID selezionati per OGNI job.
Questo rileva scambio insegnante/studente anche
quando il numero totale di Sim è identico.
Solo l'esito completo consente di togliere dal
set condiviso dei candidati gli ID consumati
nel metodo nativo; nessuna assegnazione fittizia
in una classe.

**Blocchi duplicati:** una situazione di lezione
verificata viene tentata al massimo una volta per
`(slot, giorno, zona, finestra, phase_data_guid)`
nel singolo controller. Se il metodo EA ha creato
la situazione ma il riscontro dei job è sbagliato,
il wrapper RESTITUISCE l'ID della situazione
per evitare retry (non può però annullare
retroattivamente gli effetti EA già avvenuti)
e segna il blocco, senza dichiarare riuscita
la classe. I tentativi successivi sono negati.

**Test nuovi** (NON prova runtime):
- Classe 2 + due percorsi Classe 1 nella stessa
  fase, 13 NPC scolastici unici e staff esatto;
- entrambi i passaggi `prepare` e `lesson`;
- dipendenza dai due professori e dal preside
  identificati dal relativo SituationJob;
- stesso numero di ID ma job studente/docente
  scambiati: rifiuto dopo `create_situation`;
- fallimenti/assegnazioni parziali: niente
  rimozione fittizia dal set EA condiviso, niente
  seconda richiesta EA;
- niente doppio hook e nessuna interferenza
  con situazioni estranee al liceo.

**Sicurezza/runtime ancora NON verificati:**
1. Proiezione Class1 con metaclasse EA reale
   (il test usa classi Python simulate);
2. provider reale per il contesto
   save/day/zone/fase, source e idoneità EA;
3. lettura attendibile degli ID effettivi
   PER JOB dalla situazione dopo la sua creazione;
4. controllo reale del cap del lotto, Bouncer,
   no-show/fallback e presenza 16/16;
5. tre giocabili a lezione nelle aule registrate
   e posti fisici/blackboards: il solo job NPC
   non prova il percorso del giocabile.
6. coordinamento dell'intera catena M108 (inviti,
   8 Base, Core, filtri, protezione no-show e
   lezioni) in una sola build sicura.

**Conclusione:** l'integrazione tra le due aule
esiste ora come codice sperimentale con un wrapper
unico, ma NON è un pilot giocabile. Non proporre
ancora installazione sul save reale. `main` è
rimasto intatto.

## M108 — audit nativo dopo il Bouncer + margine di capienza NPC

**Intervento del 3 novembre: codice scritto e test offline aggiunti.**
Non modificare `main` e non distribuire una beta M108.

### Scoperta sul sorgente EA originale

Durante lo zone spin-up:
1. `SituationManager.on_all_situations_created_during_zone_spin_up`
   chiama `bouncer.request_all_sims_during_zone_spin_up`.
2. `SituationManager.on_all_sims_spawned_during_zone_spin_up`
   chiama `bouncer.assign_all_sims_during_zone_spin_up`
   e imposta `_sim_assignment_complete=True`.
3. `BaseSituation.on_sim_assigned_to_request` aggiunge
   effettivamente il Sim alla situazione e al suo job.
4. Il source EA espone `SituationManager.get(situation_id)`,
   `BaseSituation.all_jobs_gen()`,
   `all_sims_in_job_gen(job_type)` e
   `all_sims_in_situation_gen()`.

**CONSEGUENZA:** il risultato immediato di
`WeeklyScheduleSituationData.try_start` è un invito
EA, NON una prova che il Bouncer abbia assegnato
effettivamente gli studenti. Chiedere la membership
subito dopo `create_situation` può produrre
falsi negativi durante lo spin-up e un falso
senso di successo. Servono due passaggi distinti:
invito pianificato PRIMA, verifica job DOPO il Bouncer.

### Modulo read-only per i job effettivamente occupati

`src/m108_native_roster/mhs108_post_bouncer_audit.py`
(`NativeJobAudit`):
- registra una situazione **appena creata** come
  `CREATED_AWAITING_BOUNCER`, mai come presenza;
- accetta solo le sei situazioni native di
  preparazione/lezione MHS già verificate per
  **Class1 e Class2**, la finestra EA corretta,
  il roster 3+5+8, save, giorno, zona, job
  alunno EA originale e gli eventuali job docente
  e preside permessi;
- vieta inviti di studenti estranei o di classe
  sbagliata, e lo stesso NPC invitato in due
  situazioni concorrenti della stessa fase;
- richiede un segnale certificato che l'assegnazione
  Bouncer sia effettivamente terminata, invece di
  dedurla dal `situation_id`;
- usa le API native sopra per leggere gli
  **ID realmente presenti in ciascun job**, il set
  completo dei membri e gli eventuali membri extra;
- se un docente è stato inserito come studente o
  compare un diciassettesimo iscritto, restituisce
  esito negativo anche quando i conteggi tornano;
- mantiene `seating_verified=False`: essere assegnati
  a un job scolastico non prova l'uso dei banchi
  o della lavagna della classe assegnata.

**Test:** `tests/test_m108_post_bouncer_audit.py`
copre attesa pre-Bouncer, ruolo docente/studente
invertito, ID sconosciuti, job duplicati, due
route Class1 senza doppioni, fasi/mondi/salvataggi
sbagliati, e uso delle API EA in sola lettura.

### Modalità differita nel controller unico

`src/m108_native_roster/mhs108_unified_lessons.py`
accetta una nuova opzione **spenta per default**
`deferred_native_audit`.

- Dopo `try_start` controlla la creazione e
  gli ID sottratti dal set temporaneo di candidati
  EA, e registra gli inviti nell'audit nativo;
  NON li chiama già assegnati dal Bouncer.
- Il contatore condiviso Classe 1 può impegnare
  gli ID nel **piano degli inviti**, per fare
  procedere la seconda route EA, ma NON può
  convertire da solo tale riserva in presenza
  reale.
- Solo una chiamata successiva e verificata
  `NativeJobAudit.observe` dopo il Bouncer
  può trasformare le situazioni da pending a
  `NATIVE_JOBS_MATCH`.
- Il controller di integrazione mantiene il
  vincolo di una chiamata EA originale per
  fase e il blocco di doppia installazione.
- Aggiunte protezioni **bidirezionali** affinché
  gli adapter M108 legacy non possano essere
  installati neppure *sopra* il controller unico.

**Test:** `tests/test_m108_deferred_unified_lessons.py`
simula due route Classe 1, Classe 2 e staff:
prima tre ID di situazione ancora in attesa,
poi assegna job esatti dopo il Bouncer; prova
inoltre che l'assegnazione scambiata docente/
studente fallisce e non viene ritentata.

**Attenzione:** manca un provider runtime verificato
che richiami l'audit al momento giusto sia durante
lo spin-up sia durante le lezioni avviate a scuola
già caricata. I flag dei test sono sintetici.
Il sistema non è ancora un .ts4script giocabile.

### Nuova scoperta Bouncer EA: capienza non è un numero fisso

L'originale `bouncer.py`, metodo
`_monitor_npc_soft_cap`, usa:
- `sim_spawner_service.number_of_npcs_instantiated`;
- `sim_spawner_service.number_of_npcs_leaving`;
- `sim_spawner_service.npc_soft_cap`.

Quando il cap è SUPERATO, accelera le partenze
o ordina ad NPC di uscire. **Anche all'uguaglianza
esatta col cap**, se esiste una richiesta non
soddisfatta con priorità superiore a un incarico
già assegnato, EA può far uscire l'NPC occupato.
Le reservation requests originali possono inoltre
modificare il cap NPC. NON assumere per il liceo
un massimo universale arbitrario di 20 Sim e
NON forzare `cap_cheat`.

`src/m108_native_roster/mhs108_npc_soft_cap_audit.py`
è un controllo read-only che:
- considera **13 adolescenti NPC iscritti**,
  più gli ID verificati di tutto il personale
  scolastico NPC (nella configurazione corrente,
  per esempio 2 docenti + preside + mensa +
  custode = 18 NPC scolastici);
- include nel numero misurato anche tutti gli
  altri NPC presenti sul lotto, non soltanto
  studenti e personale della mod;
- verifica la zona, salvataggio, giorno, contatori
  EA reali e gli eventuali studenti/personale
  già segnati come `leaving`;
- calcola il carico dopo i convocati ancora mancanti
  e ammette un margine **strettamente positivo**;
- segnala sia `SCHOOL_NPC_SOFT_CAP_SHORTFALL`
  sia `SCHOOL_NPC_SOFT_CAP_AT_LIMIT`, senza
  modificare il cap o espellere personaggi;
- non chiama un margine positivo prova di
  presenza o di posto in aula: è solo una
  fotografia di sicurezza a quell'istante.

**Test:** `tests/test_m108_npc_soft_cap_audit.py`
include 13+5 NPC, altri visitatori, studenti
mancanti, NPC in uscita, cap raggiunto, contatori
EA non verificati, margine positivo o negativo.

Tutti e tre i nuovi test sono iscritti alla CI
Python 3.7 Mac; verificare il risultato del run,
non dichiararlo superato prima dell'esecuzione.

### Prossimo blocco reale

Collegare l'evento reale di
`SituationManager.on_all_sims_spawned_during_zone_spin_up`
(e un percorso sicuro per le lezioni iniziate
dopo il caricamento) alla sola lettura
`NativeJobAudit.observe`, senza modificare
il Bouncer. Occorre poi un audit unico per i
16 adolescenti effettivamente presenti, i tre
giocabili e gli 8+8 studenti nelle due aule,
oltre alla capienza fisica/route e banchi.

## M108 — audit del Bouncer collegato e riconciliazione dei 16

**3 novembre: interventi sul ramo sperimentale, NON build giocabile.**

### Nuovi moduli e correzioni

1. `mhs108_spinup_barrier.py`: osservatore **disattivato**
   sul vero `SituationManager.on_all_sims_spawned_during_zone_spin_up`.
   Richiama UNA SOLA VOLTA il metodo EA originale e, solo
   **dopo** che ha concluso l'assegnazione Bouncer e la fonte
   save/day/zone è verificata, consulta in sola lettura
   `NativeJobAudit.observe` per tutte le situazioni di fase
   in attesa. Non installa Bouncer hacks, non crea nuove situazioni
   e non pretende di coprire gli assegnamenti successivi
   delle lezioni a zona già attiva.
2. `mhs108_post_bouncer_audit.py` ha un manifesto 3+5+8
   ricostruito in modo canonico e controlla le situazioni EA
   autorizzate, i job corretti, le finestre orarie, le due
   Class1 route disgiunte, i membri estranei e i job staff.
   Il risultato negativo ora conserva il riferimento alla
   fase, così un errore non viene escluso dall'audit complessivo.
   Espone anche i receipt in attesa e quelli verificati
   senza attribuire loro presenze inventate.
3. `mhs108_16_student_reconciliation.py`: collega
   **soltanto dati di assegnazione EA già verificati**
   con tre prove indipendenti:
   - tutti i **13 NPC iscritti** nei job di fase originali
     delle rispettive classi (due route Classe 1 sommate);
   - esattamente i **3 adolescenti giocabili** nei job
     PLAYER EA realmente osservati;
   - esattamente i **16 adolescenti iscritti sul lotto**,
     nessun estraneo e nessuna situazione extra di aula
     non monitorata dal readback.
   Restituisce
   `EXACT_NATIVE_16_STUDENTS_ASSIGNED_NOT_SEATED`
   solo quando sono soddisfatte tutte le condizioni.
   **Posti effettivamente occupati e lezioni 8+8
   restano verifiche separate**; nessun rapporto su una
   sola fase garantisce automaticamente l'intera giornata.
4. `mhs108_npc_soft_cap_audit.py` distingue la situazione
   **sopra cap** da quella **esattamente al cap**:
   EA `Bouncer._monitor_npc_soft_cap` può fare uscire NPC
   anche alla soglia, quando un'altra richiesta ha una
   priorità maggiore. Richiede margine strettamente
   positivo senza usare `cap_cheat`.
5. Corretto `mhs105_live_core_binding.py`, che ometteva
   il metodo **reale** di EA
   `BaseSituation.get_current_job_for_sim`. L'ispettore
   Core ora lo prova per primo, senza eliminare fallback.
6. Corretto il confronto fra `NativeJobAudit.manifest`
   e `mhs108_unified_lessons.install_offline_only`:
   confronta il **valore canonico** anziché l'identità
   dell'oggetto Python; altrimenti il controller rifiutava
   sempre la modalità differita anche con gli stessi 16 Sim.

### Test aggiunti alla Python 3.7 CI e a unittest discover

- `tests/test_m108_spinup_barrier.py`: callback EA
  originale unica, non attiva su altri lotti, attende
  Bouncer e legge i job EA solo dopo l'assegnazione.
- `tests/test_m108_16_student_reconciliation.py`:
  13 NPC + 3 playable, no-show e job scambiati, nessuna
  presenza fuori dal registro, nessuna situazione aula
  aggiuntiva non controllata, nessuna falsa conferma
  di banchi/lezioni.
- `tests/test_m108_post_bouncer_audit.py`:
  controllo aggiuntivo di fase / job / classi
  errati e simultaneità delle due route.
- `tests/test_m105_live_core_binding.py`:
  EA `get_current_job_for_sim` della versione
  decompilata dalla giocatrice.

### Stato e blocchi per la prima beta completa

**Ancora non verificato / non collegato in-game:**
- La CI GitHub del ramo nuovo era *queued* al momento
  dell'ultima verifica. Non dichiarare un PASS.
- Lo shadow `WeeklyScheduleSituationData` necessita
  prova con la reale metaclasse e i test EA del gioco.
- Un unico installer M108 deve coordinare il calendario
  Base 8, Core 5, guest list native, filtri school-only,
  fallback di sostituzione, lezioni e la lettura reale
  al momento delle assegnazioni.
- `on_all_sims_spawned_during_zone_spin_up` copre
  **soltanto lo spin-up**; serve un evento affidabile
  o un audit richiesto dopo le lezioni delle 10/14
  quando la zona è già operativa.
- Serve prova a scuola con 16 Sim sul lotto, staff
  correttamente assegnato, margine reale NPC,
  classi da 8 e posti effettivamente occupati.
- M108 non viene ancora inclusa negli archivi
  `.ts4script` correntemente generati dai builder
  del repository. **Non fornire una beta inventata.**

I commit sono solo su `feature/m55-presenze-studente-test`.
`main`, package e save della giocatrice non sono stati
modificati.
