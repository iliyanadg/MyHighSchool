# Passo 16 — Due errori reali del package corretti (30 ottobre 2026)

**La build M1 resta un prototipo SOLO offline. Non installarla nel gioco.**

## 1. L'assemblatore sovrascriveva la versione dell'indice DBPF
La specifica per The Sims 4 usa DBPF 2.1, con **index minor version = 3 all'offset 0x3C** e **index offset (long) all'offset 0x40**.

Il file originale dell'utente, esportato da Lot51, ha esattamente questi campi (0x3C=3; 0x40=581). In precedenza, `tooling/build_m1_offline.py` sovrascriveva **entrambi** i campi con l'offset: il nostro stesso parser non verificava 0x3C, dunque gli 82 test del passo 15 passavano pur in presenza di questo difetto.

**Corretto:** la build preserva index minor 3. Il gate DBPF `tooling/simdata_release_gate.py` ora verifica versione 2.1 e index minor 3 prima di accettare un file. Aggiunti regressions di corruzione e sistemati i fixture sintetici.

Riferimento: https://thesims4moddersreference.org/reference/dbpf-format/

## 2. Lunghezza STBL erroneamente sottostimata
Secondo il formato STBL v5, l'header contiene la somma dei byte UTF-8 delle stringhe **più uno per voce (NUL concettuale)**; il testo reale non include NUL. La STBL autentica del package Sonozaki fornito dall'utente conferma: 26 voci, 737 byte di testo, 763 dichiarati nell'header.

Il nostro compilatore dichiarava soltanto i byte di testo e il parser verificava la stessa formula sbagliata. Ora entrambi usano la lunghezza prevista dalla specifica; aggiunti test che rigettano la codifica precedente e calcolano separatamente il totale.

Riferimento: https://thesims4moddersreference.org/reference/stbl-format/

## Cosa è dimostrato e cosa no
Sono stati corretti **due errori reali di formato** che i vecchi test non catturavano. La build in memoria ora è conforme ai campi DBPF e STBL confrontati con file reali e documentazione. Il passaggio dei test statici **non dimostra** che The Sims 4 1.129 carichi tutte le interazioni né che XML Injector le mostri sulla cassetta postale.

**Prossimo traguardo:** un prototipo installabile **separato** dal file M0 e dalla v1.6, da testare su un salvataggio di prova, solo dopo ulteriori verifiche. Il prototipo M1 non salva ancora alcuna iscrizione e non è la mod finale.
