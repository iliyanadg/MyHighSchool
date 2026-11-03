# M109 — Contratto di integrazione M108: una sola attivazione, verifica EA reale, rollback

**Stato:** progettazione / non implementato, NON una nuova beta, nessuna prova in-game.
**Ramo:** `feature/m55-presenze-studente-test`. Non modificare `main`.
**Scopo:** trasformare i molti moduli M108 *offline-only* in un unico percorso
controllato, verificabile e reversibile, evitando doppie patch e falsi positivi.

## Risultato richiesto dalla giocatrice

- Esattamente **due classi, otto adolescenti per classe**.
- **Tre giocabili**, assegnati manualmente alle classi, **13 NPC precisi**.
- Tra i 13 NPC, **cinque ID per i cinque ruoli Core EA esatti**, otto per
  i job Base; niente NPC estranei, sostituti casuali o Sim inventati.
- Insegnanti, preside, custodi e mensa mantengono le loro identità e i job EA.
- Il registro sopravvive ai giorni e viene letto per salvataggio; nessuna
  riassegnazione a caso. Cambi durante la scuola applicati il giorno dopo.
- Fasce EA originali: 09:30 ingresso a lezione, 10:00 lezione, 13:30 preparazione,
  14:00 lezione. Non alterare pranzo, prom, diplomatura o lotti diversi.
- Nessuna modifica irreversibile al salvataggio o ai tratti dei Sim.

## Stato verificato (non inferire che sia una release)

La base M108 attuale contiene diversi **prototipi offline-only**:
`mhs108_native_invitation`, `native_precreate`, `native_base_count`,
`school_filter_scope`, `no_show_guard`, `unified_lessons`,
`post_bouncer_audit`, `spinup_barrier`, `npc_soft_cap_audit`,
`16_student_reconciliation`.

I moduli chiedono molti `REQUIRED_LIVE_GATES`, ma i test passano solo flag
**sintetici**: non esiste ancora un provider runtime verificato che li
certifichi. All'ultimo controllo del 03-11-2026 la GitHub Actions CI
del commit `e25f5426` era **queued**, non passed. Non creare una release
basata sui soli mock.

**Rischio di architettura critico**: più strategie di hooking
`WeeklyScheduleSituationData.try_start` sono alternative, NON cumulative.
Il controller M109 deve selezionare SOLO `mhs108_unified_lessons`;
gli adattatori di studio `mhs108_ea_phase_adapter` e
`mhs108_class1_try_start_bridge` restano disattivati.

## Una sola macchina a stati per il giorno scolastico

| Stato | Attivazione | Prova necessaria | Fallimento |
|---|---|---|---|
| S0 DISATTIVATO | Salvataggio normale | Nessun hook M108 | Lascia EA vanilla |
| S1 REGISTRO_VALIDATO | Fuori dalla giornata attiva | Manifesto canonico 2x8/3+5+8, staff umano, stesso save | Non iniziare |
| S2 PRIMA_DEL_CALENDARIO | Prima della prima richiesta EA | Origine EA nativa, contesto save/day/zone, nessun controller concorrente, 5 ruoli Core verificati come *piano* | Non installare |
| S3 INVITI_EA_CREATI | Calendario EA chiama Base poi Core | Otto situation ID Base + uno Core, 13 ID distinti nel guest list | Blocca ulteriori richieste MHS e segnala, niente refill |
| S4 BOUNCER_ASSEGNATO | Dopo `on_all_sims_spawned_during_zone_spin_up` oppure barriera late comprovata | `SituationManager.get` + `all_sims_in_job_gen` dei job effettivi | Non chiamare i 13 presenti; report dettagliato |
| S5 LEZIONE_VERIFICATA | 09:30, 10:00, 13:30, 14:00 | Un solo hook `try_start`, classe 1 a due vie, classe 2 con staff, job readback post-Bouncer | Segnala fase incompleta, non ritentare a caso |
| S6 16_VERIFICATI | Controllo prima/durante ogni lezione | 13 NPC di classe giusta + 3 playable nei job EA + esattamente 16 teen sul lotto, tutte le situation del periodo enumerate | Nessun pass fittizio |
| S7 POSTI_VERIFICATI | Dopo assegnazione di lezione | Banco/aula e comportamento osservati per ciascun Sim; separati dalla sola membership EA | `SEATING_UNVERIFIED` |
| S8 FINE_GIORNO | Dopo la fine normale EA | Report, rilascio per-day dei guard e ticket; registro per-save intatto | Cleanup e report anche in caso di errore |

Le transizioni devono essere **monotone**. Un job o situazione falliti
non possono tornare automaticamente «verificati» semplicemente dopo un
nuovo invito. Le quattro fasce orarie devono utilizzare contatori distinti;
non riciclare l'esito delle 10:00 come prova delle 14:00.

