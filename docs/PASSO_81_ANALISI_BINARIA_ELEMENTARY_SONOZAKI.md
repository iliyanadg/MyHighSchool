# Passo 81 — Analisi BINARIA Sonozaki Elementary: whitelist, blacklist, filtri Zerbu e hook household

Data: 1 novembre 2026. **Analizzati effettivamente i due file caricati dall'utente**:
`SonozakiSisters_Elementary_School_Management_IT(2).package` e
`SonozakiSisters_elementary_school_management.ts4script`.
Analisi statiche in sola lettura. Nessun salvataggio Sims, file Mods o
modulo Sonozaki è stato modificato.

## Inventario riproducibile del package

DBPF v2.1, indice 3, **78 risorse**, tutte estratte:
- 20 interazioni XML: **10 SimPickerInteraction** e **10 ImmediateSuperInteraction**;
- 13 loot actions XML;
- 7 trait tuning XML (tutti nascosti);
- 6 pie menu category XML;
- 13 SimData binari;
- 18 STBL;
- 1 snippet **Lot51 TuningInjector**.

Lo snippet contiene **5 blocchi `inject_to_sim_filters`** e **3
`inject_to_traits`**, oltre a `inject_by_object_tags` per la
cassetta postale. Questo file **non** contiene override `TunableSimFilter`
autonomi: le condizioni vengono aggiunte a filtri **esistenti di Zerbu**,
richiedendo `lot51_core`.

## Flusso preciso del compagno

1. Il picker **Assign Classmate** seleziona al massimo **7 bambini** esterni
   alla famiglia, usa il filtro selettore nativo; la continuation richiama
   un'immediate interaction e il loot di assegnazione.
2. Il loot di assegnazione aggiunge il tratto nascosto di **whitelist
   compagno** (ID `14895628556053349417`) al Sim selezionato e rimuove
   il tratto nascosto di **blacklist NPC bambino**
   (ID `14998154786489864803`).
3. Il loot di rimozione compagno fa l'inverso.
4. Lot51 inietta una condizione invertita sul tratto blacklist nel filtro
   Zerbu **classmate** (ID `2842006145`).
5. Lo script Python compilato contiene la logica di aggiornamento dello
   status e dei tratti quando vengono caricati gli household.
6. Al passaggio alle diverse età, `inject_to_traits` esegue loot su
   tratti EA di età: inserimento della blacklist bambino al raggiungimento
   CHILD, rimozione della blacklist quando passa a TEEN, blacklist adulti
   quando arriva a YOUNGADULT/ADULT/ELDER. **Il ciclo di vita dei flag è
   gestito**, non solo la selezione da menu.

**Interpretazione:** il gioco/Go to School rimane proprietario delle
situazioni scolastiche; la mod orienta la lista di candidati mediante
tratti e condizioni dei filtri Zerbu. Non esiste nel package una modifica
autonoma alla capienza delle situazioni. Non sono stati verificati inviti
manuali o l'assegnazione diretta ad un banco.

## Flusso preciso del personale

- I picker di assegnazione staff permettono un Sim per ruolo
  (teacher, principal, janitor, counsellor).
- I loot aggiungono il tratto nascosto del ruolo Sonozaki, rimuovono il
  tratto blacklist adulti e aggiungono anche il corrispondente
  **trait Zerbu Go to School**. I loot di rimozione invertono le modifiche.
- Il TuningInjector modifica i filtri Zerbu:
  - `3020159961` principal;
  - `2507651203` teacher;
  - `3949134492` janitor;
  - `4028596705` counsellor.
- Ogni filtro riceve la condizione positiva del ruolo corretto e condizioni
  invertite che disfavoriscono o escludono blacklist/ruoli incompatibili.
  Non si deduce dall'XML il risultato esatto dello scoring a runtime senza
  il filtro Zerbu caricato.

## Ispezione ts4script

Archivio ZIP con **un modulo**:
`elementary_school_management/__init__.pyc` (3448 byte, magic Python 3.7
`42 0d 0d 0a`). È stato letto il payload marshal Python 3.7 con parser
locale di sola lettura per estrarre struttura di code object, nomi e
costanti, **non** copiato/decompilato in sorgente da riutilizzare.

