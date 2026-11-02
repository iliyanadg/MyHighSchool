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
