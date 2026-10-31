# Passo 43 — M41, menu completo in una build (31 ottobre 2026)

## Ricevuti e confrontati quattro file estratti dalla creatrice via Lot51 TDesc

1. `03E9D964!...0000000000003C93.sim_Friendly.xml`
2. `545AC67A!...0000000000003C93.sim_Friendly.SimData.xml`
3. `03E9D964!...000000000004DCE8.sim_SubCat_Friendly_Activities.xml`
4. `545AC67A!...000000000004DCE8.sim_SubCat_Friendly_Activities.SimData.xml`

Sono **riferimenti in formato XML**, non i file binari SimData installabili nel gioco.
Non sono inclusi nel repository o nel package per evitare di redistribuire risorse originali EA.

### Struttura EA osservata

- Root `sim_Friendly`: tuning ID `15507` (hex 0x3C93), `_collapsible=False`, SimData `_collapsible=0` e `_parent=0`.
- Child `sim_SubCat_Friendly_Activities`: ID `318696` (hex 0x4DCE8), `_collapsible=False`, SimData `_collapsible=0`, **XML e SimData `_parent=15507`**.
- SimData moderna: schema `PieMenuCategory`, hash `0xE2EAA141`, include `always_show_disabled_interactions`.

Il nostro file binario M37 è stato controllato su GitHub: contiene già `0xE2EAA141` ed il campo `always_show_disabled_interactions` (diagnostica https://github.com/iliyanadg/MyHighSchool/actions/runs/41165930507). Il problema non è quindi attribuibile senza ulteriori prove a uno schema obsoleto.

### M41 sviluppata in un unico pacchetto

File generati con pipeline Python 3.7:
- `MHS_M41_MENU_COMPLETO_EA_SCHEMA_TEST.package`
- `MHS_M41_MENU_COMPLETO_EA_SCHEMA_TEST.ts4script`

Build e suite test: https://github.com/iliyanadg/MyHighSchool/actions/runs/41166037504

M41 combina:
- M38: gerarchia `MY HIGH SCHOOL -> Classe 1 / Classe 2 / Classe 3 / Impostazioni`, azioni per classe e attiva/disattiva nel root;
- M39: la logica dei test di visibilità, classe 3 opzionale e possibilità di aggiungerla in seguito;
- M40: XML `_collapsible=False` e SimData `_collapsible=0` su **tutte e cinque le categorie**, con parent coerente e schema EA verificato.

Le cinque coppie XML/SimData condividono Type + Group corretto e istanza univoca; il root ha SimData parent 0, ogni figlia ha parent uguale al root. I 35 record DBPF vengono verificati e i 15 script sono bytecode Python 3.7. Nessun cambiamento a dati JSON, ID dei Sim, roster o codici di conferma. Test automatici superati.

### Importante: limiti

**La M41 non è stata testata nel client Mac.** È possibile che resti un problema di UI o che la logica dei test di visibilità `_test` non venga eseguita come previsto. Quindi non presentarla come mod completamente funzionante o pronta per il liceo.

Le operazioni sono ancora `ImmediateSuperInteraction` (spesso non funzionano finché il tempo è in pausa). Le conferme e la scrittura da interfaccia grafica senza console restano da implementare. EA High School Years non è controllata: il registro esterno è ancora sperimentale.

### Un solo ciclo di test (senza reiscrivere studenti)

1. Nel save TEST 11, con gioco completamente chiuso, **fare backup della cartella `MY_HIGH_SCHOOL_M25_TEST_DATA`**. La scrittura dei JSON esterni non segue Salva/Non salvare del gioco.
2. Rimuovere dalla Mods tutte le vecchie coppie MHS, in particolare M37/M36/M35B, ma conservarle fuori da Mods per recupero. Inserire solo la coppia M41 (package + ts4script) con XML Injector già installato.
3. Avviare il gioco, mettere in pausa. Cliccare cassetta postale. Se il menu non compare o Better Exceptions segnala `invalid category ID`, **NON usare alcun pulsante**; chiudere senza salvare, togliere M41 e ripristinare M35B (o M34), inviando screenshot report.
4. Se il menu appare, verificare che `MY HIGH SCHOOL (M38 TEST)`/root sia l'unico ramo principale MHS, con `Attiva` quando il registro è spento. Nessun pulsante Classe 1/2/3 a livello radice. La label root rimane quella di M38 perché M39/M41 hanno preservato STBL.
5. Attivare dalla radice con tempo avviato se necessario. Riaprire il menu: `Classe 1`, `Classe 2`, `Impostazioni` compaiono e Classe 3 è ancora nascosta quando la configurazione è 2 classi.
6. Aprire Classe 1 e Classe 2 per vedere l'insieme completo (Iscrivi/Consulta/Rimuovi/Trasferisci), senza selezionare alcun studente.
7. Aprire Impostazioni e selezionare `usa 3 classi` (possibilmente avviando tempo per eseguire l'interazione); verificare che Classe 3 ora compaia. Poi si può ripristinare lo stato precedente con 2 classi (Classe 3 vuota) e Disattiva; queste impostazioni scrivono nel JSON esterno.
8. Mandare screenshot: root spento, root acceso, Classe 1 aperta, menu con Classe 3 abilitata. Basta questo giro per controllare l'organizzazione; non ripetere prove già concluse su picker e studenti.

**Obiettivo dopo prima prova M41:** non continuare a generare pacchetti per un click alla volta. Se l'albero funziona, terminare insieme la logica di conferma nativa e la scrittura delle operazioni mentre il gioco è in pausa, poi fare un test end-to-end complessivo.

### Nota tecnica sulla denominazione
Il root compare ancora `MY HIGH SCHOOL (M38 TEST)` e la Classe 1 riporta `Classe 1 - M35 PROVA` perché il builder M41 ha preservato le STBL già verificate: è normale in questa build. Le etichette definitive si applicheranno dopo il test del menu; **non confondere il nome temporaneo con la struttura**.
