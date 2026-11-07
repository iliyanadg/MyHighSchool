# M155–M159 — Continuità del salvataggio, 2 classi

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