## Ordine degli hook e rollback atomico

Prima di toccare qualsiasi classe EA, costruire un **preflight completo**,
con controlli positivi ricavati da API *live* concrete, mai passando
arbitrariamente `{gate: True}`.

Solo dopo il preflight:
1. Installare un contatore Base EA 6→8 **per calendario scolastico
   verificato**, e il solo hook `SituationManager.create_situation`.
2. Proteggere i 13 inviti con filtro *solo sulla richiesta* e
   `clone_for_replace` mirato. Le riserve Core locali non sono vere
   prenotazioni del Bouncer: non affermare il contrario.
3. Installare **un solo** wrapper `try_start` con controller
   unificato, e leggere i job attraverso l'audit differito.
4. Installare l'osservatore di `on_all_sims_spawned_during_zone_spin_up`.
5. Attivare l'intero sistema solo dopo che tutti gli installer hanno
   restituito uninstall validi. Se uno fallisce, ripristinare
   **tutti** gli hook installati nell'ordine inverso.

Il rollback deve essere testato per ogni passo e non deve mai richiamare
il metodo EA `create_situation` due volte dopo un'eccezione.
Nessun tentativo di undo può ripristinare retroattivamente una situazione
EA già avviata: segnalarlo esplicitamente nei report. Un installer può
rifiutare la partenza prima del calendario anziché attivarsi a metà giorno.

## Fonti runtime che mancano ancora (gates da implementare, NON bypassare)

- **Origine del calendario**: vera classe EA, schedule GUID, giorno/zona
  del salvataggio e prova che non sia già partita.
- **Identità NPC e roster**: `SimInfo` adolescente umano realmente nel
  salvataggio, selezionabile vs NPC, appartenenza effettiva al registro.
- **Job e filtro originali**: risorse EA del gioco corrente
  (Base 277894, Core cinque job) e guest list nativa.
- **Due vie Classe 1**: compatibilità della classe shadow col
  runtime/metaclasse EA, cap modificato solo per chiamata,
  lettura autentica delle idoneità WithTrait/NoTrait.
- **Bouncer cap**: contatori `number_of_npcs_instantiated`,
  `number_of_npcs_leaving`, `npc_soft_cap` misurati sulla zona;
  un margine positivo non è garanzia di presenza.
- **Lettura post-Bouncer late**: la callback spin-up osserva il
  caricamento; manca una barriera comprovata per i job assegnati
  quando la zona è già in esecuzione.
- **Playables e banchi**: verificare tre adolescenti giocabili
  nelle vere situazioni e il loro percorso fisico verso
  la corretta aula; il job non basta a provare che siano seduti.
- **Conflitti**: impedire l'attivazione in presenza di
  Sonozaki HS/M106/controller scolastici concorrenti,
  senza intaccare mod di scuola elementare non coinvolte.

## Protocollo di collaudo a step, su copia del salvataggio

**T0 — Test automatici effettivamente verdi:** Python 3.7/3.11, XML
e test sintetici di CI; raccogliere log di fallimento, correggere.
Nessuna beta se la CI più recente è queued/failing.

**T1 — Osservabilità read-only:** una diagnostica Mac che verifica
solo origini API, conteggio del cap e job reali, senza cambiare
spawning, filtri o situazione; report con source dei dati.

**T2 — Inviti Native controllati:** riutilizzo delle situazioni EA,
13 ID esatti, zero sostituti o extras, nessun conflitto.

**T3 — Lezioni:** Classe 1 via doppia, Classe 2, entrambi gli
orari; nessun doppio incarico; tutelare docenti/preside.

**T4 — Presenze vere:** due giorni scolastici consecutivi con
gli stessi 16 adolescenti; distinzione fra job presenti,
posizione nell'aula e seduti; no-show senza sostituto.

Una verifica fallita deve produrre una spiegazione specifica
e il prossimo esperimento **minimo**, non una nuova famiglia
di 10 mod sperimentali.

## Primo lavoro concreto successivo

1. Attendere/eseguire fino a completamento una CI che includa
   M108, identificare tutti i test falliti per causa.
2. Correggere le discrepanze e fare una esecuzione locale
   indipendente sui mock e XML reali, evitando altra crescita
   del numero di commit finché la CI non termina.
3. Solo poi scrivere una funzione `M109SchoolActivation`
   (preflight, install, uninstall, stati) con un **unico entrypoint**
   e un test di rollback su ogni hook; modalità default OFF.
4. Prima di dichiarare "funzionante", prova in-game su
   una copia del salvataggio e osservazioni native complete.

**Vietato fare claim «16/16 funzionano» senza prove dal gioco.**

