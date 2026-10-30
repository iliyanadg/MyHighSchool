# Passo 22 — Registro M2: primo nucleo di iscrizioni verificabile

**Stato: sorgenti e test Python, non ancora collegati alla UI M1. Non
installare nulla.**

## Risultati provati nel gioco nel precedente prototipo M1
L'utente ha verificato il 30 ottobre 2026 che sul Mac la categoria
`MY HIGH SCHOOL (PROVA)` si apre dalla cassetta postale, i due
`SimPicker` mostrano ritratti, accettano fino a 8 scelte e producono
notifiche italiane per entrambe le classi. Non persistono nulla.

## Cosa abbiamo aggiunto adesso
- `src/m2_registry/mhs_m2_roster.py`: core indipendente, classi 1 e 2,
  8 posti rigidi ciascuna, batch da 1 a 8 Sim ID, solo selezione manuale.
  **Le selezioni si AGGIUNGONO** agli iscritti correnti; uno studente già
  iscritto alla stessa classe resta tale; uno spostato da Classe 1 a 2
  viene tolto dalla classe precedente. Nessun duplicato e nessuna
  iscrizione automatica.
- Verifica **esplicita che ciascun ID appartenga a un adolescente idoneo**,
  compresi gli ID già iscritti: non basta apparire nel picker.
- Verifica **atomica**: se un solo Sim non è adolescente, un ID è ripetuto
  o si supera la capienza 8, la classe non cambia per nessuno.
- `src/m2_registry/mhs_m2_store.py`: file JSON in una cartella di
  prototipo SEPARATA dalla v1.6, distinto per save-slot ID del gioco,
  creato solo dopo la prima iscrizione. Scrittura atomica con file
  temporaneo e `os.replace`. Un file corrotto o appartenente ad
  altro slot non viene sovrascritto.
- `src/m2_registry/mhs_m2_game_bridge.py`: funzioni di collegamento
  per una futura callback del picker, controllo del `SimInfo` reale e
  slot da `services.get_persistence_service()`. **Non** è eseguito
  automaticamente e **non** è ancora incluso in un ts4script.
- `tests/test_m2_registry.py`: test Python che simulano più salvataggi,
  adulti, duplicati, capienza piena, trasferimenti, riapertura dei dati,
  corruzione e un ritorno dalla callback.

## Limitazioni importanti, da risolvere PRIMA di una promessa utente

1. **La M1 è ancora UI di prova**: i ConfirmClass1/2 XML non richiamano
   il bridge M2. Cliccando ✓ M1 continua a mostrare solo la notifica,
   non registra Sim.
2. Il JSON di prova è **esterno al file .save**: rimane fra sessioni
   dello stesso slot, ma non segue automaticamente `Salva con nome`,
   ripristini di salvataggi precedenti o slot riutilizzati. Quando
   arriva una nuova partita senza slot definitivo, il registro si
   rifiuta di scrivere. Questo rischio deve essere risolto o comunicato
   chiaramente prima del test di persistenza.
3. La gestione della Classe 3 (facoltativa), del PC, del filtro dei
   candidati non assegnati, del cambio differito al giorno scolastico
   successivo e delle lezioni fisiche **non è ancora implementata**.
4. Non combinare questi sorgenti con la .ts4script v1.6: nomi dei
   moduli M2 sono separati per evitare collisioni.

## Prossimo passo
Studiare e verificare il comportamento dei partecipanti
`PickedSim` nella **continuation** di `SimPickerInteraction`,
quindi costruire una piccola interazione Python di conferma che
riceva **tutti** i Sim scelti e richiami `receive_selected_ids`
senza effetti collaterali se il gioco non passa i partecipanti.
Solo dopo una prova su salvataggio di test potremo dire che
l'iscrizione si salva davvero.
