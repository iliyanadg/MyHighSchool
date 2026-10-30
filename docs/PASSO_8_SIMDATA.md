# Passo 8 — verifica obbligatoria SimData per MY HIGH SCHOOL

Stato: **controllo offline completato, nuovo menu non ancora costruito né installabile**.

## Esito della verifica sui file forniti dall'utente

| Package analizzato | Categorie menu | SimData nel package | Esito controllo |
| --- | ---: | ---: | --- |
| `MHS_M0_MENU_NATIVO_SOLO_TEST.package` (bloccava l'avvio) | 1 | 0 | **BLOCCATO** — manca la SimData della categoria `7064630105397426819` |
| `SonozakiSisters_High_School_Management_2.2.1.package` (riferimento tecnico) | 14 | 24 (14 associate alle categorie) | **Controllo strutturale passato** |

Le risorse binarie di Sonozaki non sono state importate qui, e non saranno copiate come risorse di MY HIGH SCHOOL.

## Nuovo controllo automatico

`tooling/simdata_release_gate.py` legge un file `.package` **senza modificarlo** e verifica:
- intestazione/indice DBPF, chiavi duplicate, intervalli e decompressione supportata;
- ogni categoria `PieMenuCategory` ha XML valido e ID coerente;
- per ogni categoria esiste una SimData (`0x545AC67A`) con **lo stesso ID Instance**;
- la SimData ha un'intestazione binaria `DATA` plausibile.

Codice di esempio:

```bash
python tooling/simdata_release_gate.py /percorso/alla/build.package
```

Il controllo passa sui dati strutturali esaminati in Sonozaki e blocca M0. Non valida tutti i campi binari SimData, tutti gli schemi di tuning EA, lo snippet d'iniezione o la compatibilità di avvio: **non è una prova che una mod funzioni nel gioco**.

## Come produrre la SimData corretta

Utilizzare un generatore basato sulle Tuning Descriptions (TDESC) aggiornate, ad esempio **Lot51 Tdesc Builder**, per creare insieme la `PieMenuCategory` **originale** di MY HIGH SCHOOL e la sua SimData; non tentare di generare la SimData a mano, non riutilizzare il binario di Sonozaki. Verificare il nome del tuning, il numero Instance identico, il tipo di risorsa, i riferimenti al testo e la compatibilità del formato con la versione 1.129.39.1230.

Riferimento pubblico: https://thesims4moddersreference.org/tutorials/creating-a-pie-menu/ (sezione "SimData" e "Exporting Your Pie Menu").

### Prossimo obiettivo tecnico

1. Esportare con Tdesc Builder una categoria XML + SimData **dello stesso tuning originale**.
2. Controllare il bundle esportato con `simdata_release_gate.py`.
3. Verificare anche i tuning `SimPickerInteraction`, le conferme, l'injector e le stringhe STBL. Il superamento della verifica SimData **da solo non autorizza un nuovo test nel gioco**.
4. Solo dopo ottenere una build distinta e documentata, mai sovrascrivendo la v1.6 funzionante.
