# Passo 15 — Assemblaggio M1 completo in memoria; NON installare

Abbiamo aggiunto `tooling/build_m1_offline.py` e `tests/test_m1_offline_package.py`.

L'assemblatore parte dal **package autentico esportato dall'utente
tramite Lot51**, ne verifica lo SHA-256 e conserva i due payload di tuning
e SimData binaria. Aggiunge i nostri cinque XML (2 picker, 2 conferme e
1 snippet XML Injector), più due STBL originali IT/EN di nove stringhe.

## Inventario atteso: 9 risorse
- 1 PieMenuCategory (`0x03E9D964`)
- 1 SimData (`0x545AC67A`)
- 4 Interaction Tuning (`0xE882D22F`)
- 1 XML Injector Snippet (`0x7DF2169C`)
- 2 STBL (`0x220557DA`)

Lo script riproduce il layout DBPF dell'export Lot51, applica la
compressione zlib, costruisce l'indice e verifica che **tutti i payload
siano identici dopo una lettura del risultato**. Verifica inoltre
l'unicità degli ID e l'abbinamento categoria–SimData.

Per eseguire solo la verifica: `python -m tooling.build_m1_offline`.
Non salva automaticamente un file `.package`; l'assemblaggio avviene
in memoria durante il test GitHub Actions. Nessuna modifica alla
v1.6 installata o ai salvataggi.

## Cosa NON è stato dimostrato
**QUESTA NON È UNA MOD PRONTA.** Il superamento dei test DBPF non
equivale a un avvio riuscito di The Sims 4; i precedenti prototipi
passavano alcuni controlli statici e bloccavano il gioco.
È necessario verificare anche:
- conformità degli XML agli schemi EA 1.129;
- esecuzione reale dello snippet XML Injector;
- disponibilità dei candidati adolescenti e comportamento dei picker;
- avvio del gioco in un test separato e isolato.

Non pubblicare né installare questa build come prodotto finito.
