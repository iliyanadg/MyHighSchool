# Passo 31 — M29 cumulativa: registro fotografico, audit e annullamento

**Stato:** sorgenti e compilazione CI; tutto cio che usa API EA resta da verificare realmente in The Sims 4 su Mac. Non installare durante lo sviluppo, evita test singoli.

## Nuove funzioni aggiunte sopra M28

- **Consulta iscritti Classe 1, 2, 3**: tre opzioni nella cassetta postale. Aprono un elenco fotografico filtrato agli iscritti effettivi presenti nel SimInfoManager. Solo lettura; la spunta non esegue alcun salvataggio.
- **Cerca studente**: `mhs29.find Nome` (parola chiave o ID). Visualizza la classe e l'ID degli iscritti che corrispondono. Non cerca nei Sim non iscritti.
- **Controllo del registro**: `mhs29.audit` elenca i totali delle 3 classi e segnala eventuali iscritti non trovati o che non sono piu adolescenti. Nessuna rimozione automatica.
- **Pulizia sicura**: `mhs29.cleanpreview` mostra gli iscritti non idonei e prepara una lista. La vera modifica al registro avviene soltanto con `mhs29.cleancommit conferma`. Se la lista, lo slot o il registro cambiano, blocca. `mhs29.cleancancel` annulla.
- **Annulla ultima modifica al JSON TEST**: `mhs29.undo conferma`. Tutte le scritture nel registro attraverso `RosterStore.save` ora conservano la versione precedente per ogni slot. L'annullamento e consentito solo se la versione corrente corrisponde all'impronta salvata. Dopo l'annullamento la cronologia non puo essere riutilizzata per eseguire un secondo undo.
- **Diagnostica**: `mhs29.report` mostra i problemi di apertura dei tre nuovi picker.

## Tutto cio che resta da M28

- Tre classi max 8 posti ognuna, iscrizione manuale, rimozione manuale, scambio atomico di due iscritti con comandi.
- Il comando `mhs28.roster` visualizza il registro con nomi, ID e posti liberi.
- Il bug M27 della tupla `icon_resource` e corretto nei sorgenti ma non ancora verificato dal gioco.
- Non installare coppie M25/M27/M28 contemporaneamente alla coppia M29.

## Limitazioni e sicurezza

- I registri sono sempre **JSON esterni** per salvataggio di prova, non integrati con i file `.save` EA. Annullare una modifica al JSON non ripristina altre azioni compiute nel gioco.
- Prima di provare una modifica scrivente, copiare la cartella `MY_HIGH_SCHOOL_M25_TEST_DATA` al sicuro.
- Il meccanismo di rollback ha una sola posizione di cronologia, **non** e un archivio illimitato delle modifiche.
- La consultazione fotografica dipende dalla compatibilita dell'interfaccia EA attuale; se non compare, usare `mhs29.report`. Nessun salvataggio eseguito dall'apertura.
- La pulizia non e automatica; l'utente controlla e conferma. I Sim rimangono esistenti.
- Lezioni, docenti, assegnazione di lavagne, presenza fisica nelle aule e prom non sono ancora operativi.

## Unico giro di test Mac previsto

1. Solo quando la build M29 e verificata offline: chiudere The Sims 4 senza salvare la partita di prova corrente. Rimuovere SOLO coppia M27 o M28 attuale e mettere SOLO la coppia M29 nella Mods; v1.6 e XML Injector invariati.
2. Avviare il salvataggio di prova. Eseguire `mhs28.roster`, `mhs29.audit`, `mhs29.find Nome` senza scrivere dati.
3. Cassetta postale → **Consulta iscritti Classe 1/2/3**. Verificare i ritratti e che non compaiano studenti di altre classi.
4. Cassetta postale → **Rimuovi studenti Classe 1**. Se il picker appare, usare solo la selezione e `mhs27.removepreview`, senza eseguire `removecommit`.
5. Provare **Prepara iscrizione Classe 3** e `mhs25.preview`, senza eseguire `commit`.
6. `mhs29.audit`: nessuna rimozione automatica; se un popup non compare, `mhs29.report` / `mhs27.report`.
7. Il test di `mhs29.undo` richiede uno slot dedicato, una copia del registro e una modifica deliberata gia verificata. Evitare sulla famiglia principale.

Dopo questo test e la correzione di eventuali problemi UI, si puo iniziare il controllo delle classi **fisiche** con lavagne e insegnanti; 24 Sim effettivamente presenti vanno validati per prestazioni e conflitti con le situazioni EA.
