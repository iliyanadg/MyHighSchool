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
