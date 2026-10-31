# Passo 47 — M44 build locale da SimData autentica Lot51 (2026-10-31)

## Esito
L'utente ha fornito le tre categorie che mancavano (i nuovi .package Lot51):
- creator_name-tuning-export-1793450518.package: Classe 1 XML e SimData;
- creator_name-tuning-export-1793450553.package: Classe 1+2 XML e SimData;
- creator_name-tuning-export-1793450562.package: Classe 1+2+3 XML e SimData.

Per la build finale sono stati combinati i seguenti **tre export non sovrapposti**:
- creator_name-tuning-export-1793449868.package: radice MainMenu;
- creator_name-tuning-export-1793450021.package: Settings (ignorando l'interazione extra ChooseClass3);
- creator_name-tuning-export-1793450562.package: Classe 1/2/3.

Il merge è stato realizzato a partire dal `MHS_M43_MENU_GERARCHIA_E_FIX_TEST.package` e `.ts4script` **realmente forniti dall'utente** e non da nuove modifiche speculative al codice della gestione degli studenti.

Le categorie di Lot51 hanno gli stessi campi XML della M43 (differiscono soltanto nell'ordine degli elementi, nei ritorni a capo e nella dichiarazione XML); i tuning XML sono rimasti byte-per-byte identici alla M43.

Le **4 SimData figlie** (Classe 1/2/3/Settings) sono state sostituite *integralmente* con i loro 475 byte ricompilati da Lot51, senza modificarli a mano. Il root SimData è byte-per-byte identico tra M43 e Lot51, quindi è stato conservato.

### Differenza misurata in ogni SimData figlia
- 4 byte in posizione 0x24..0x27: nuovo valore generato da Lot51, diverso dall'header copiato del vecchio template;
- 8 byte da 0x5C a 0x63: TableSetReference cambia da `CF D9 C0 73 00 00 00 00` a `00 00 00 00 CF D9 C0 73`, cioè Parent `1942018511` in high-half dei 64 bit.

Non è stato toccato nessuno degli altri 25 record (interazioni XML, snippet injector, STBL). L'archivio `.ts4script` è copiato byte-per-byte dalla M43 (15 moduli Python 3.7, ZIP CRC valido).

Output creati nella sessione chat:
- `MHS_M44_MENU_ANNIDATO_LOT51_TEST.package`
- `MHS_M44_MENU_ANNIDATO_LOT51_TEST.ts4script`
- `MHS_M44_MENU_ANNIDATO_LOT51_TEST.zip` (entrambi i file sopra).
- `MHS_M44_DIAGNOSI_E_INSTALLAZIONE.txt` con istruzioni.

Checksum SHA-256 `package`: `078f512c4e3c121c30a749cfb3eb2ce040335fd7209d32548c47b44c9294d1fb`.

Tutte le 35 risorse DBPF sono state decodificate e reimpacchettate correttamente. Dieci risorse sono categorie+SimData, con cinque categorie univoche, ciascuna con la sua SimData. I quattro children hanno Parent correttamente codificato nel formato Lot51. È stato confermato che nessuna stringa o script è cambiato.

**Stato: COMPILATO, TEST MAC NECESSARIO.** Ancora nessuna prova di annidamento in gioco, quindi non dichiarare già risolto. Il risultato precedente M43 era stabile ma menu non annidato. La M44 dovrebbe testare proprio questa differenza, senza reinstallare altre mod né modificare il salvataggio principale.

### Test raccomandato
1. Chiudere gioco e fare copia di sicurezza della cartella dati JSON del progetto (l'interazione modifica file esterni, anche senza salvare la partita). Conservare la coppia M43 fuori Mods per rollback.
2. Togliere da Mods solo le versioni MHS precedenti; inserire **soltanto** i due file M44 sotto `Mods/MY HIGH SCHOOL`, lasciando tutte le altre mod intatte.
3. Aprire il salvataggio di prova, cliccare la cassetta postale e verificare che Classe 1, Classe 2, Classe 3, Impostazioni siano *all'interno* di `MY HIGH SCHOOL`, senza loop di eccezioni Better Exceptions.
4. Non modificare iscrizioni in questa verifica. Se compare un errore, chiudere senza salvare; ripristinare M43.

La parte funzionale del registro studenti non viene considerata completata: controlli reali della frequenza scolastica EA, conferme native in pausa e navigazione completa richiedono ulteriore sviluppo.