Nomi di funzioni osservati:
- `assign_not_school_related_trait` usa `ACTION`,
  `SingleSimResolver` e `apply_to_resolver` per applicare loot;
- `assign_not_student_status` e `assign_not_school_stuff_status`;
- `split_household_by_age`, `assign_school_status_in_household`;
- `choose_grade_school_classmates_household_loaded` con hook
  `HouseholdManager.on_all_households_and_sim_infos_loaded` e `get_all`.

Questo supporta la tesi che la mod applica automaticamente blacklist ai
non selezionati dopo il caricamento famiglie/Sim. **Non** prova che ogni
flusso funzioni nella versione corrente del gioco, né che i 7 siano
sempre tutti sul lotto.

## DIFFERENZA fondamentale per MY HIGH SCHOOL

| Elemento | Elementary Sonozaki | MY HIGH SCHOOL oggi |
| --- | --- | --- |
| Registro selezione | Trait whitelist/blacklist sui Sim | JSON per salvataggio con ID Sim, C1 8/8 e C2 8/8 |
| Collegamento con selezione effettiva | Lot51 modifica **filtri Zerbu Go to School** | L'hook M57/M60 sui **filtri EA EP12** è DISATTIVATO per non svuotare le lezioni |
| Quando si sincronizza | Script al caricamento household e loot age-up | Registro e manifest disponibili, ma non tradotti in job EA |
| Posti presenti | Determinati dalle situazioni Go to School e impostazioni separatamente | EA liceo ha 6 situazioni base NPC e job core separati nel tuning esaminato |
| Risultato Mac test | Non testato qui | M58 isolamento: lezioni partono alle 10:00, **studenti casuali** |

**Conseguenza:** non è sufficiente copiare i tratti della Elementary o
iniettare il suo stesso filtro: i GUID e le situazioni scolastiche di
Zerbu elementare **non sono quelli del liceo EA**. L'approccio riutilizzabile
è *concettuale*: selezione dei candidati tramite marker/condizioni sul
filtro corretto, senza imporre `sim_constraints` a tutte le chiamate
`SimFilterService`.

**Criticità capienza:** il filtro può scegliere *chi*, ma non aumenta
automaticamente *quanti* NPC compaiono e a quale aula vengono assegnati.
Il limite e le fasi EA devono essere studiati assieme a More Students o
tuning equivalenti, altrimenti 16 iscritti potrebbero ruotare.

## Prossima implementazione originale MHS

- NON attivare la Elementary nel liceo né inserire i suoi ID/Tuning in MHS.
- Non copiare il codice script di terzi. Conservare la build di isolamento
  [M58 41257486408](https://github.com/iliyanadg/MyHighSchool/actions/runs/41257486408)
  e i registri/menu verificati.
- Fase 1: mappare esattamente gli **EA school situation jobs e slots**
  per capire come ottenere 16 posti simultanei in due aule. Confrontare
  le risorse More Students (o alternativa) se disponibili; non basta
  cambiare un numero di capienza lotto.
- Fase 2: implementare in codice originale sincronizzazione
  `registrati → eligibility marker` solo dove sicuro, con scope
  salvataggio/zona e rollback; test delle chiamate EA e fallback.
- Fase 3: collegare la selezione alla creazione dei **job esistenti**,
  distinguendo studenti NPC non-core, ruoli core, staff e Sims giocabili.
  Stabilire la classe usando gli effettivi phase jobs e non il solo
  registro. Evitare situazioni NPC aggiuntive.
- Test in-game incrementale prima del rollout 16/16: rispettare lezioni
  sedute alle 10:00, poi 14:00, mensa e prom. Niente promesse di presenza
  fino a riscontro fisico.

### Stato

**Analisi binaria Sonozaki COMPLETATA**. **Nessuna nuova build installabile
prodotta**. Prossimo obiettivo concreto: capacity + role/phase handoff EA.
