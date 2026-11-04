# Installazione pulita MY HIGH SCHOOL — Classroom Control su Mac

La nuova coppia prevista è `MHS_CLASSROOM_CONTROL.package` e `MHS_CLASSROOM_CONTROL.ts4script`, generata dalla stessa compilazione con relativo manifest SHA-256. Questa revisione integra il progetto e richiede ancora verifiche nel gioco: non è una dichiarazione di release stabile o di compatibilità universale.

La revisione dopo il primo collaudo contiene **50 moduli**; il modulo aggiunto
legge gli ingressi e confronta personale scelto/effettivo, senza assegnare job.
Per la seconda giornata seguire `SECONDA_GIORNATA_DIAGNOSTICA.md`.
I precedenti ZIP a 47/49 moduli restano backup: installare una sola coppia.

## Dati da conservare

Chiudere The Sims 4 e fare una copia dell'intera cartella:

`~/Documents/Electronic Arts/The Sims 4/`

Preservare **sempre** `saves/`, i backup `.save.ver*` e tutta `MY_HIGH_SCHOOL_M25_TEST_DATA/`, inclusi:

- `Registro_slot_*.json`: studenti e classi.
- `Ultima_modifica_slot_*.json`: metadati delle modifiche.
- `Impostazioni_slot_*.json`: attivazione e classi.
- `Personale_slot_*.json`: incarichi del personale.
- `MHS97_RuoliSpeciali_slot_*.json`: ruoli speciali.
- Ogni altro file o JSON, anche se diagnostico o con nome sconosciuto.

Non azzerare il registro per aggiornare la mod. Usare una copia del salvataggio per il primo collaudo.

## Inventario preciso della propria cartella Mods

Il repository e l'ambiente cloud non hanno accesso ai file realmente installati sul Mac. Per stabilire **quali nomi e percorsi esatti** siano presenti, eseguire dal checkout del progetto, con Python 3.7 o successivo:

```sh
python3 -m tooling.mod_inventory \
  "$HOME/Documents/Electronic Arts/The Sims 4/Mods" \
  --output "$HOME/Desktop/MHS-inventario.json"
```

Se il gioco usa una cartella diversa, indicare il percorso effettivo. L'opzione `--data-dir` consente di specificare la cartella dati; normalmente è quella accanto a Mods. Il report di destinazione deve essere nuovo e fuori da Mods, saves e dati persistenti. Senza `--output`, lo scanner stampa il JSON sul terminale.

Nel pacchetto scaricabile lo scanner è anche fornito come `mod_inventory.py`:
si può usare `python3 /percorso/mod_inventory.py` al posto di
`python3 -m tooling.mod_inventory`, con gli stessi argomenti. Non serve clonare
il repository per eseguire questo file.

Lo scanner legge soltanto: non cancella, sposta, estrae o esegue alcuna mod; non legge i valori dei JSON. Elenca percorsi, dimensioni, SHA-256 e moduli presenti negli archivi `.ts4script`/`.zip`; segnala gli stessi moduli distribuiti da più archivi. Non segue link simbolici. Un percorso non leggibile o saltato produce `complete=false`, così l'inventario incompleto non viene presentato come esaustivo.

Per confrontare anche i nuovi file con il manifest di compilazione:

```sh
python3 -m tooling.mod_inventory \
  "$HOME/Documents/Electronic Arts/The Sims 4/Mods" \
  --manifest /percorso/CLASSROOM_CONTROL_BUILD_REPORT.json \
  --output "$HOME/Desktop/MHS-inventario-dopo.json"
```

Il manifest supportato contiene `files` (oppure `artifacts`) con `name` e `sha256` per ciascun file, ad esempio:

```json
{"files": [{"name": "MHS_CLASSROOM_CONTROL.package", "sha256": "<SHA-256 completo della build>"}]}
```