## Avanzamento M109: coordinatore atomico e ripristino EA (prototipo offline)

**Implementato, non collegato a una build giocabile:**
- `src/m109_activation/mhs109_atomic_activation.py`
  contiene `M109SchoolActivation`: manifesto canonico verificato
  con `prepare_fixed_manifest` (2 classi da 8, 3 giocabili,
  5 Core, 8 Base); prova preventiva di salvataggio, giorno,
  zona, calendario, API EA e assenza di controllori concorrenti;
  attivazione una volta sola della sequenza di **sei hook M108**
  (conteggio Base, precreate, school filter, no-show guard,
  lezioni unificate, osservatore post-Bouncer);
  `disarm` e ripristino in **ordine inverso**, con stato
  `ROLLBACK_INCOMPLETE` se uno dei ripristini fallisce.
- La struttura di ogni stage prevede `install` e
  `restore` **già disponibili prima della mutazione**.
  Questo copre l'errore di un installer che riesce a
  modificare un metodo ma genera un'eccezione prima di
  restituire il callback di uninstall.
- `src/m109_activation/mhs109_native_hook_stage.py`
  contiene `M109NativeStage`: cattura i descrittori EA
  nativi originali prima di installare i wrapper M108;
  se l'installer fallisce parzialmente, ripristina soltanto
  metodi con il marker M108 esatto. Per
  `school_filter_scope` sono controllati **entrambi**
  `__init__` e `get_additional_filter_terms`.
  Se una mod terza interviene nel frattempo,
  la M109 **NON sovrascrive** il suo wrapper:
  segnala invece ripristino incompleto.
  Per le mutazioni *sulle singole richieste*
  `BouncerRequest` serve anche un cleanup apposito
  (non basta ripristinare i metodi della classe).
- Nessun meccanismo globale installato automaticamente;
  il provider degli attestati runtime reali
  **non è stato ancora implementato**.

**Test aggiunti** al job Mac Python 3.7 e al
`unittest discover`:
- `tests/test_m109_atomic_activation.py`:
  attivazione di sei stage, ordine, preflight,
  errori dopo mutazioni parziali, eccezioni durante
  restore, blocco al cambio save/day/zone e
  singola attivazione per sessione.
- `tests/test_m109_native_hook_stage.py`:
  metodo EA classmethod originale, restore
  descrittore, doppio metodo di SchoolFilterScope,
  fallimento a metà, callback assente, controllo
  mod concorrenti, owner classmethod errato e
  cleanup che richiede un secondo tentativo.

**Limiti noti e requisiti prima del runtime:**
1. Test M109 usano classi e flag *sintetici*, non
   verificano compatibilità con la metaclasse EA
   di `WeeklyScheduleSituationData` o col Bouncer.
2. Il vero provider EA per i 15
   `REQUIRED_RUNTIME_EVIDENCE` NON esiste; il campo
   `source='EA_RUNTIME_OBSERVATION'` dei test è
   soltanto un valore di fixture e non va mai usato
   come prova a runtime.
3. M109 non usa ancora `M109NativeStage` con sei
   proprietari EA verificati in-game: necessita
   un adattatore di ambiente che fornisca owner,
   risorse native, contesti e installer reali M108.
4. Per `SchoolFilterScope`, l'installer M108
   modifica filtri di request individuali:
   una procedura di cleanup deve chiamare
   `scope.restore()` anche se la patch ha
   fallito dopo il primo dei due metodi.
5. Ripristinare classmethod EA non può
   annullare una situazione scolastica che
   EA ha già creato. Non intervenire su save
   principale e non spacciare un rollback come
   cancellazione di effetti EA già prodotti.
6. Le esecuzioni GitHub Actions più recenti
   risultavano **queued** all'ultimo controllo.
   Non dichiarare i test M109 superati finché
   non si ottiene il relativo risultato.

**Prossimo lavoro tecnico:** validare i test
eseguiti e i loro traceback, poi realizzare un
*live adapter read-only* che misuri i gate EA
e fornisca gli owner nativi. Soltanto dopo
autorizzare l'installazione dell'intera catena
e una beta su copia del salvataggio.

## M109 — verifica sorgenti EA esistenti e sonda di metodi in sola lettura

**Nuovi file:**
`src/m109_activation/mhs109_readonly_ea_probe.py`,
`tests/test_m109_readonly_ea_probe.py`.

**Verifica reale dei sorgenti EA già condivisi (AST locale, non mock):**
- `base_situation.py`, classe `BaseSituation`:
  `all_jobs_gen(self)`, `all_sims_in_situation_gen(self)`,
  `all_sims_in_job_gen(self, job_type)`,
  `get_current_job_for_sim(self, sim)`.
