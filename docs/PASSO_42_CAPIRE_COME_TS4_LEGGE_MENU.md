# Passo 42 — come The Sims 4 legge i menu e come verificare il nostro bug

31 ottobre 2026. Richiesta della creatrice: *«dove possiamo trovare, come legge queste cose il gioco?»*

## Fonti tecniche
- Guida specifica: https://thesims4moddersreference.org/tutorials/creating-a-pie-menu/
- Sims 4 Studio (strumenti Extract Tuning, Game File Cruiser): https://thesims4moddersreference.org/reference/s4s-top-menus/
- TDesc Builder (Lot51): https://tdesc.lot51.cc/
- Spiegazione del motore Python vs client e della SimData: https://lot51.cc/simdex/game-concepts
- Esempio di build SimData di menu: https://github.com/derneuere/HistorianCareer (sezione "Pie menu")
- Visualizzatore riferimenti EA: https://app.ts4modhound.com/

## Componenti del nostro menu
1. `.package`: archivio DBPF con i file tuning XML delle categorie/interazioni, SimData binaria, tabelle di stringhe STBL e risorse necessarie.
2. Categoria `PieMenuCategory`: il tuning ha `s` (Instance ID), `_display_name`, `_collapsible` e `_parent` (eventuale categoria padre). Type ID tuning = `0x03E9D964`, Group 0 nel nostro progetto.
3. SimData: companion della categoria, Type ID `0x545AC67A`, Group `0x00E9D967` nel nostro progetto; rispecchia gli stessi campi, incluso parent, con struttura e instance corretti. Il client (Olympus) utilizza questa SimData per costruire la mappa dei pie-menu.
4. Interazioni: ciascuna porta un `category` di riferimento al menu e alcuni `interaction_category_tags`. Il tuning deve puntare alla categoria con ID effettivamente valido.
5. `.ts4script`: zip di script Python 3.7 che gestiscono picker, azioni, salvataggi e test di visibilità. Non sostituisce la SimData.

## Stato verificato su Mac (non confondere)
- M34: gestione attiva/disattiva e scelta 2/3 classi persistono nello slot 11 dopo riavvio. Solo registro JSON esterno; non controlla la scuola EA.
- M35B: **sottomenu autonomo** `Classe 1 - M35 PROVA` compare, contiene Consulta e Rimuovi, picker e iscritti corretti.
- M36: aggiunta `_parent` verso il root a ID 64-bit, Better Exceptions "invalid category ID", cassetta non interattiva.
- M37: entrambi i category IDs sotto 2^31, cassetta funzionante, ma Classe 1 continua a comparire **separata**, non sotto MY HIGH SCHOOL.
- M40: variano soltanto i flag `_collapsible=False` nelle coppie XML+SimData di root e child, test automatici superati, MA non ancora verificata nel gioco. Questa è un'ipotesi, non una spiegazione confermata.

## La ricerca corretta: confrontare con EA
- Da Sims 4 Studio (su Mac): `Tools → Extract Tuning...`, cercare `pie_menu_category` / `sim_Friendly` e una sottocategoria nota, per es. `sim_SubCat_Friendly_Activities`, oppure fare `Extract All` e filtrare le categorie. Esportare tuning e **SimData** associata, non solo XML.
- In alternativa, su https://tdesc.lot51.cc/ usare `Import EA Tuning` e cercare `sim_Friendly` e le sue sottocategorie. Aprire prima il padre e poi la figlia.
- Confrontare: (A) root EA, (B) sottocategoria EA, (C) root M37, (D) child M37. Verificare `Instance ID`, Type, Group, `_parent`, `_collapsible`, `_display_name`, `interaction_category_tags`, dati reali della SimData (schema incluso), non soltanto la dimensione e un valore a offset fisso.
- La prova più affidabile dopo il confronto è far generare una categoria padre+figlia completa con **TDesc Builder** e importare la coppia XML/SimData coerente nel package. Evitare nuove modifiche binarie a offset indovinati quando è possibile generare le risorse dal descrittore EA.
- Se il menu sembra diverso nonostante XML corretti, ripetere solo dopo chiusura del gioco, una sola versione MHS nella cartella Mods, cancellazione della cache `localthumbcache.package` (file ricostruibile), senza toccare i salvataggi. Non cancellare altri file indiscriminatamente.
- In caso di errori usare `BE-UIExceptionReport.html`, `lastUIException.txt`, eventuali `LastException*.txt` del nuovo avvio e i log della mod. Non trarre conclusioni da "Found 0 Interaction Mod": può coesistere con il vero errore `invalid category ID`.

## Prossima strada di sviluppo
1. Validare la gerarchia delle categorie su un esempio EA e/o su un pacchetto pubblico compatibile.
2. Portare `MY HIGH SCHOOL → Classe 1` correttamente sotto il root SENZA variare l'algoritmo del registro. M35B resta fallback.
3. Poi introdurre la struttura completa `MY HIGH SCHOOL → Attiva/Disattiva → Classe 1/2/3 (ultima opzionale) + Impostazioni`.
4. Lo stato deve nascondere realmente le voci nel client, non limitarsi a un modello dati puro. La Classe 3 può essere abilitata dopo aver usato la scuola con 2 classi.
5. Interazioni in pausa e conferma GUI richiedono ancora una soluzione tecnica specifica e test reale. Nessuna riscrittura automatica del JSON senza un'azione di conferma.
6. La gestione della frequenza scolastica EA, delle tre aule e dei docenti è ancora lavoro separato.

Non redistribuire i file originali EA nella repo pubblica; usare risorse locali solo per confronto.

## Conferma con due tuning EA esportati dalla creatrice

La creatrice ha estratto da Lot51 TDesc due esempi EA (qui riportiamo solo i campi essenziali e non redistribuiamo il tuning EA):
- `sim_Friendly`: `s=15507`, `_collapsible=False`, nessun `_parent` esplicito, `_display_priority=9`, icona propria.
- `sim_SubCat_Friendly_Activities`: `s=318696`, `_collapsible=False`, `_parent=15507`.

Quindi il valore parent si riferisce al tuning ID *decimale* esatto del padre, e il flag `_collapsible` è esplicitamente `False` per entrambi. L'esempio dà riscontro alla modifica di M40 (root + child `_collapsible=False` e SimData 0), ma **non dimostra che M40 sia già funzionante nel gioco**. Il controllo delle coppie SimData resta necessario: l'XML da solo non dimostra che il client risolva le categorie.

Fonti esterne supplementari:
- https://thesims4moddersreference.org/tutorials/creating-a-pie-menu/ spiega il comportamento di `Collapsible`: con una sola interazione la categoria può sparire a favore dell'interazione.
- https://modthesims.info/showthread.php?t=645711 segnala la necessità di un `_collapsible=False` coerente nel tuning e nel companion SimData.
- https://modthesims.info/download.php?c=1&ht=0&page=3&pp=25&t=652181 conferma un caso risolto impostando `_collapsible=False` e SimData `_collapsible=0`.

M40 compilata: https://github.com/iliyanadg/MyHighSchool/actions/runs/41164792986 , artefatto `MHS_M40_MENU_COLLAPSIBLE_FALSE_SOLO_TEST`. Usare solo per prova isolata nella partita TEST, con backup M35B/M37 fuori Mods. Verificare prima che la cassetta si apra; poi che Classe 1 appaia DENTRO MY HIGH SCHOOL, non nel menu radice. Non effettuare rimozioni o commit.
