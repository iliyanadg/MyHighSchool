# Passo 11 — Menu -> Classe 1/2 -> conferma; testi IT/EN

**Stato: SOURCES ONLY — nessun nuovo file installabile.**

La categoria esportata da Lot51 `Iliyana:MHS_MainMenu` ha instance
`14567074618947653827`. Entrambi i `ChooseClass1/2.xml` in
`src/experiments/m1_unbuilt` la referenziano nella voce `category`.

Le due voci puntano alle rispettive `ConfirmClass1/2.xml` e i riferimenti
a **nove testi** sono ora definiti in `localization.json` sia in italiano
che in inglese. Le chiavi testuali sono conservate dal vecchio M0 ma le
traduzioni sono state rilette e corrette. `tooling/m1_links_and_strings.py`
verifica coerenza degli ID e genera STBL v5 **in memoria** per controllarne
la decodifica, senza pubblicare una build.

Questa analisi prova soltanto i **link fra le risorse sorgente**. Non prova
che il picker mostri tutti i teen né che il metodo `actor_continuation`
passi correttamente i risultati all'interazione di conferma.

## Cosa resta prima di qualsiasi prova nel gioco
1. Validare `SimPickerInteraction` e notifiche con i TDESC adatti alla
   versione 1.129; non basta che XML sia ben formato.
2. Verificare il meccanismo per aggiungere le interazioni sulla cassetta
   postale (lo snippet XML Injector M0 non è ancora considerato affidabile).
3. Integrare categoria e SimData binaria **esportate da Lot51**, STBL in
   italiano e fallback inglese, pickers e conferme in un unico package.
4. Passare tutti i controlli statici *e poi* testare avvio sul Mac su un
   salvataggio di prova, senza toccare la v1.6.

Il menu in questa fase è soltanto una **prova d'interfaccia**. Le notifiche
non equivalgono a iscrizioni salvate né a studenti smistati in aula.
