# Passo 32 — M30: tre sottomenu nativi per le classi (test Mac)

## Richiesta confermata dalla prova M29

Invece di nove voci sparse nel menu MY HIGH SCHOOL, l'utente vuole:
- MY HIGH SCHOOL → Classe 1 → azioni Classe 1
- MY HIGH SCHOOL → Classe 2 → azioni Classe 2
- MY HIGH SCHOOL → Classe 3 → azioni Classe 3

**Foto M29 dell'utente:** il menu test compare sulla cassetta postale. `mhs28.roster` restituisce salvataggio di prova slot 11 con:
- Classe 1: 2/8, Baby Ariel e Amarachi Darong
- Classe 2: 2/8, Sofia Bjergsen e Sofia Abrantes
- Classe 3: 0/8
Tali studenti non sono codificati a mano: il menu rimane dinamico.

## Implementazione M30

- Costruite **tre nuove PieMenuCategory** con istanze univoche e campo `_parent` diretto alla categoria MY HIGH SCHOOL, mantenendo intatta la categoria madre. Chiavi per le categorie a 31-bit.
- Ognuna ha XML Tuning **e** SimData compilata, derivata da copia del template in uso: `_parent` e `_display_name` aggiornati in una struttura binaria di dimensione invariata, con verifica esatta dei byte.
- Le nove operazioni grafiche esistenti sono associate a una delle tre sottocategorie: iscrizione (che puo anche spostare studenti se c'e posto), rimozione e consultazione. 3 per classe.
- Le funzioni diagnostiche e gli scambi fra classi piene restano disponibili tramite la console (non ancora pulsanti dedicati): `mhs28.swappreview`, `mhs28.swapcommit`, `mhs28.roster`.
- Nessuna modifica al formato dei dati, ai 4 iscritti di prova, al resto della Mods o al numero di studenti; tutte le funzioni precedenti della M29 rimangono presenti.

## Distinzioni fondamentali

- Il sottomenu e una struttura di tuning/SimData. I test GitHub del package e di Python 3.7 sono passati, ma **deve ancora essere verificato nel gioco** che il client organizzi correttamente le 3 categorie.
- Non chiamare il tasto iscrizione 'Scambio classi piene': quello rimane per ora un comando console per due ID.
- Il numero 2/8 sopra viene dal registro fotografato, non e un numero hardcoded del menu e non compare necessariamente nell'etichetta della categoria.
- La UI di consultazione/rimozione M27/M29 non ha ancora completato la prova reale dopo la correzione del crash `icon_resource`.
- Non modifica la scuola EA, la presenza in lotto, le lavagne, il corpo docente o il salvataggio EA; il registro rimane un JSON esterno.

## Installazione SOLO in partita di prova

1. Finire qualsiasi prova in corso. Chiudere completamente il gioco senza salvare una partita di test che non si vuole alterare.
2. Scaricare l'archivio dal workflow [M30](https://github.com/iliyanadg/MyHighSchool/actions/runs/41144870227).
3. Spostare FUORI dalla Mods **solo** i due file sperimentali M29 attualmente installati. Non toccare v1.6, XML Injector o i file dei registri.
4. Estrarre e inserire la coppia `MHS_M30_MENU_CLASSI_TEST.package` e `MHS_M30_MENU_CLASSI_TEST.ts4script`.
5. Avviare salvataggio TEST. Cliccare la cassetta: attesi **Classe 1, Classe 2, Classe 3**, dentro ciascuno consultazione, iscrizione e rimozione.
6. Aprire soltanto un sottomenu (nessun commit) e verificare se le tre azioni appaiono; poi `mhs28.roster` per controllare 2/8, 2/8, 0/8. Se non compaiono le categorie, usare screenshot e non salvare.
7. Prima di qualsiasi test scrivente, fare backup della cartella JSON esterna. La chiusura senza salvare del gioco **non** annulla un comando `commit` gia eseguito.

Questa build non va installata nella partita principale fino a validazione.
