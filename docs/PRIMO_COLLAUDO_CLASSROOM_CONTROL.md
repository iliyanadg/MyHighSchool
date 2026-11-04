# Primo collaudo della correzione lavagna

Questa build unifica il menu e il registro esistenti con il filtro di aula
basato sulle API EA ricevute. È pronta per il **primo collaudo su copia del
salvataggio** dopo i controlli offline; non è ancora certificata come stabile.
È richiesta Vita da Liceali. Conservare XML Injector compatibile.

## Installazione di una sola versione

1. Chiudere il gioco. Fare una copia di `saves/` e di tutta
   `MY_HIGH_SCHOOL_M25_TEST_DATA/` fuori dalla cartella del gioco.
2. Spostare fuori da Mods i vecchi archivi MHS identificati nell'inventario,
   conservandoli come backup. Non spostare i JSON della cartella dati.
   Nell'inventario analizzato l'unico script MHS è
   `MY HIGH SCHOOL MOD/MHS_M148.ts4script`; non risultano altre versioni MHS
   né la coppia M54 con un nome riconoscibile.
3. Installare soltanto `MHS_CLASSROOM_CONTROL.package` e
   `MHS_CLASSROOM_CONTROL.ts4script` della **stessa nuova build** in
   `Mods/MY_HIGH_SCHOOL/`. Non installare lo ZIP intero, lo scanner o i file EA.
   Conservare Zerbu Go to School, Sonozaki Elementary e XML Injector.
4. Abilitare mod e mod script; aprire la copia del salvataggio da casa.
   Verificare nel menu che registro, classi, ruoli e personale siano quelli
   già salvati. Non azzerarli e non creare nuovi studenti per fare la prova.
5. Con due classi da otto e cinque ruoli speciali manuali, usare una volta
   `Disattiva MY HIGH SCHOOL` e `Attiva MY HIGH SCHOOL` da casa. La preparazione
   delle giornate successive è automatica. Se compare un blocco, conservarne
   il messaggio: non forzare l'attivazione tramite vecchi controller.

## Una giornata completa, senza interventi sulle lezioni

Seguire il normale ingresso EA al liceo. Non usare teletrasporto, comandi
di recupero, cambio ora, `arm` ripetuto o ordini manuali di andare in classe.

- Prima delle 10: osservare se gli NPC di Classe 2 vanno verso la propria
  lavagna e non prima a quella di Classe 1.
- Alle 10 e alle 14: annotare quanti sono fisicamente seduti in ciascuna aula;
  distinguere un Sim in piedi che sta già eseguendo la materia da uno senza
  interazione. Se mancano posti, annotare l'ora del loro arrivo, senza forzarli.
- Lasciare proseguire pranzo, eventuali punizioni e lezioni fino alla fine
  originale EA. Verificare che gli obiettivi si riconoscano e terminino
  normalmente; la mod non li segna come completati.
- Dopo la fine della giornata, aprire la console ed eseguire solo
  `mhs148.report`: è l'alias mantenuto per esportare la nuova diagnostica,
  non richiede di reinstallare M148. Il file da inviare è
  `MY_HIGH_SCHOOL_M25_TEST_DATA/MHS_CLASSROOM_CONTROL_REPORT_COMPLETO.json`.

I file `MHS_M148_*` precedenti restano conservati. Il nuovo report comprende
controlli della lavagna, target rifiutati, job dei 16 studenti, tratti e code.

## Seconda giornata e verifiche successive

Nella seconda giornata scolastica lasciare gli stessi iscritti e non riarmare
da console: verificare che la classe conservi gli stessi otto studenti.
Un cambio di iscritti deve essere preparato da casa per il giorno successivo,
non applicato forzando le situazioni già in corso.

Prima di considerarla stabile restano anche le verifiche di scuola elementare
con Zerbu/Sonozaki, sostituzioni e trasferimenti, eventi/esami e salvataggi
diversi. Le altre mod non vanno rimosse indiscriminatamente sulla sola base
di una collisione di nome modulo.
