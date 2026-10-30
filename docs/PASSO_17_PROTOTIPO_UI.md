# Passo 17 — Prototipo M1 di sola interfaccia (NON TESTATO NEL GIOCO)

Il 30 ottobre 2026 è stato costruito e verificato **offline** il package
`MHS_M1_MENU_SOLO_TEST.package`. È stato consegnato all'utente in un archivio
ZIP separato, `MHS_M1_SOLO_TEST_CON_ISTRUZIONI.zip`, contenente package,
`LEGGIMI_PRIMA.txt` e `MANIFEST.json`.

## Identità dell'esemplare testato localmente

- Dimensione del package: **3457 byte**
- SHA-256: `a3bb443e3fa24e85365be74074e7ef46bfb5b61f14535516e346209d58bacdc3`
- Base Lot51 originale (categoria e SimData binaria):
  SHA-256 `ab2ecb3c51485d27f12dfbe5844df5e610e486abe88dce2395f1872872b53c3c`
- PieMenuCategory: `Iliyana:MHS_MainMenu`,
  instance `0xCA28A52FAEFBD0C3`.

## Controlli offline eseguiti (NON un game test)

1. DBPF v2.1; **index minor = 3**; header, index e 9 risorse decodificate
   da un secondo parser indipendente dall'assemblatore.
2. Payload Lot51 originali preservati; corrispondenza dell'ID della
   categoria alla SimData con magic `DATA`.
3. Due SimPickerInteraction, due conferme, snippet XML Injector.
4. Due STBL v5 (IT 0x0B, EN 0x00), nove voci ciascuna; lunghezza dichiarata
   con un byte NUL concettuale per voce; tutte le chiavi referenziate.
5. Archivio ZIP letto nuovamente per confermare che il file incluso sia
   identico al package generato.

Risorse: **1 PieMenuCategory + 1 SimData + 4 Interaction + 1 Snippet +
2 STBL = 9**. Il file M1 non include gli script della v1.6, né l'antico
M0 danneggiato; le due classi sono soltanto una prova d'interfaccia.
Non persiste iscrizioni.

## Limiti e prerequisiti prima della prova

**Questo package non è stato avviato in The Sims 4**: i nove controlli
statici non garantiscono l'apertura del menu o la stabilità del gioco.

- Fare backup dei salvataggi e usare un **salvataggio di prova**.
- Lasciare inalterata la mod funzionante `v1.6`; prima di testare M1
  rimuovere tutte le vecchie build sperimentali UI/M0.
- Serve **XML Injector v4.2 (o versione compatibile)** installato.
- Per testare su Mac, inserire *solo* il package M1 nella cartella
  `Documents/Electronic Arts/The Sims 4/Mods`, con gioco chiuso.
- Osservare prima l'**avvio**, poi un clic su cassetta postale standard.
  Menu previsto: `MY HIGH SCHOOL (PROVA)`, voci `Classe 1/2`.
- In caso di errore, chiudere il gioco, togliere il solo file M1 e
  riprovare; non toccare salvataggi e non rimuovere v1.6.

## Rapporto con la build del repository

`tooling/build_m1_offline.py` può ricostruire un package con **le stesse
risorse e riferimenti** dal sorgente M1. La serializzazione testuale XML
può cambiare byte, quindi non presumere che un output prodotto da un'altra
macchina abbia lo stesso SHA-256 dell'esemplare allegato alla chat.

**Passo seguente:** prova graduale sul Mac, verificando prima che la
dipendenza XML Injector sia presente e che le vecchie build siano fuori
dalla cartella Mods; una sola modifica per volta. Non promettere che
il menu funzionerà prima di verificarlo sul gioco reale.
