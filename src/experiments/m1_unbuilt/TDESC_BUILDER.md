# Categoria MY HIGH SCHOOL — sorgente per Tdesc Builder, NON installabile

Abbiamo conservato la chiave categoria **7064630105397426819** e la stringa esistente **0x3FCE8D06** (MY HIGH SCHOOL (PROVA)), perché i due selettori nel vecchio progetto fanno riferimento a quegli identificativi.

- `Category_for_Tdesc.xml` è **solo tuning XML sorgente**. Non è una SimData, non è un package e non si può copiare in Mods.
- Va aperto in **Lot51 Tdesc Builder** (strumento esterno: https://tdesc.lot51.cc/) tramite **Open Tuning or Package** o trascinamento di XML.
- Va esportato **insieme alla SimData generata dal builder**; la categoria e la SimData devono condividere lo **stesso ID Instance** indicato sopra.
- Il bundle esportato va analizzato con `tooling/simdata_release_gate.py`. Attenzione: anche un esito positivo è solo verifica strutturale, non prova d'avvio.
- Alla data della ricerca, il builder pubblico mostrava dati TDESC 1.128.90 mentre il gioco locale è 1.129.39.1230. Verificare lo schema effettivo e non presumere compatibilità completa.
- Il vecchio M0 non va installato, e `Category_for_Tdesc.xml` non deve essere aggiunto direttamente a Mods.

**Il prossimo compito effettivo:** ottenere l'esportazione dal generatore affidabile, non fabbricare un altro package DBPF a mano.
