# Passo 45 — M43, mismatch ID/nome della categoria principale + fix runtime

## L'errore concreto

Better Exceptions su The Sims 4 1.129.39.1230 ha segnalato M41: `AttributeError: type object 'TestResult' has no attribute 'FALSE'` durante il test di `Iliyana:MHS32_Transfer_3_to_2`. Il modulo `mhs39_visibility_ui.py` usava due volte questa proprietà inesistente.

Il codice è stato corretto per restituire `TestResult(False, ...)` in caso di menu non disponibile e se la configurazione non è leggibile. La regola del trasferimento blocca i collegamenti a una terza classe non abilitata. La suite contiene un test che esegue il vero corpo della classe con una `FakeResult` priva di `FALSE`.

## Altra discrepanza sul menu

La vecchia M37 e discendenti hanno avuto la categoria radice con:
- `n='Iliyana:MHS_MainMenu'` nel tuning XML e nella SimData,
- ma `s=964622970` era derivato dal nome **diverso** `Iliyana:MHS_Root_Small_v37`.

Le categorie figlie invece usavano già numeri derivati dai propri nomi. Questa discrepanza era una plausibile causa di mancato collegamento in game: nella M41 la radice `MY HIGH SCHOOL` mostrava solo `Disattiva`, e Classe 1/2/3 e Impostazioni venivano mostrate fuori da essa.

M43 sostituisce soltanto l'identità numerica della radice con `1942018511`, hash compatto a 31 bit coerente con il nome reale `Iliyana:MHS_MainMenu`. Aggiorna insieme:
- tuning radice XML `s` e TGI;
- corrispondente TGI della SimData radice;
- quattro `_parent` delle categorie figlie in XML e nei binari SimData;
- tutti gli `interaction.category` che indicavano la precedente radice.

M43 conserva i testi delle categorie e le interazioni e include i miglioramenti M42. Il formato del menu è ancora `MY HIGH SCHOOL -> Classe 1, Classe 2, Classe 3 opzionale, Impostazioni`, con attivazione e disattivazione. Non è una nuova implementazione del registro scolastico.

## Build

Workflow https://github.com/iliyanadg/MyHighSchool/actions/runs/41167494132 — **tutti i test offline Python 3.7 superati**.

Artifact `MHS_M43_MENU_COMPLETO_FIX_ROOT_E_EXCEPTION`, con:
- `MHS_M43_MENU_GERARCHIA_E_FIX_TEST.package`
- `MHS_M43_MENU_GERARCHIA_E_FIX_TEST.ts4script`

Staticamente: 35 risorse, 5 tuning categorie + 5 SimData accoppiate, 15 script bytecode Python 3.7. M43 non è validata nel runtime macOS. L'ipotesi dell'ID/nome non è ancora causa confermata dell'errore di annidamento.

## Prova unica e ripristino

- Chiudere M41 senza salvare; conservare backup dati JSON esterni e vecchi file fuori Mods.
- Una sola coppia MHS in Mods; togliere M41 (e qualsiasi M42/M40/M37). Installare solo M43 (package+ts4script) lasciando XML Injector correttamente installato.
- Con gioco chiuso eliminare SOLO `localthumbcache.package` (ricreato dal gioco).
- Avviare save TEST, cliccare cassetta e fare SOLO due verifiche senza registrare studenti:
  1. Niente loop Better Exceptions e niente MCCC LastException relativo a MHS.
  2. Dentro `MY HIGH SCHOOL` sono visibili le voci `Classe 1`, `Classe 2`, `Impostazioni`; `Classe 3` deve comparire solo quando è stata abilitata (e le voci non devono comparire a livello generale della cassetta).
- Se una condizione fallisce chiudere, togliere M43, ripristinare M35B o M34 già testate; non ripetere click in loop. Richiedere massimo screenshot principale e rapporto errore.

## Restano da implementare in modo distinto

- cliccare conferma su GUI senza cheat/console, applicare le modifiche **anche mentre il tempo è in pausa**;
- inserimento/presenza effettiva degli adolescenti nel liceo, assegnazione di aule, staff, eventi EA.
- separazione salvataggi completa in caso di operazioni con JSON esterno.

## Esito reale M43 su Mac — 31 ottobre 2026, ore 12:24–12:25

La creatrice ha testato la M43 con screenshots della cassetta postale. **Il loop di Better Exceptions/MCCC non ricompare nelle schermate condivise**, e le tre classi hanno singoli sottomenu navigabili:
- Classe 1: trasferisci in Classe 2; rimuovi; consulta; prepara iscrizione.
- Classe 2: trasferisci in Classe 1; rimuovi; consulta; prepara iscrizione.
- Classe 3: prepara iscrizione (coerente con possibile classe vuota, da verificare la configurazione attiva).

