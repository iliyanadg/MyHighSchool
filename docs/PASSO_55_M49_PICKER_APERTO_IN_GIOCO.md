# Passo 55 — M49 il picker di iscrizione si apre nel gioco Mac (31 ottobre 2026, ore 15:28)

## Riscontro diretto dell'utente

Dopo l'errore M48 `'ImmutableSlots' object has no attribute 'get_max_selectable'`, la M49 con la strategia EA per `max_selectable` è stata installata. La creatrice ha fornito screenshot della finestra **«ISCRIVI STUDENTI - CLASSE 1»** aperta nel gioco The Sims 4 su Mac e in pausa.

Sono visibili:
- Titolo, testo «Seleziona fino a 8 adolescenti. Classe 1 attualmente: 2/8 iscritti. Premi la spunta per iscriverli, X per uscire»;
- elenco Sim con miniature e nomi (Sandro Paoletti, Sofia Ogliari, Rosario Lanzafame, Amarachi Darong, Ash Harjo, Aurelio Robles, Baby Ariel, Dante Montreschi, Darling Walsh);
- Amarachi Darong evidenziata con contorno verde;
- X per chiudere e spunta in basso a destra.
- Nessun nuovo errore `get_max_selectable` visibile.

Questo **conferma soltanto l'apertura del SimPicker M49 nel gioco**, e la lettura visiva del conteggio 2/8 dal JSON; NON conferma ancora la persistenza né l'esecuzione del callback della spunta, la cancellazione con X, il limite massimo UI, o l'aggiornamento in pausa.

## Test end-to-end concordati, senza nuove build

1. Prima prova X: con Amarachi selezionata, chiudere con X. Aprire `Classe 1 → Consulta iscritti`. Devono restare Amarachi Darong e Baby Ariel, senza nuove iscrizioni.
2. Su save TEST e con backup del registro JSON esterno, riaprire `Classe 1 → Prepara iscrizione`; selezionare UN solo adolescente non iscritto, per esempio Rosario Lanzafame; premere spunta. Attesa: notifica di riuscita, quindi `Consulta iscritti` deve mostrare 3/8 e i nomi Amarachi, Baby e Rosario.
3. Una volta convalidato il commit: su save TEST, verificare la persistenza dopo chiusura/riavvio e la capacità effettiva fino a 8; non sovraccaricare la prima sessione.
4. Verificare che la modifica avvenga anche in pausa (screen attuale è in pausa). Se la X o ✓ non completa il callback, riportare screenshot o notifica esatta e non eseguire iscrizioni multiple.

Il menu M45 e le sue SimData Lot51 restano inalterati. Non modificare il salvataggio principale. Le iscrizioni M49 sono soltanto nel JSON di prova e **non** pilotano ancora la frequenza EA al liceo.