- `bouncer.py`, classe `Bouncer`:
  `request_all_sims_during_zone_spin_up(self)`,
  `assign_all_sims_during_zone_spin_up(self)`,
  `_monitor_npc_soft_cap(self)`.
- `bouncer_request.py`, classe `BouncerRequest`:
  `clone_for_replace(self, only_if_explicit)`,
  `get_additional_filter_terms(self)`,
  `__init__(...)`.
- Esistono anche classi *factory* con nomi simili: la M109 deve
  scegliere il vero owner `BouncerRequest`, non un factory.

La nuova `inspect_runtime_shapes(classes)` **non modifica EA**:
verifica soltanto la presenza dei nomi, la corretta
natura `classmethod` per i due metodi WeeklySchedule,
la classe in cui ciascun metodo è dichiarato,
e rileva marker di patch MHS/M108/M96/M105 già presenti.
Restituisce `NATIVE_EA_METHODS_NOT_READY` su incongruenze,
e `METHOD_SHAPES_AVAILABLE_UNVERIFIED` se i metodi esistono.
**Non restituisce MAI autorizzazione al gioco**:
`activation_authorized_by_game=False` per definizione.
Un test con classi Python simulate non può provare
che si tratti dei veri oggetti EA presenti in una partita.

**Resta da eseguire** la vera lettura dei tipi EA in un gioco
caricato, e i controlli dei SimInfo/tuning risorse, conteggi
dinamici Bouncer, Class1 shadow e provenienza calendario.
La sonda è quindi diagnostica preparatoria, NON un nuovo
controller da attivare.

## M109 — diagnostica console realmente eseguibile (solo dopo build verde)

**Realizzato nel sorgente, non ancora validato nel gioco:**
- `src/m109_activation/mhs109_game_probe.py`: registra
  `mhs109.probe` con la normale API
  `sims4.commands.Command(..., CommandType.Live)`.
  Il comando importa **solo quando viene usato**
  le classi native:
  `venues.weekly_schedule_zone_director.WeeklyScheduleDay`,
  `WeeklyScheduleSituationData`,
  `situations.situation_manager.SituationManager`,
  `situations.bouncer.bouncer_request.BouncerRequest`,
  `situations.bouncer.bouncer.Bouncer` e
  `situations.base_situation.BaseSituation`.
  Se l'installazione EA reale ha una struttura diversa,
  riporta `EA_CLASS_MISSING`/`IMPORT_<tipo>` e
  NON inventa l'esito. Non raccoglie Sim ID.
- Richiama `inspect_runtime_shapes` e salva
  `MHS_M109_NATIVE_METHODS_READ_ONLY.json` in
  `Documents/Electronic Arts/The Sims 4/
  MY_HIGH_SCHOOL_M25_TEST_DATA/`.
- La diagnostica **non importa alcun controller M108**,
  non attiva `try_start`, non intercetta il Bouncer,
  non cambia classi, Sim, studenti, presenze,
  situazioni o il registro. NON è il liceo M109.
- `tooling/build_mhs109_readonly.py`: produce
  `MHS_M109_NATIVE_METHODS_READ_ONLY.ts4script` con
  **soltanto due .pyc**, senza `.package`, e
  rifiuta Python diverso da **3.7** e bytecode
  diverso da `42 0D 0D 0A`.
- `tests/test_m109_game_probe.py`: testa la
  registrazione del comando senza eseguirlo,
  moduli EA simulati, lettura a sola visualizzazione,
  import non riusciti, nessun M108 hook incluso,
  scrittura sicura di report in cartella temporanea.
- Il workflow `.github/workflows/offline-tests.yml`
  contiene un job **indipendente**
  `m109_readonly_mac_probe`: testa, compila con
  Python 3.7, verifica l'archivio e carica
  l'artifact `MHS_M109_NATIVE_METHODS_READ_ONLY_NOT_CLASSROOM_MOD`.

**Condizioni prima dell'eventuale installazione:**
1. GitHub Actions di questo *esatto commit* deve
   concludere con **success** del job specifico.
2. Scaricare unicamente l'artifact verificato,
   non compilare localmente con Python 3.13.
3. Usare una copia di salvataggio e un'installazione
   di Mods priva di vecchie coppie MHS.
4. Comando in console `mhs109.probe`, fornire
   il JSON risultante per il confronto degli owner
   EA e dei metodi disponibili.
5. Questa prova **non vale** come test di
   presenza/lezione 16/16: dopo la diagnostica
   manca ancora l'adapter vero di integrazione M109.

All'ultimo controllo la CI M109 era **queued**.
Non dichiarare il .ts4script pronto al download
finché il workflow non fornisce l'artifact.
