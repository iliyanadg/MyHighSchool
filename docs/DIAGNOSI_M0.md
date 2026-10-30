# Diagnosi preliminare del package M0 — NON INSTALLARE

**Sintomo verificato dall'utente:** The Sims 4 su Mac 1.129.39.1230 non si avvia con il package `MHS_M0_MENU_NATIVO_SOLO_TEST.package` in Mods; si avvia dopo aver rimosso esclusivamente questo file.

## Verifiche offline sui file forniti
- Il package M0 contiene 8 voci DBPF: 4 interazioni, 1 categoria menu, 1 snippet XML Injector e 2 tabelle STBL.
- L'intestazione DBPF, il puntatore d'indice, la decompressione e l'intestazione STBL hanno struttura paragonabile al package Sonozaki fornito. **Questo non prova che la mod venga caricata dal gioco.**
- **Risorsa mancante verificabile:** la categoria `PieMenuCategory` di M0 (tipo `0x03E9D964`) non ha una risorsa `SimData` (tipo `0x545AC67A`) abbinata allo stesso instance ID. In Sonozaki, tutte le 14 categorie hanno una SimData abbinata.
- I picker M0 sono `SimPickerInteraction` con riferimento alla categoria, e lo snippet è di XML Injector (non Lot51 Core).

## Conclusione
La SimData mancante è una differenza importante, **non la causa dimostrata** del mancato avvio. Altre possibilità da isolare: tuning non conforme, snippet d'iniezione, dipendenze, risorse costruite manualmente. Nessuna nuova build viene considerata pronta finché non viene validata con un tool adatto e con un test di avvio separato.

## Regola pratica
Non installare più il M0 e non ricompilare automaticamente i suoi XML. Mantenere la v1.6 funzionante. Il prossimo intervento riguarda l'analisi e la generazione corretta delle risorse, non l'assegnazione degli studenti.
