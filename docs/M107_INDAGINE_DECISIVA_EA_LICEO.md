# M107 — Indagine decisiva, prima di ulteriori beta in gioco

Data: 2 novembre 2026. **Nessun codice EA modificato, nessuna nuova beta autorizzata.**

## Il punto debole scoperto dai test M105–M106

I test offline verdi non simulano la scelta reale dei Sim, l'occupazione
dei SituationJob né la classe EA. Nel salvataggio della giocatrice:

- 16 iscritti fissi, due gruppi di 8, tre teen giocabili.
- 13 NPC iscritti, 12/13 hanno superato il SimFilter Base EA.
- Nessuno dei 13 ha superato il SimFilter EA per MeanSim.
- M106 si è fermata: `no 5 Core + 8 EA-eligible Base partition for the fixed 16`.
- Non sostituire nessun iscritto, non cambiare le personalità, non assegnare
  arbitrariamente ruoli diversi.

## Fonti pubbliche che modificano l'ipotesi di sviluppo

1. SonozakiSisters, *High School Management 2.2 and Add-Ons*,
   post pubblicato 17 marzo 2026, aggiornato 10 aprile 2026:
   https://www.patreon.com/posts/153195289
   - il tratto nascosto `trait_HighSchool_Active_Class1Student` può alterare
     priorità e distribuzione (a prescindere dal nome, non garantisce l'aula);
   - esistono filtri di regione, particolarmente Moonwood Mill,
     Strangerville e Henford-on-Bagley, oltre a vincoli per household
     nascosti, relazioni nascoste e certi NPC di servizio;
   - MeanSim e membri delle squadre hanno condizioni diverse dagli altri;
   - la mod usa metodi di selezione speciali e segnala che nemmeno con
     More Students il risultato è sempre garantito.
2. SonozakiSisters, *Choose High School Classmates 2.0*:
   https://www.patreon.com/posts/121367985
   - usa regole di blacklist per i ruoli di liceo e i relativi SimFilter;
   - non prova 16 identità fisse senza modifiche al calendario originale.
3. Konanhurry, *Choose Your High School Classmates*:
   https://www.curseforge.com/sims4/mods/choose-your-high-school-classmates
   - l'idoneità a squadre/club e il salvataggio del nucleo scelto possono
     richiedere passaggi ulteriori rispetto alla semplice scelta del ruolo.
4. Motherlode, decompilatore Python 3.7 EA con verifica bytecode:
   https://github.com/BigBadBleuCheese/Motherlode
   - supporta macOS e può generare script leggibili e report di verifica
     direttamente dalla copia locale di The Sims 4.

L'articolo di Sonozaki non dimostra che un certo vincolo sia presente su
tutti i Sim del salvataggio; sono piste da verificare sul codice corrente.

## Artefatti di cui abbiamo già i dati

L'utente aveva fornito `weekly_schedule_zone_director.py`,
ritrovato nella propria Library ChatGPT in data 30 ottobre 2026.
Nel repository ci sono tunings originali dell'1 novembre:
`assets/ea_2026_11_01/277657.xml`, `279958.xml`,
`298052.xml`, `277733.xml` e altri.

**Non richiedere all'utente un'altra copia di
`weekly_schedule_zone_director.py`.**

## File sorgente mancanti, in ordine di valore

Da una decompilazione verificata *della sua installazione attuale*:
- `situations/bouncer/bouncer.py`
- `situations/bouncer/bouncer_request.py`
- `filters/sim_filter_service.py`
- `situations/base_situation.py`
- `situations/situation_guest_list.py`, se presente

Sono sufficienti pochi file mirati. Non è necessario condividere
salvataggi privati o l'intera installazione EA.

Se disponibili localmente, possiamo anche ispezionare soltanto i tunings
di Sonozaki High School Management 2.2.1 (nessuna installazione) per
capire quali filtri effettivamente sovrascrive e quali marker usa.

## Tre interrogativi che debbono avere una risposta tecnica PRIMA del prossimo test

1. **Ammissione:** esiste un punto sicuro in cui un gruppo esplicito di
   SimID iscritti viene invitato a un *vero* SituationJob EA, senza
   scegliere NPC diversi in fallback e senza cambiare tratti caratteriali?
   Verificare il Bouncer e i vincoli della situation guest list.
2. **Capienza:** come si realizzano esattamente 8 richieste Base quando
   il calendario originale ne prevede 6, senza crearne 16 o generare
   comparse aggiuntive?
3. **Lezioni:** quale parte di WeeklyScheduleSituationSet, lezione e
   RoleState assegna 8 al vero job dell'aula 1 e 8 all'aula 2? La sola
   convocazione sul lotto non equivale al ruolo di studente in lezione.

## Soglia di decisione e criterio di stop

Prima della prossima beta serve prova di codice e test **almeno** per
(1) original Bouncer acceptance, (2) exactly 13 NPC IDs and no
fallbacks, (3) schedule 8 Base, (4) mapping delle lezioni 8+8.

Se i quattro requisiti non sono realizzabili con gli hook nativi
verificati, dichiarare l'architettura EA-first inadeguata e valutare
un controller di situazioni alternativo, senza lanciare un'altra serie
di beta per singolo NPC.

Un test Python o GitHub Actions verde non soddisfa i criteri di
presenza nel gioco; servirebbe **un solo** test integrato su copia
del salvataggio, dopo il superamento di questi controlli.

## Analisi di prima mano degli script EA caricati il 2 novembre

La giocatrice ha estratto la propria installazione EA con Motherlode e
fornito **i file sorgente decompilati**, non soltanto screenshot:
`situations/bouncer/bouncer.py`,
`situations/bouncer/bouncer_request.py`,
`situations/bouncer/bouncer_client.py`,
`situations/bouncer/bouncer_types.py` e
`situations/bouncer/specific_sim_request_factory.py`.

Si annotano solo fatti tecnici sintetici, non si copia il sorgente EA
nel repository pubblico.

**Prove rilevanti nell'attuale codice EA:**
- `BouncerRequest.__init__` accetta `requested_sim_id` e
  `accept_alternate_sim=False`. Una richiesta esplicita viene marcata
  diversa da una non esplicita nella priorità della Bouncer.
- La richiesta contiene `job_type` e viene associata a una specifica
  situazione. L'ID, da solo, non autorizza arbitrariamente il Sim ad
  assumere quel job: il Bouncer richiama il `SimFilterService` e usa
  anche blacklist e additional filter terms.
- Nei due percorsi EA, istanziazione in zone spin-up e chiamate successive,
  l'ID richiesto può diventare `sim_constraints`: questo è il punto in
  cui le modifiche tardive ai filtri della M105/M106 hanno fallito.
- La `SpecificSimRequestFactory` non è un invito generalizzato di un
  Sim assente: la factory imposta `CANNOT_SPAWN` nelle richieste create
  per Sim già presenti. **Non usarla per promettere 13 NPC convocati**.
- Il Bouncer gestisce anche richieste di **prenotazione SimID** e può
  elevare la capacità NPC tramite `add_npc_cap_modifier(1)`. Va verificato
  se e quando lo specifico `SituationManager` scolastico ne fa uso;
  non aumentare il cap genericamente.
- Il Bouncer applica regole di esclusività per evitare doppie situazioni
  incompatibili e gestisce NPC soft-cap: un invito esatto può comunque
  essere respinto o una presenza già soddisfatta può essere eliminata.
- Dopo `submit_matching_filter`, EA invoca `_sim_filter_service_callback`
  per richiedere la generazione del Sim e solo successivamente
  `on_sim_creation_callback` per assegnare alla situazione. **Una
  richiesta vincolata NON è una prova di assegnazione o presenza**.

**Decisione:** non scrivere un nuovo hook che modifichi globalmente i
filtri. L'ipotesi migliore da esaminare è generare nel calendario EA
`SituationGuestInfo` con ID espliciti e senza fallback, rispettando
la divisione Core/Base e l'ordine di spin-up. Prima è necessario
verificare la trasformazione `SituationGuestList -> BouncerRequest`
e il comportamento di `SimFilterService` sui Sim ID espliciti.

**Due file ancora necessari da Motherlode:**
1. `scripts/situations/situation_guest_list.py`.
2. `scripts/situations/base_situation.py`.

Terzo file utile per stabilire come non penalizzare i Sim premade:
`scripts/filters/sim_filter_service.py`. Le assunzioni andranno
confrontate con i tuning originali già presenti nel repository.

Nessun test nel gioco richiesto in questa fase.

## Evidenza diretta: SituationGuestList + BaseSituation (file EA originali ricevuti)

File di origine forniti dalla giocatrice:
`situations/situation_guest_list.py` e
`situations/base_situation.py`, estratti da Motherlode il 2 novembre 2026.

Catena nativa CONFERMATA:
1. `SituationGuestInfo.construct_from_purpose(sim_id, job_type, INVITED)`
   genera una richiesta VIP, con `accept_alternate_sim=False` di default.
   L'eccezione per sostituti riguarda soltanto `PREFERRED` e `HIRED`
   con `job_type.no_show_action == REPLACE_THEM`.
2. `SituationGuestList.add_guest_info(guest_info)` organizza gli invitati
   per SituationJob. La lista può essere costruita con `invite_only=True`.
3. In `BaseSituation.start_situation()`, PRIMA delle richieste,
   `_expand_guest_list_based_on_tuning()` aggiunge
   `AUTO_FILL sim_id=0` per `job_type.get_auto_invite()` non soddisfatti.
   **ATTENZIONE:** `invite_only=True` NON disattiva questo auto-fill.
4. `_issue_requests()` trasforma ogni `SituationGuestInfo` in un
   `BouncerRequest`, conservando esattamente `requested_sim_id`,
   `accept_alternate_sim`, `job_type`, priorità e spawning option.
5. Se `_is_invite_only` è falso e `default_job()` esiste,
   `_create_uninvited_request()` aggiunge una
   `BouncerFallbackRequestFactory`. Con `invite_only=True` questo
   fallback NON viene creato, ma restano gli AUTO_FILL del punto 3.
6. In `BaseSituation.invite_sim_to_job(sim,job)` viene nuovamente
   costruito un BouncerRequest esplicito EVENT_VIP. NON è una garanzia di
   presenza, perché il Bouncer fa passare l'ID nel SimFilter originale.
7. Il callback `on_sim_assigned_to_request` è la prova di reale
   appartenenza al SituationJob. Se lo spawn fallisce, il
   `job_type.no_show_action` può invocare la sostituzione creando una
   nuova richiesta: anche con `accept_alternate_sim=False` è
   importante verificare il no-show e la politica del job.

Conseguenza: **non basta mettere `requested_sim_id`**; per avere gli
esatti NPC della giocatrice è necessario governare INSIEME (a) inviti
espliciti, (b) auto-fill per job, (c) fallback per default-job,
(d) no-show replacement e (e) accettazione SimFilter/Bouncer.
I prossimi controlli riguardano `scripts/filters/sim_filter_service.py`
della medesima installazione EA e solo in seguito `situation_job.py`.
Non pubblicare beta in gioco prima che sia noto il percorso di
accettazione degli ID espliciti.
