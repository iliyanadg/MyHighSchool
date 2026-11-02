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
