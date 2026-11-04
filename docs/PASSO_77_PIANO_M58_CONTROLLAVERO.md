# Passo 77 — Specifica M58: controller delle situazioni EA, senza patch alla cieca

## Materiale già verificato
- XML originali The Sims 4 macOS 1.129.39.1230; 7 SimFilter, 3 situazioni base, 10 base Situation Jobs, 2 situazioni giocabili, 5 phase jobs, archivio di 1067 XML HighSchool_Active.
- Passi 73–76 sul ramo feature/m55-presenze-studente-test.
- M57d in gioco: registro corretto slot 11 C1=8 C2=8, 4/16 iscritti sul lotto e 0/8 staff scelto; API filtri osservata ma 0 constraints applicati. Non è una soluzione di presenze.
- Codice M57 attuale: filtra SimFilterService; M55 prima creava additive 277733 per singolo Sim, disattivato nella M57 per evitare duplicati. NON riattivarlo come soluzione senza coordinamento dei job EA.

## Vincoli non negoziabili
- Conservare registro esterno per-save, possibilità di assegnare/rimuovere/trasferire e menu funzionanti.
- Massimo 8 iscritti per classe inclusi giocabili, fase 1 due classi, fase 2 terza classe solo con routing confermato.
- No auto-enrol giocabili non registrati, no duplicazione con core role jobs; non cancellare/alterare altri file Mods o save.
- EA gestisce eventi/ore/prom. Evitare tratti nascosti permanenti e tuning override indiscriminati.
- M54 main rollback, M57d come prova precedente, implementazione M58 in ramo separato solo dopo piano e test statici.

## Evidenza tecnica
- WeeklySchedule 277657 e 279958 creano 6 situazioni NPC_Base_Student (277733), una CoreClassNPCs 298052, una VenueNPCs 298096 e Vendor mensa 278011.
- NPC_Base_Student job 277894 ha filtro 280516 e auto_invite=1, ma numero effettivo dipende da schedule/guest decisions.
- CoreClassNPCs 298052 contiene jobs teacher1, teacher2, Cheer, Chess, Football, Computer, Mean; VenueNPCs 298096 contiene principal e janitor.
- I job di phase Student1/2/3 e Teacher1/2 usano filtro vuoto 15940 e auto_invite 0; gli NPC di fase vengono scelti da base situation già attive mediante situationData, con max 0..6 o 0..8 e talvolta trait Class1Student 293779.
- Student3 nella Background_Morning è un raggruppamento mattutino, NON prova di terza aula.
- Staff teacher/principal/janitor base jobs hanno REPLACE_THEM, quindi EA può scegliere ricambi se la prima selezione non funziona.
- Cafeteria Vendor situazione 278011 identificata, ma il job non è ancora analizzato; non è blocco per test di studenti e docenti.

## Architettura proposta M58 a stadi
**Stadio A: prova diagnostica del percorso EA prima del primo intervento**
- Identificare in codice EA (matching class/version) l'accesso al WeeklySchedule/creation path oppure l'entrypoint di creazione situazione, con annotazione delle signature reali, job_guest_list e lifecycle. Non assumere che si possa scrivere SimID sul filtro generic.
- Sviluppare controlli pure Python del piano roster per 6 situazioni BaseStudent: subset esatto, gruppi core non doppi, playable esclusi da convocazioni NPC, validità della carriera liceale e dei tratti esclusi (Baby Ariel).
- Un contatore leggero **per situazione base / job EA**: planned, created, selected IDs e physical arrivals (solo nel save test), senza mutare live NPC. Non serve una nuova build finché non sono identificati gli hook con affidabilità.
**Stadio B: selezione vera degli NPC e del personale**
- Prima delle scelte EA, sostituire o costruire guest list **nelle situazioni base esistenti** preservando situazione e job vanilla e solo per la zona/slot verificati. Selezione per ID con fallback fail-closed che non forza NPC inadatti. Non creare situazioni aggiuntive indipendenti né fare despawn globale.
- Testare prima 1–2 NPC non-core e 1 docente, poi roster completo e sostituzioni; controllare no duplicate/safety.
- Se la selezione originale dipende da trait role, verificare precisamente se è necessario assegnare un flag transitorio al Sim selezionato, evitando salvataggio permanente, se mai possibile.
**Stadio C: assegnazione aula/lezioni**
- Leggere situationData e role states per i due gruppi: seguire stesso player/phase handoff EA, mappare il manifesto delle classi e lavagne, evitare sovrapporre due situazioni allo stesso Sim.
- Incrementare capienza delle situationData pertinenti solo dopo che il conteggio fisico è confermato e rispettare limiti di performance.

## Condizioni di accettazione
- M58 non dichiara «presenti 16/16» finché 16 persone reali non sono sul lotto in job EA corretti.
- Numero dei non iscritti presente per limiti EA e playable, distinguere visite da vere presenze scolastiche.
- Personale nominato visibile nel ruolo, non semplicemente registrato.
- Lezioni 10:00 e 14:00, mensa 11:00 e prom non bloccate.
- Mac EA 1.129.39.1230, Python 3.7, compatibilità con Sonozaki Elementary e altre mod non controller liceo.

## Decisione operativa
Niente build adesso. La prossima azione da programmare è studio delle **API reali di creation/guest list** e una serie di test pure Python su piano studenti NPC/core/playable prima di qualunque hook nuovo. Nessun ulteriore file richiesto all'utente salvo risorsa con nome/ID esatto mancante in archivio.
