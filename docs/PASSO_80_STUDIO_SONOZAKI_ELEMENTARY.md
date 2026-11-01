# Passo 80 — Cosa imparare da Sonozaki Elementary School Management

## Perché questo confronto
Il test Mac M79 ha dimostrato che la build M58 con le restrizioni M57/M60 ai
`SimFilterService` disattivate ripristina le lezioni EA alle 10:00, ma gli NPC
seduti sono casuali, **non gli iscritti del registro** (C1=8, C2=8).

La richiesta dell'utente è studiare il meccanismo di **Elementary School
Management for Go to School** di SonozakiSisters (non solo More Students).
Obiettivo: scegliere l'intero registro senza rompere il comportamento EA.

## Fatti verificati dalla descrizione dell'autrice (non dal binario)

Fonte primaria: https://www.patreon.com/SonozakiSistersSims4/posts/elementary-for-132310716

- Elementary School Management è un add-on per **Zerbu Go to School V5**
  e richiede anche High School Years e Lot51 Core.
- Usa la cassetta postale per assegnare/rimuovere compagni, docente, preside,
  consulente e bidello; gli studenti si scelgono con un Sim picker.
- La scuola elementare Go to School convoca di default **7 compagni oltre al
  bambino giocabile**; il numero si cambia nelle impostazioni Go to School
  sulla cassetta postale.
- L'autrice avverte: non assegnare più bambini dei posti realmente richiesti,
  altrimenti vengono scelti a rotazione nei vari giorni.
- Il personale non assegnato viene lasciato alla scelta standard del gioco.
- L'autrice segnala possibili interferenze con mod di spawn, ma precisa che
  qui le situazioni sono gestite dall'altro mod Go to School, non dagli stessi
  filtri EA del liceo.

Pagina download pubblico del modulo principale:
https://www.patreon.com/SonozakiSistersSims4/posts/elementary-for-132313120
Archivio dichiarato dall'host:
https://simfileshare.net/download/2rR3xeCjX9oWSp8irFZwlSK2339hQ4dZVrGCKetIKCyzNVgxZBWJ83xFzvMFMFm4/

**Aggiornamento 1 novembre 2026:** l'utente ha caricato il package Elementary
IT e lo script ".ts4script". Sono stati analizzati direttamente in sola
lettura: **78 risorse DBPF, 5 iniezioni nei filtri Zerbu, 7 tratti nascosti,
script Python 3.7 con hook al caricamento delle famiglie**. Tutti i dettagli
sono documentati nel [Passo 81](PASSO_81_ANALISI_BINARIA_ELEMENTARY_SONOZAKI.md),
che sostituisce il precedente limite relativo all'assenza dei file.

## Evidenza già analizzata da Sonozaki High School 2.2.1

L'analisi locale preesistente `ANALISI_SONOZAKI_PER_MY_HIGH_SCHOOL.md`
fu effettuata su un archivio fornito dall'utente in data 30/10.

La mod high-school contiene 165 risorse DBPF: 24 SimPickerInteraction native,
25 ImmediateSuperInteraction, 29 LootActions, 18 filtri scolastici XML,
10 tratti, 24 SimData ecc. La scelta passa da picker -> actor continuation ->
loot sui tratti (whitelist/classe) -> override `TunableSimFilter` EA.

L'autrice, nella documentazione v2.2.1, avverte di problemi dovuti a
filtri regionali, sim nascosti, NPC di servizio, tratti classe e priorità EA;
la correzione alla suddivisione classi richiede logica ulteriore.
Fonte: https://www.patreon.com/SonozakiSistersSims4/posts/high-school-2-2-153195289

## Cosa trasferire a MY HIGH SCHOOL (architettura originale)

1. **Registro come unica fonte delle scelte**, indipendente per salvataggio
   e persistente. Il picker e i menu già funzionano: non rifarli.
2. **Capienza del gioco e numero registrato non sono la stessa cosa**:
   verificare quanti slot reali EA mette a disposizione per ciascun lavoro/
   situazione, e come la fase di lezione consuma quei ruoli.
3. **Separare selezione, arrivo e presenza in aula.**
   Non basta che un Sim sia nel registro o abbia un tratto: deve entrare
   in una situazione EA esistente con un job idoneo e partecipare alla fase
   di lezione. Non inventare nuove situazioni additive per riempire i posti.
4. **Escludere NPC casuali soltanto nei ruoli giusti**, preservando Core NPC,
   studenti giocabili, eventi, personale e fallback; non riattivare i vincoli
   M57/M60 globali che hanno probabilmente svuotato le classi.
5. Se i marcatori/trait temporanei risultano necessari in-game, implementarli
   originalmente e con lifecycle/test espliciti. Non copiare il codice
   proprietario di Sonozaki.

## Decisione pratica

- Conservare il baseline **M58 isolamento, Actions 41257486408**, perché
  ora gli studenti EA si siedono alle 10:00.
- **Analisi del modulo Elementary completata nel Passo 81**. Il pattern
  whitelist/blacklist + loot + filtro Zerbu è verificato staticamente, ma i
  suoi ID non vanno trasferiti nel liceo EA. Ora priorità a capienza e job EA.
- Confrontare successivamente i TGI con i tuning di Zerbu e del liceo EA:
  NON assumere che i filtri di Elementary siano gli stessi del liceo.
- Sviluppare in seguito un meccanismo di assegnazione esatta delle
  situazioni scolastiche *esistenti* per tutti gli iscritti idonei.
  Testare progressivamente ma con obiettivo finale C1=8 e C2=8.
- Nessun nuovo package da installare durante questa sola analisi.
