# M105 — Un unico piano per 16 studenti, non altri inviti sperimentali

## Stato al 2 novembre 2026

M104 ha modificato **una** vera richiesta di filtro del Bouncer EA
(GUID 280516) ma, nel gioco, erano presenti solo **4/16 iscritti**
(Classe 1: 1, Classe 2: 3) e sette adolescenti estranei nelle
situazioni scolastiche. Non c'è prova che il filtro abbia causato
l'arrivo dell'unico NPC iscritto.

Le prove M99/M101/M102/M104 di una sola convocazione sono quindi
**chiuse**. Nessun'altra versione da installare per quei test.

## Nuovo codice realmente implementato

- `src/m105_day_controller/mhs105_atomic_school_roster.py`:
  elabora **insieme** le liste di idoneità di *tutti e sei* i job
  scolastici EA: Base Student 277894 e cinque Core 278965,
  278966, 278967, 278968, 303765. Con i tre adolescenti
  giocabili già iscritti e le due classi da 8, verifica un piano
  con **3 giocabili + 5 Core + 8 ordinari = 16**.
- Risolve i cinque ruoli speciali come assegnazione con vincoli,
  non in modo casuale. Un NPC che non supera il filtro Base
  può essere utilizzato **solo se** passa il filtro di uno dei
  cinque job speciali. Nessun duplicato o Sim estraneo.
- Le assegnazioni dei cinque ruoli restano **manuali** per default.
  Se si chiede esplicitamente un suggerimento, lo stato è
  `PROPOSAL_NEEDS_MANUAL_CONFIRMATION`, MAI
  assegnazione automatica salvata nel gioco.
- `src/m105_day_controller/mhs105_native_core_requests.py`:
  prepara gli argomenti originali delle cinque richieste EA
  `submit_matching_filter`, limitandole ciascuna al Sim
  confermato per quel ruolo, ma solo con verifiche di
  scuola, salvataggio, giorno e Bouncer. Nessun invito,
  nessuna situazione aggiuntiva, nessuna interferenza con
  professori o preside.
- Test:
  `tests/test_m105_atomic_school_roster.py` e
  `tests/test_m105_native_core_requests.py`.
  Il primo verifica anche la compatibilità con i contratti
  preesistenti M97, M92, M96.

## Ciò che NON è ancora implementato o provato

1. Nessun hook EA runtime M105 installato: il codice nuovo
   è un modulo di logica isolato. **Non installarlo in Mods.**
2. I cinque ruoli non sono ancora prenotati nel gioco
   prima del primo spawn delle situazioni Core.
3. Il numero **8** di richieste Base non è stato ancora
   applicato in una sessione reale tramite il scheduler M96.
4. I limiti fisici del lotto, le assegnazioni di fase
   8+8, e le due lezioni non sono stati ancora validati
   con questo controller.
5. Il rapporto M101d di 12 candidati Base idonei su 13
   non fornisce da solo le idoneità ai cinque filtri Core:
   servono i risultati reali in memoria nel nuovo
   preflight, non liste ipotetiche.

## Prossima attività di codice (prima di chiedere test alla giocatrice)

Implementare il runtime PRE-SPAWN con lettura della
registrazione e delle assegnazioni MHS97, verificare tutti
i sei filtri EA nel salvataggio e vincolare atomically
cinque chiamate Core e otto situazioni Base prima
dello spin-up. Confermare dall'API EA che gli studenti
assegnati ai ruoli sono i cinque scelti; se il runtime
non può garantirlo, disattivare l'intero tentativo e
mantenere la scuola EA normale.

**Criterio finale non modificato:** 16/16 iscritti sul
lotto, nessun adolescente non iscritto in una situazione
scolastica, Classe 1 8/8 e Classe 2 8/8; lezioni e
personale EA non danneggiati. Il test in-game si farà
**solo dopo** avere integrato e compilato questo runtime.


## Avanzamento di codice successivo — M105 preflight + sessione nativa

Sono stati aggiunti nuovi componenti di codice, non ancora inclusi
in alcuna build Mac installabile:

- `src/m105_day_controller/mhs105_live_preflight.py`:
  legge l'esatto registro dello slot attivo, verifica i tre
  adolescenti giocabili e le cinque assegnazioni MHS97, esegue
  **sei interrogazioni originali EA SimFilter** con
  `callback=None` e con i 13 NPC esistenti. Accetta soltanto
  risultati `SimFilterResult` verificati con punteggio.
  Qualsiasi eccezione o assegnazione non valida blocca il piano.
- `src/m105_day_controller/mhs105_native_session.py`:
  mantiene **un'unica sessione per slot, giorno e lotto**.
  Prepara al massimo cinque richieste Core, ciascuna
  vincolata allo studente specifico, e otto richieste Base,
  ciascuna vincolata a un altro iscritto. Non riutilizza
  indiscriminatamente uno stesso Sim e non altera
  richieste esplicite di EA.
