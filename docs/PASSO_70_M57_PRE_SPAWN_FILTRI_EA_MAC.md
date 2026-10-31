# Passo 70 — M57: selezione preventiva EA via SimFilterService (Mac experimental)

## Da screenshot del 31 ottobre 2026 (M56)

La M56 legge correttamente il salvataggio e il registro a Copperdale e lancia richieste a studenti iscritti. Dopo la giornata alcuni iscritti come Ollie Mark, Yuki Behr, Jeb Harris, Kiyoshi Ito, Wolfgang Munch, Nyon Specter e Savannah Prezzo sono visibili, ma sono presenti anche Morgan Fyres, Duane Talle, Molly Prescott e altri non iscritti; il personale è quello scelto da EA, non MHS. Concludiamo che **creare situazioni EA aggiuntive non equivale a sostituire le scelte del bouncer della scuola**.

## Ricerca e fonti tecniche

- Zerbu Mod Constructor 5, preset EP12 `AllSimFiltersEP12.Presets.xml`: gli ID dei filtri EA degli studenti e della faculty sono **280516** studenti normali; **296396** docente 1, **300741** docente 2, **300742** preside, **300743** mensa, **300744** bidelli. Gli ID per Core NPC sono **276592** cheer, **276594** football, **276595** informatica, **276596** scacchi, **303766** cattivo/mean; **280466** rivale. https://github.com/Zerbu/Mod-Constructor-5/blob/master/Constructor5/Presets/SimFilter/AllSimFiltersEP12.Presets.xml
- Interfacce di `SimFilterService` (`submit_filter`, `submit_matching_filter`): il parametro `sim_constraints` può restringere gli ID Sim che EA considera. Il servizio mantiene punteggi, filtri esistenti e requisiti, invece di cambiare i tratti di ogni Sim o creare nuovi personaggi.
- Sonozaki School Management 2.1/2.2 e konanhurry Choose Your High School Classmates documentano la necessità di Core NPC specifici e i conflitti degli override EA con altre mod. https://www.patreon.com/SonozakiSistersSims4/posts/choose-high-2-1-132672857 ; https://www.curseforge.com/sims4/mods/choose-your-high-school-classmates .
- Nessun XML EA o codice di altre mod è incluso o copiato: l'adapter M57 originale chiama API di filtro con un elenco di IDs provenienti da registri MHS.

## Codice M57 su GitHub

1. `src/m57_selection/mhs57_school_manifest.py`: unica lista autorevole di studenti (max 8 per classe) e staff per slot, con distinzione degli adolescenti giocabili della famiglia attiva.
2. `src/m57_selection/mhs57_filter_policy.py`: mappa GUID EP12 ai ruoli e trasforma le chiamate al filtro EA, con restrizioni ai SimID iscritti e corrispondenza ai SimID del personale scelto. Se EA impone un vincolo esplicito, lo interseca (non lo cancella). Per `submit_matching_filter`, imposta `continue_if_constraints_fail=False`, `conform_if_constraints_fail=False` in modo da non ripopolare automaticamente con NPC casuali dopo un risultato vuoto.
3. `src/m57_selection/mhs57_filter_runtime.py`: installa wrapper sui due metodi EA una volta, **solo per i GUID dei filtri del liceo**. Gli altri filtri (famiglie, eventi, negozi ecc.) sono passati al codice EA originale. Se l'identità dello slot è incerta, MY HIGH SCHOOL è disattivata, o un parametro EA è sconosciuto: preserva il flusso originale e registra la ragione.
4. `src/m55_attendance/mhs55_attendance_auto.py`: con il filtro M57 installato blocca il vecchio sistema di situazioni aggiuntive M56 (per evitare doppi studenti), mostra quanti filtri EA sono stati veramente intercettati. Se nessun filtro è stato chiamato, questo contatore rimane 0: non interpretare l'installazione come prova che le classi siano state selezionate da MHS.
5. `tooling/build_m55_attendance_trial.py`: nuovo binario Mac versione M57, contenente package M54 baselined (63 risorse; 10 categorie+10 SimData) e **26 moduli** bytecode Python 3.7, incluso lo stesso registro staff già testato.
6. `tests/test_m57_school_manifest.py` e `tests/test_m57_ea_filter_policy.py`: validano 8 studenti TOTALI per classe, 3 giocabili nel registro come parte della capienza, staff e salvataggio, intersezione con vincoli di EA, chiamate pass-through dei filtri non scolastici e mantenimento dei metodi EA originali.

## Limitazioni da testare e correggere

- Questi strumenti intervengono nel servizio dei filtri EA, ma **non garantiscono** che tali filtri siano chiamati prima del caricamento del lotto o che tutti gli NPC vengano creati. La diagnostica M57 mostra il numero reale di chiamate filtrate dopo il caricamento. Prima prova su **salvataggio test** con M56 tenuta come rollback.
- I cinque filtri Core NPC restano **vanilla** perché il registro attuale non contiene assegnazioni a Cheer, Football, Scacchi, Informatica, Mean. Imporli a caso rischierebbe eventi/lezioni che non si avviano: la M58 dovrà implementare ruoli speciali scelti manualmente e validarne l'appartenenza ai club EA.
- I due docenti vengono nominati secondo gli ID scelti, ma il servizio EA può rifiutarli se non soddisfano il filtro originale (età/career/ruolo ecc.). I due custodi e tre addetti mensa nel registro sono **candidati**, non prova che EA abbia 2/3 situation jobs. Non aumenta automaticamente la capienza del personale.
- Se un filtro EA non ha nessuno degli ID selezionati idoneo, possono mancare personaggi. Meglio ripristinare M56 e segnalare contatori/errori, non forzare NPC scelti rompendo le situazioni.
- Non esiste ancora la terza aula fisica e non viene modificata la capacità EA del lotto. La capienza 8/classi è un contratto di registro, NON un'espansione della capienza EA.
- I playable attivi non sono imposti come NPC attraverso la selezione di filtro: devono essere iscritti manualmente entro gli 8 posti, poi EA li accompagna normalmente.
- Rischio di incompatibilità con Sonozaki, More Students, Rex Strict, o altre mod che intercettano gli stessi metodi EA. Per la prova disattivare gli altri controller liceali.

## Test Mac solo dopo CI positiva

1. Chiudere The Sims 4. Copiare **il salvataggio di prova** e la directory esterna `MY_HIGH_SCHOOL_M25_TEST_DATA`.
2. Sostituire la coppia M56 con la coppia M57 **della medesima esecuzione** CI, senza tenere più versioni.
3. Avviare la partita **dalla casa**, poi portare i giocabili a Copperdale in un nuovo giorno di scuola. Non riutilizzare la situazione scolastica EA creata con M56 nella stessa giornata, altrimenti non si può testare lo spawn preventivo.
4. Aprire `M55 – Consulta presenze automatiche`: leggere `Selezione M57: installata` e, dopo il caricamento al liceo, `Filtri limitati: N`. Se **N=0**, il controller non è intervenuto nella selezione (non dichiarare successo).
5. Verificare visualmente gli ID reali degli iscritti e confrontarli con quelli di EA; confrontare preside/docenti/bidello/mensa.
6. Se un docente o membro di staff non arriva oppure le lezioni si bloccano: interrompere il test, uscire senza sovrascrivere e ripristinare M56; il filtro può essere troppo restrittivo per le condizioni interne di EA.

**Stato**: controller M57 codice completo per i filtri normali e staff, Core roles esclusi intenzionalmente; test offline/CI e poi Mac necessari. Non pubblicare come scuola completa finché i presenti reali e le lezioni non sono stati verificati.
