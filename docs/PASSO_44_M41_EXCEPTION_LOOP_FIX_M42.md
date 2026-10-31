# Passo 44 — M41 errore runtime e fix M42 (2026-10-31)

## Evidenza reale dal Mac (game version 1.129.39.1230)

La creatrice ha installato M41 `MHS_M41_MENU_COMPLETO_EA_SCHEMA_TEST`.
La cassetta postale apre il menu ma Better Exceptions v3.17 e MCCC segnalano di continuo:
```
Exception during call to test method on
<class 'sims4.tuning.instances.Iliyana:MHS32_Transfer_3_to_2'>
(AttributeError: type object 'TestResult' has no attribute 'FALSE')
```
Il report attribuisce la *possible cause* a `/MHS_M41_MENU_COMPLETO_EA_SCHEMA_TEST.package` (confidence 30%), mentre la causa diretta visibile nel sorgente è il nostro script `src/m39_visibility/mhs39_visibility_ui.py` (bundled .ts4script) che usava `TestResult.FALSE`.

Screenshots:
- root mailbox: `Impostazioni...`, `Classe 1...`, `Classe 2...`, `Classe 3...` compaiono ancora **al livello della cassetta**, invece che dentro `MY HIGH SCHOOL`.
- cliccando `Impostazioni...` apre il suo comando; `MY HIGH SCHOOL...` appare separato e mostra soltanto Disattiva. Quindi la gerarchia **NON è ancora risolta**, nonostante schema e `_collapsible` staticamente verificati.
- Le notifiche ripetute e il simulatore che deve rivalutare il menu sono coerenti con eccezioni continue nel metodo `_test`.

## Correzione implementata: M42

- Sostituzione dei due riferimenti a `TestResult.FALSE` nel corpo del mixin con `TestResult(False, 'MY HIGH SCHOOL: azione non disponibile')`. Questo elimina l'accesso inesistente responsabile dell'AttributeError, senza sostituire il fallimento con successo. In-game effectiveness ancora da verificare.
- `mhs39_visibility_rules.allowed(...)`: nuova azione `transfer` per controllare sia la classe d'origine sia quella di destinazione. La Classe 3 disattivata impedisce di vedere trasferimenti 1→3 o 2→3.
- La struttura di categorie M41 è conservata. Priorità della categoria radice 9 in XML e nel corrispondente campo SimData, in linea con l'esempio `sim_Friendly` esportato dalla creatrice; **priorità non certifica annidamento**.
- Testi delle quattro impostazioni puliti: `Attiva MY HIGH SCHOOL`, `Disattiva MY HIGH SCHOOL`, `Disabilita Classe 3`, `Abilita Classe 3`. Nessun cambio dati roster o salvataggi.
- Suite test Python 3.7 comprende un finto `TestResult` **privo di attributo `FALSE`** ed esegue il vero codice del mixin, con configurazione 2/3 classi e fallimento di lettura. 35 risorse DBPF, cinque categorie e cinque SimData, 15 .pyc Python 3.7, tutta la suite offline superata.

Workflow completato: https://github.com/iliyanadg/MyHighSchool/actions/runs/41167275089
Artifact `MHS_M42_CORRETTO_EXCEPTION_E_MENU_TEST`, con:
- `MHS_M42_MENU_CORREZIONE_EXCEPTION_TEST.package`
- `MHS_M42_MENU_CORREZIONE_EXCEPTION_TEST.ts4script`

## Prevenire altri cicli di notifiche

1. STOP M41; chiudere gioco senza salvare. Eseguire backup del registro esterno `Documents/Electronic Arts/The Sims 4/MY_HIGH_SCHOOL_M25_TEST_DATA` e del save TEST.
2. Togliere M41 `.package` e `.ts4script` da Mods; NON tenere contemporaneamente più release MHS; conservare M35B o M34 fuori Mods come fallback.
3. Se si desidera provare M42, con gioco chiuso togliere SOLO `localthumbcache.package` nella cartella The Sims 4 (rigenerabile, non è un salvataggio) e installare un'unica coppia M42. Non reinstallare M41.
4. Avviare il save TEST. Click sulla cassetta in pausa: **prima verifica l'assenza del loop Better Exceptions**; la M42 non è dichiarata funzionante finché la partita non la conferma. La presenza di `MY HIGH SCHOOL` root + classi **ancora esterne** conta come test non superato della gerarchia.
5. Senza toccare gli iscritti, vedere se i comandi Classe 3 e 1→3 sono nascosti quando si usano 2 classi. Se si apre `MY HIGH SCHOOL` controllare se dentro contiene tutti i sottomenu. Raccogliere solo due screenshot: livello radice dopo il click, livello `MY HIGH SCHOOL` dopo averlo aperto.
6. Se ricompare un'eccezione: fermare subito, chiudere senza salvare, reinstallare la M35B testata; non continuare a cliccare la cassetta per evitare valanghe di log.

## Problema residuo separato: annidamento

Perché le categorie appaiano a livello radice nonostante parent coerenti, occorre investigare il comportamento del runtime UI Olympus (si è già verificato in M37 senza il mixin M39). Un errore della funzione di visibilità NON spiega necessariamente questa persistenza; la correzione del loop non deve essere confusa con una correzione certa del menu.

Prima di un'altra modifica alla gerarchia:
- Ispezionare con Sims 4 Studio `MHS_M42_...` e vedere XML+SimData di tutte le 5 categorie, mostrando `_parent` nel formato importato dal tool.
- Confrontare il root e una figlia di categoria con i due EA `sim_Friendly` / `sim_SubCat_Friendly_Activities`, non soltanto i campi patchati a offset.
- Per il caso che appaia ancora a livello radice provare generazione originale della coppia dal Lot51 TDesc, NON scritture binarie manuali ulteriori prima di capire il dato differente.
- Lavoro ancora aperto: finestre di conferma e scrittura dei registri a gioco in pausa, e controllo reale del liceo EA.