- `src/m105_day_controller/mhs105_game_controller.py`:
  connette il preflight alla M57, mantenendola nel suo stato
  originale per i filtri non scolastici. Il wrapper interviene
  soltanto se è riconosciuto il vero calendario del liceo
  `277657` o `279958`, il chiamante EA Bouncer e lo stesso
  salvataggio/giorno preparato a casa.
  Include `arm`, `check`, `off` nel sorgente ma **NON
  è caricato in alcun pacchetto Mods**.
- Test: `tests/test_m105_live_preflight.py`,
  `tests/test_m105_native_session.py`,
  `tests/test_m105_game_connector.py`. Inclusi in
  `m96_school_dispatcher_logic` su GitHub Actions.

### Importantissimo: che cosa non abbiamo ancora dimostrato

Questo codice PREPARA e VINCOLA le richieste originali, ma un
filtro chiamato non equivale a Sim effettivamente assegnato
dal Bouncer. Le 8 situazioni Base necessarie non sono state
ancora abilitate: il calendario EA originale spesso ne
crea meno. Non sono inoltre verificati l'effettivo limite
fisico del lotto e le due lezioni da 8.

L'attivazione del conteggio M96 viene quindi mantenuta
**disattivata** in questo controller. Non si deve creare
una beta per la giocatrice finché una soluzione non
verifichi i cinque ruoli, il budget del lotto e il
routing delle lezioni senza generare studenti estranei.

**Nessuna nuova prova utente richiesta in questa fase.**


## M105 — correzione delle richieste EA multiple (2 novembre 2026)

I controlli isolati del planner rimangono **3 giocabili + 5 Core + 8 Base**,
ma ora la sessione nativa riconosce il numero effettivo richiesto
da `submit_matching_filter(number_of_sims_to_find, ...)`.

- Se EA chiede otto NPC Base con **un'unica chiamata**, prepara otto
  `sim_constraints` distinti tra gli iscritti Base, non uno soltanto.
- Se EA effettua richieste da **3 + 2 + 3**, prepara esattamente otto
  ID non ripetuti e conserva il conteggio reale delle chiamate separato
  dal conteggio degli studenti.
- Richieste senza numero affidabile, con numero zero, bool, numero oltre
  i posti rimasti, o richiesta Core per più di uno studente **non
  vengono riscritte**. Sono registrate come buchi del tentativo:
  non potranno far risultare completato il piano dei 13 NPC.
- Il dato `all_thirteen_native_targets_requested` diventa vero soltanto
  se, nello stesso slot/giorno/zona, sono state vincolate senza buchi
  tutte le **cinque chiamate Core** e tutti gli **otto target Base**.
  **Non prova** che EA abbia davvero attribuito i ruoli, creato le
  situazioni, fatto arrivare 16 studenti o impedito ogni NPC esterno.
- Test di regressione aggiunti in
  `tests/test_m105_native_session.py` per richieste 8, 3+2+3,
  quantità malformate/sovrabbondanti, ruoli Core con quantità non
  consentite e invocazioni per keyword.
- Aggiornato `mhs105_game_controller.check` per mostrare quanti
  **studenti Base** sono stati richiesti e non confondere le chiamate
  del filtro con i posti utilizzati.

**Limite fondamentale ancora aperto:** non sappiamo se il calendario
EA crei almeno otto posti Base oppure quando il Bouncer stabilisca i
cinque Core rispetto allo spawn. Un filtro non intercettato o una
richiesta Base aggiuntiva può ancora far scegliere NPC vanilla.
Non è stata abilitata M96, non è stato collegato alcun compilato Mac
installabile. La verifica richiede CI e successivamente evidenza
dal gioco, non soltanto test di sorgente.


## M105 — verifica effettiva ruoli e ingresso in classe (proseguimento)

Il codice EA `weekly_schedule_zone_director.py` già fornito dall'utente
conferma che **WeeklyScheduleSituationData.try_start** riceve
`sims=set(services.sim_info_manager().instanced_sims_gen())`.
Il motore seleziona gli *attuali Sim istanziati* presenti sulla
zona, valuta i requisiti per ciascun `SituationJob`, e se non trova
abbastanza Sim per i job obbligatori **la situazione di lezione
non parte**. Quando crea una situazione, costruisce una guest list
dei Sim già assegnati: questa fase non riempie un'aula mancante
con tutti i nomi del registro MHS.

Quindi la sequenza corretta è:
**convocazione originale EA → Sim materializzato sulla zona →
SituationJob effettivamente occupato → situazione di lezione
8+8 → seduti nella rispettiva classe**. Una fase non può
essere usata come prova delle successive.

Nuovi componenti effettivamente sviluppati:

- `src/m105_day_controller/mhs105_role_binding_gate.py`:
  verifica cinque **effettive** coppie
  `SituationJob EA → Sim iscritto` nel CoreClassNPCs
  `298052`, più l'effettiva presenza fisica dei cinque
  Sims. Una risposta positiva al filtro, un invito o una
  scelta nell'interfaccia MHS non costituiscono prova.
