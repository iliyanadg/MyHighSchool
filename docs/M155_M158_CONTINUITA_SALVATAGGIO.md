# M155–M163 — Continuità del salvataggio, 2 classi

Questa revisione parte dal controller M154 e **non modifica** inviti EA, lezioni,
lavagne, organico scolastico o capienza (due classi di otto).

## Correzioni

1. Il ritorno a casa può mantenere l'ID del salvataggio già verificato
   anche quando EA espone temporaneamente un ID scratch. Una modifica del
   registro è consentita soltanto se lo stesso controller è già attivo,
   fuori dal liceo, e il GUID EA continua a corrispondere alla sessione
   verificata. Il primo avvio su ID scratch sconosciuto resta bloccato.
2. Il cambio di famiglia all'interno della stessa partita non invalida
   da solo l'identità, purché il controller a casa sia ancora verificato
   e il GUID EA non cambi. Il caricamento di un altro salvataggio rimane
   isolato.
3. Un nuovo slot ottenuto tramite «Salva con nome» può importare
   automaticamente le quattro configurazioni esterne (studenti, impostazioni,
   personale, ruoli Core) **solo** dopo la verifica di un numero slot EA
   reale, fuori scuola, con destinazione non ancora configurata e Sim
   corrispondenti al gioco attuale.
4. Più salvataggi sorgente possono essere considerati equivalenti soltanto
   se i quattro registri, ricostruiti per la stessa destinazione, sono
   identici. In caso di configurazioni diverse, nessuna sorgente viene
   scelta automaticamente e i file non vengono sovrascritti.
5. Se il nuovo slot viene caricato nella stessa sessione in cui il controller
   conosce ancora lo slot precedente, quest'ultimo è usato come sorgente
   preferita, dopo tutte le convalide; non viene scelta una partita qualsiasi.
6. Se il recupero opzionale fallisce, la mod conserva i dati preesistenti
   senza impedire il caricamento del gioco.

## Ulteriori correzioni M160–M163

- **M160:** una coppia GUID EA / slot numerico realmente osservato viene
  memorizzata nel file separato `MHS_VerifiedSaveIdentity.json`.
  Al nuovo avvio, se EA espone uno slot temporaneo, l'identità viene
  recuperata soltanto se esiste una corrispondenza univoca di GUID,
  famiglia e Sim del registro correntemente presenti nel salvataggio.
  La collisione tra più slot con lo stesso GUID e nucleo resta bloccata.
- **M161:** il monitor di arrivo scuola, già presente e leggero, riconosce
  anche il cambio di slot quando «Salva con nome» viene fatto restando a
  casa e richiede il ricaricamento sicuro del controller.
- **M162:** la verifica dell'identità non richiede più che la classe sia
  piena o la mod attiva; anche un registro temporaneamente incompleto
  (almeno un iscritto) può essere riconosciuto dopo una chiusura.
  **La frequenza scolastica mantiene invece i requisiti 8+8 e cinque ruoli.**
- **M163:** gli aggiornamenti dei registri studenti, impostazioni e ruoli
  speciali ri-verificano da casa l'attivazione del controller appena
  sono stati salvati, senza dover cambiare lotto per riarmarlo.
- Test in `tests/test_m160_restart_identity.py` e
  `tests/test_m163_home_auto_rearm.py`.

Il file identità è locale al Mac; non va modificato a mano. Conservare
sempre insieme `saves` e `MY_HIGH_SCHOOL_M25_TEST_DATA`. Il solo backup dei
file EA `.save` **non** comprende i registri esterni né i nuovi binding.

## M165 — Recupero automatico dei salvataggi preesistenti

La M164 non poteva recuperare un salvataggio più vecchio se non esisteva
ancora `MHS_VerifiedSaveIdentity.json`: al primo riavvio con ID EA temporaneo
mostrava `M142 NON ATTIVA: BridgeError ... modifiche bloccate`.
La M165 introduce l'inizializzazione automatica **soltanto da casa**:

- Richiede GUID EA valido, famiglia attiva e un adolescente giocabile
  iscritto nel registro sorgente.
- Verifica che nel salvataggio esistano tutti i 16 Sim registrati e gli
  incarichi/personale richiesti dal formato precedente.
- Quando c'è un'unica configurazione compatibile (o più configurazioni
  perfettamente identiche), copia in modo atomico i quattro registri in
  un nuovo spazio dati derivato deterministicamente dal GUID EA.
- Conserva i registri originali, senza sovrascriverli, e registra il
  nuovo riferimento per i riavvii successivi.
- Se le configurazioni divergono, l'ID manca o la copia non è sicura,
  non seleziona un registro a caso. La notifica ora include una diagnosi
  leggibile invece di dire genericamente che le regole EA non sono supportate.

**Cautela su Salva con nome:** i Save ID EA possono essere condivisi tra
copie dello stesso salvataggio. Se il numero di slot non è visibile,
il GUID da solo non distingue necessariamente due copie. La separazione
totale resta subordinata alla verifica dello slot reale; non dichiarare
questa situazione già certificata.

Test aggiunti in `tests/test_save_as_copy.py` con primo avvio
automatico da registro legacy e rifiuto di sorgenti divergenti.

## Limiti da non nascondere

- Un avvio **diretto al liceo**, a giornata EA già avviata e senza
  controller in memoria, non può ricostruire retroattivamente gli inviti
  scolastici. È necessario verificare il caricamento prima della scuola.
- Se EA restituisce soltanto un ID scratch già al primo caricamento di una
  nuova sessione, non esiste ancora un'ancora di slot verificata: la mod
  deve rifiutare le scritture invece di attribuire dati alla partita sbagliata.
- Con più sorgenti differenti la copia automatica è deliberatamente bloccata.
  La scelta manuale della sorgente resta disponibile.
- **La prova offline non equivale a un collaudo in The Sims 4.** Servono
  prova su Mac con Salva, chiusura totale, riapertura, due giorni scolastici,
  modifiche di iscrizione da casa, Salva con nome e cambio di famiglia.
- Non sostituire la build di gioco stabile prima che la pipeline di build
  passi e che il nuovo pacchetto sia collaudato su una copia del salvataggio.

## Test aggiunti

- `tests/test_m155_verified_home_writes.py`
- `tests/test_save_as_copy.py` (recupero automatico, origine
  equivalente, origini divergenti)
- Esecuzione M155 inclusa in `.github/workflows/classroom-control.yml`.

## Situazione del CI del 7 novembre 2026

Le esecuzioni GitHub Actions del ramo hanno segnalato *failure* ma i job
consultati non esponevano step né log leggibili (endpoint del log 404
BlobNotFound). Perciò questa revisione **non è certificata né pronta
all'installazione** fino a esecuzione dei test verificabile.