Il manifest reale contiene gli hash della build, non il segnaposto di questo esempio. I moduli attesi possono comparire in `modules` nell'elemento dello script. Un nome `MHS...package` da solo **non prova** che un file appartenga al progetto; il controllo hash è necessario per riconoscere con certezza un artefatto della nuova release.

## Una sola versione installata

Dopo il backup, usare il report per preparare una cartella di quarantena **fuori da Mods**, conservando i percorsi originali. Lo scanner non esegue questa operazione.

- Gli archivi identificati dai moduli MHS storici sono candidati da verificare e spostare nella quarantena: M54/menu precedente, convocazioni M55–M104, controller M105–M148 e diagnostiche/piloti precedenti. Non lasciare un controller storico accanto a quello unificato.
- Per i `.package` vecchi, usare l'hash noto dell'artefatto originale o una provenienza verificabile. Un file sconosciuto resta da identificare; non eliminarlo soltanto per il nome.
- Non spostare mod di terzi per una corrispondenza generica con “scuola” o “Sonozaki”. **Conservare Zerbu Go to School e Sonozaki Elementary**: la loro compatibilità va valutata separatamente e non richiede una rimozione indiscriminata.
- Conservare tutti i dati e salvataggi elencati sopra. Spostare un vecchio `.ts4script` o `.package` non richiede spostare il registro.

Nell'inventario ricevuto è identificato un solo archivio MHS:
`MY HIGH SCHOOL MOD/MHS_M148.ts4script`. È il file preciso da spostare fuori
da Mods. La cartella contiene anche `.DS_Store`, metadato Finder innocuo.
Nessun vecchio package MHS è identificabile dai nomi del report: non spostare
package sconosciuti presumendo che siano una versione M54.

Installare la sola nuova coppia direttamente in Mods o in una sola sottocartella, ad esempio `Mods/MY_HIGH_SCHOOL/`. Non tenere copie duplicate in altre cartelle. Ricontrollare l'inventario: nessun modulo MHS deve essere fornito da due archivi e i due SHA-256 devono corrispondere al manifest della stessa build.

**XML Injector è una dipendenza del menu:** conservare la versione compatibile
già utilizzata con M54/M148. Non è incluso nel nuovo archivio. Il manifest
elenca sia i moduli MHS inclusi sia questa dipendenza esterna.

## Verifica nel gioco

Abilitare contenuti personalizzati/mod e mod script, riavviare il gioco e aprire la copia del salvataggio. Verificare registro e personale esistenti prima di cambiarli. Controllare entrambe le classi da otto, i giocabili realmente iscritti e i ruoli speciali configurati; quindi il flusso della revisione installata.

I test automatici e il manifest verificano struttura, dipendenze e identità dei file. La presenza di otto studenti al banco corretto alle 10 e alle 14, il completamento naturale, pranzo, punizioni, esami ed eventi richiedono osservazioni nel gioco. Conservare il report della giornata e distinguere un invito accettato da un Sim realmente presente e impegnato nella lezione.

## Attivazione della gestione unificata

Da casa, usare il menu MY HIGH SCHOOL per completare Classe 1 e Classe 2 con
otto iscritti ciascuna e `Ruoli speciali` per confermare i cinque NPC scelti.
Il personale già scelto resta nel suo registro separato.

Dopo la configurazione iniziale, usare `Disattiva MY HIGH SCHOOL` e poi
`Attiva MY HIGH SCHOOL` una volta da casa. Non si cancellano iscrizioni o ruoli.
Le sessioni successive si preparano dal caricamento del lotto e dai nuovi
eventi EA; non sono richiesti comandi console quotidiani. Il caricamento
diretto di una giornata scolastica già iniziata viene bloccato anziché
ricostruire arbitrariamente gli inviti.

La revisione conserva due aule originali EA; non abilita frequenza di una
terza aula. Se il registro precedente contiene Classe 3, trasferire prima gli
iscritti usando il menu: non cancellare o modificare manualmente il JSON.
