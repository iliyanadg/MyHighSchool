# MY HIGH SCHOOL — versione giocabile e funzioni complete

**Base da proteggere:** commit `fb877355`, ramo `stable/mhs-16-students-8-staff-2026-11-06`. L'osservazione in gioco ha mostrato 16 studenti, 8 persone del personale e limite NPC effettivo 30. Nessun cambiamento al roster, ai ruoli o alla capienza è ammesso come "ottimizzazione" senza regressione e prova nel gioco.

## A. Chiusura del primo ciclo giocabile (M149/M150)

1. **Lezioni:** iniziare il tragitto prima delle 10:00 (obiettivo 09:40 nel tempo visualizzato), lezioni EA alle 10:00 e 14:00, lavagna giusta per ogni classe. I Sim giocabili possono scegliere **anche manualmente** le interazioni originali della propria lavagna; un comando già scelto prevale sull'invito automatico. Non dichiarare riuscita dall'accettazione di un push o da una seduta osservata.
2. **Mensa:** conservare servizio EA, i tre addetti con situazioni native disponibili e la pausa comune. Verificare NPC che ordinano/mangiano e le transizioni verso la lezione successiva; non costringere i Sim giocabili a mangiare. Non certificare tutti i pasti da uno snapshot.
3. **Giorni successivi:** confrontare per SimID gli stessi 16 iscritti, le classi 8+8 e lo stesso personale anche dopo uscita dal lotto, salvataggio, riavvio e nuova giornata. Le presenze fisiche e i lavori EA devono essere controllati separatamente dalla selezione salvata.
4. **Prestazioni:** misurare entrambi gli orologi (interfaccia e simulazione); distinguere il carico diagnostico da ritardi causati dal gioco/altre mod. Ridurre scansioni passive, NON le richieste EA delle lezioni. Con un divario di 30–43 minuti non è corretto dichiarare garantita l'entrata entro le 09:40 visualizzate.
5. **Regressione:** nessun NPC non iscritto, nessuna sostituzione casuale, nessun evento vanilla rotto, compatibilità con gli adattatori EA/Zerbu, funzionamento su Mac e test Windows ancora da eseguire.

## B. Classi 3 e 4 — sviluppo effettivo, non pulsanti vuoti

Il controller convalidato usa esattamente **due** situazioni native di lezione e due lavagne EA esclusive. Il registro/il menu storico ammette al massimo tre classi, ma questo NON prova che una terza lezione separata funzioni. È vietato presentare la terza o la quarta classe come pronta finché non esistono test per **quattro** aule con 1 docente e 8–10 adolescenti ciascuna, situazione di lezione autonoma, orari EA compatibili e politica di capienza verificata. Conservare la possibilità di scegliere 2, 3 o 4 classi e mostrare soltanto quelle realmente supportate. Durante la migrazione, l'attuale salvataggio 2×8 deve restare utilizzabile.

## C. Creare Sim dal menu

Usare esclusivamente un flusso CAS realmente supportato dal runtime del gioco. Alla conferma, leggere l'ID del nuovo Sim adolescente e verificare età, specie, capienza e salvataggio corrente prima dell'iscrizione. Annullare CAS non deve modificare il registro. La lista degli NPC esistenti deve restare alternativa. NON fabbricare un Sim ID né dichiarare CAS completo per aver soltanto aperto l'editor.

## D. Menu e opzioni avanzate

Gestione PC/cassetta postale, iscritti e non assegnati, ricerca/filtri, multiselezione, trasferimenti anche a classi piene, scelta NPC precisa per riempire posti, personale e sostituzioni, regolamento dei giorni successivi, anziani diplomati, pensionamenti/decessi, ballo e diploma. Ogni operazione è per-salvataggio e gli effetti durante l'orario scolastico vanno al successivo giorno. Conservare possibilità di disattivare e riattivare senza perdere i dati.

## Condizioni prima di dichiarare una release

- Compilazione Python 3.7 e test GitHub tutti superati.
- Test reale su **copia** di un salvataggio, dal mattino alla fine delle lezioni e almeno un giorno scolastico successivo.
- NPC cap, 16 studenti e personale invariati rispetto alla base stabile, più prove specifiche sulle nuove opzioni.
- Nessun merge nella base stabile sulla sola base dei test offline.