- `src/m105_day_controller/mhs105_live_core_binding.py`:
  osserva in sola lettura i Sim del lotto e il loro
  SituationJob all'interno della situazione Core. Richiede
  che l'API EA corrente esponga davvero un getter di job:
  in caso contrario l'esito è `UNKNOWN`, non `VERIFIED`.
- `src/m105_day_controller/mhs105_lesson_gate.py`:
  verifica separatamente i 16 iscritti **fisicamente sul
  lotto**, i 16 nelle situazioni EA senza adolescenti
  estranei, 8+8 membri nei due veri job di lezione, e 8+8
  Sim osservati **seduti**. Non confonde una classe
  assegnata con un'aula realmente occupata.
- `mhs105_game_controller.check()`: integra la verifica
  Core effettiva senza modificare direttamente nessuna
  situazione scolastica.

Test automatici aggiunti nella job
`m96_school_dispatcher_logic`:

- `tests/test_m105_role_binding_gate.py`;
- `tests/test_m105_live_core_binding.py`;
- `tests/test_m105_lesson_gate.py`;
- `tests/test_m105_game_connector.py` aggiornato.

**Restano bloccanti per una release stabile:** la verifica
della firma dell'API EA che restituisce il vero SituationJob,
il collegamento della quantità esatta di richieste Base allo
scheduler (non soltanto ai filtri), la capienza reale del lotto
con studenti e personale e l'assegnazione fisica ai banchi.
Il modulo M105 non è ancora distribuito come pacchetto Mac.
Non chiedere altri test M99-M104 all'utente.


## M105 — ponte di osservazione verso il calendario M96

È stato aggiunto `src/m105_day_controller/mhs105_schedule_audit.py`, con
`tests/test_m105_schedule_audit.py`, incluso nei controlli offline.
L'adattatore osserva **esclusivamente** il conteggio originale EA restituito
per la Situation Base Student `277733` dai due calendari liceo
`277657` e `279958` attraverso
`WeeklyScheduleDay.get_long_term_situation_count`. Riporta separatamente
il minimo e il massimo originali e se questi possono fornire gli otto
posti NPC Base richiesti dal piano di **3 giocabili + 5 Core + 8 Base**.

Le letture vengono accettate solo con save/day/zone liceo verificati;
sono memorizzate fino a 32 osservazioni e scartate se il conteggio non
è una coppia di interi attendibili. Il wrapper osservativo restituisce
**sempre esattamente** il valore originale EA, senza creare situazioni,
ricorrere a NPC sostitutivi o attivare M96. Il codice rifiuta
l'installazione sopra un conteggio M96 già modificato, per non spacciare
il numero modificato per quello originale.

Una previsione di otto Base **non è un'autorizzazione** ad aumentare
il conteggio: rimane impossibile usare M96 finché non è dimostrata
la prenotazione effettiva PRE-SPAWN dei cinque ruoli Core, il budget
del lotto e la compatibilità dei due cicli di lezione da otto. Né
l'audit né i suoi test dimostrano l'arrivo degli studenti.
Il componente **non è incluso in alcuna build Mac installabile**.


## M105 — prima beta Mac di verifica integrata (NON risultato finale)

La pipeline di compilazione è stata aggiunta in
`tooling/build_mhs105_beta.py` e nel job Actions `m105_mac_3_5_8_beta`.
Quando supera il job su Python **3.7**, produce uno ZIP con
`MHS_M105_CONTROLLO_16_MAC_BETA.package`,
`MHS_M105_CONTROLLO_16_MAC_BETA.ts4script`, report e istruzioni.
Usa il pacchetto M98 da 76 risorse (menu di scelta dei cinque ruoli)
e 48 moduli Python, sostituendo il loader M104 con quello M105.
Resta su un ramo sperimentale; `main` non è alterato.

Il controller aggiunge `mhs105.arm` da casa prima del viaggio,
`mhs105.check` al liceo e `mhs105.off`. Le chiamate native per
cinque Core + otto Base sono opt-in. Il nuovo
`mhs105_schedule_runtime.py` prova ad agganciarsi al calendario
originale EA soltanto per **osservarne** il conteggio: non cambia
`get_long_term_situation_count`, non abilita M96 e non crea situazioni.
Il rapporto esprime *richieste preparate*, non prova di arrivo.

Questa beta non può garantire ancora 16/16: se EA offre meno posti Base,
la selezione non può materializzare quelli mancanti; la prenotazione dei
cinque ruoli, i limiti del lotto e due lezioni da otto restano da
verificare in-game. Un risultato CI verde certifica solo la build
offline, **non il funzionamento del gameplay**. Se uno qualunque dei
controlli fallisce, non distribuire la beta come soluzione funzionante.

### Limite agli esperimenti

Evitare il ciclo infinito di build per singolo invito. Consentire al
massimo tre *cicli di verifica focalizzati* prima di rivalutare
l'architettura: (1) selezione Core/Base realmente rispettata da EA,
(2) copertura posti e presenza senza estranei, (3) lezioni 8+8.
Se l'API nativa non consente i risultati, discutere un controller
scolastico alternativo invece di ripetere la medesima prova.
