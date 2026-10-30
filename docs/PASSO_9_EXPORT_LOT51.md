# Passo 9 — File autentici esportati da Lot51 Tuning Builder

L'utente ha esportato due file da Lot51 (TDESC mostrato: **1.128.90**, The Sims 4 sul Mac: **1.129.39.1230**).

- Tuning XML: `03E9D964!00000000!CA28A52FAEFBD0C3.Iliyana_MHS_MainMenu.xml`
- SimData in **rappresentazione XML**, non ancora in formato binario: `545AC67A!00E9D967!CA28A52FAEFBD0C3.Iliyana_MHS_MainMenu.SimData.xml`
- Nome interno: `Iliyana:MHS_MainMenu`
- Identificativo condiviso: **14567074618947653827** (`0xCA28A52FAEFBD0C3`)
- Chiave di testo STBL: `0x3FCE8D06`.

## Risultato verificato
L'XML della categoria e lo schema XML della SimData corrispondono per nome, ID di risorsa presente nel nome del file e chiave testo. I test `tests/test_lot51_exports.py` ne controllano la coerenza.

## Attenzione prima di installare
La `.SimData.xml` **non è il file binario SimData**: non basta rinominarlo. Il generatore Lot51 può esportare anche un **package direttamente** (File > Download Package), oppure un editor di package adatto può convertire la rappresentazione XML nel tipo binario corrispondente. Quella build dovrà comunque superare il nostro gate statico. Non caricare questi XML nella cartella Mods.

Le due interazioni `ChooseClass1.xml` e `ChooseClass2.xml` in `m1_unbuilt` sono solo una copia di lavoro con il riferimento alla nuova categoria sostituito. **Non sono tuning validati dalla versione EA 1.129**, non garantiscono avvio e non rappresentano la mod funzionante.

## Passo successivo
Ottenere il **package di esportazione della sola categoria** direttamente da Lot51 e verificarlo staticamente, senza installarlo. In un secondo momento verificare le interazioni, le stringhe STBL e l'injector prima di preparare il menu nel gioco.