**FAIL GERARCHIA**: MY HIGH SCHOOL contiene solo la voce «Disattiva MY HIGH SCHOOL»; Classe 1, 2, 3 appaiono direttamente al livello generale della cassetta postale. La sola coerenza del nuovo ID root con il nome, benché corretta staticamente, **NON ha risolto l'annidamento nel gioco**. Non dichiarare M43 funzionante rispetto alla specifica UI.

### Test successivi, senza generare altri package alla cieca

1. In-game, soltanto come controllo funzionale opzionale e su save TEST, controllare se in Impostazioni compare «Disabilita Classe 3» (con tre classi attive) o «Abilita Classe 3» (con due classi). La visibilità dei trasferimenti deve essere coerente. Non iscrivere/rimuovere studenti per indagare l'annidamento.
2. Priorità: ispezionare il **pacchetto M43 installato** nel Lot51 TDesc Builder (File > Open Tuning or Package) o Sims 4 Studio, non il solo sorgente:
   - categoria `Iliyana:MHS_MainMenu`, ID radice decimale `1942018511`, nessun parent;
   - categoria `Iliyana:MHS_Class_1_`, il suo Parent deve essere **esattamente 1942018511**; stessi controlli per Classe 2, 3 e Impostazioni;
   - controllare la **SimData effettiva** dei child con nome, parent e schema associato, preferibilmente esportata dal programma senza manipolazioni a offset.
3. Il builder attuale copia byte a byte SimData da una categoria preesistente e cambia manualmente pochi offset (incluso parent a 0x5c). I test verificano i byte, NON che Olympus risolva effettivamente la gerarchia: confronto con un piccolo pacchetto generato da TDesc, con un parent/child di prova su un'istanza di salvataggio duplicata, prima di modificare la M43.
4. Ricerca: la guida https://thesims4moddersreference.org/tutorials/creating-a-pie-menu/ spiega che TDesc genera il file SimData, che deve rappresentare ogni campo e che Parent è l'ID decimale della categoria superiore; questo conferma il tipo di controllo ma non diagnostica da solo l'errore M43.

**Non fare reinstallazioni né ulteriori micro-build per i soli click delle singole classi.** La causa del mancato annidamento resta aperta.


## Audit eseguito sui file M43 REALMENTE caricati dall'utente (31/10/2026)

Analisi diretta di `MHS_M43_MENU_GERARCHIA_E_FIX_TEST.package` e `MHS_M43_MENU_GERARCHIA_E_FIX_TEST.ts4script` caricati nella chat, NON solo delle fonti del builder GitHub. Il DBPF contiene **35 risorse** e l'archivio .ts4script contiene **15 moduli .pyc**, ZIP integro e magic byte Python 3.7 `420d0d0a`.

Tutti i cinque tuning `PieMenuCategory` sono accompagnati da una risorsa SimData (tipo `545AC67A`, gruppo `00E9D967`) con la stessa Instance ID:

| Categoria | ID | Parent XML | Parent SimData |
| --- | ---: | ---: | ---: |
| Iliyana:MHS_MainMenu | 1942018511 | 0 | 0 |
| Iliyana:MHS_Class_1_ | 869446548 | 1942018511 | 1942018511 |
| Iliyana:MHS_Class_2_ | 869619243 | 1942018511 | 1942018511 |
| Iliyana:MHS_Class_3_ | 869875458 | 1942018511 | 1942018511 |
| Iliyana:MHS_Settings | 126543528 | 1942018511 | 1942018511 |

Il pacchetto include 22 SuperInteraction tuning, di cui 19 hanno `category` esplicita; **nessuna delle 22 include `interaction_category_tags` espliciti**. Esempi di implementazioni che usano questa lista per custom pie menu esistono, ma la sua assenza NON identifica da sola la causa del *parent hoisting*: le sottocategorie vengono visualizzate in game e i dati parent sono presenti.

Conclusione: il package installato ha ID e riferimento Parent corretto sia in XML che nella SimData. La precedente ipotesi di un disallineamento id/name root non è sufficiente: M43 non ha risolto il problema sul Mac. Evitare nuove micro-build che cambiano soltanto `_parent` o gli ID. Distinguere prima tra contaminazione da copie MHS/altre mod, cache o salvataggio, e problema vero del parser UI. Test controllato suggerito: solo coppia M43 + XML Injector richiesto, con una copia isolata di `Mods` e salvataggio di TEST duplicato o nuovo, senza alterare la partita principale; usare stessa cassetta per comparare l'albero menu.

Riferimenti tecnici: https://thesims4moddersreference.org/tutorials/creating-a-pie-menu/ e https://modthesims.info/t/581879 .
