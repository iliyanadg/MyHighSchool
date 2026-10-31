# Passo 65 — M56: controller completo di iscritti giocabili, studenti EA e personale

## Riscontro reale, 31 ottobre 2026

- M55b installata; dal lotto di casa il riepilogo mostra:
  `Automazione M55: installato`, `CONTROLLO_AVVIATO: Verifica scuola automatica ogni 5 minuti Sim`, `Giornata liceale: non ancora rilevata`.
- **Questo è normale dalla casa:** il controllo periodico parte, ma prima della scuola EA non esistono situazioni scolastiche attive rilevabili. Non equivale né a riuscita né a fallimento della convocazione.
- Al liceo la creatrice vede ancora adolescenti e personale scelti da EA. Non c'è evidenza che tutti i 16 iscritti siano stati convocati.
- Servono **diagnostiche del gate a scuola** (errore del save-slot, ora Sim, API situazioni EA, nessuna situazione base, o chiamate create_situation rifiutate): il codice M55b precedente faceva return silenziosi.
- M55c aggiunge: contatore poll, ultimo gate con motivo, riepilogo per classe, contatore adolescenti giocabili della famiglia e nomi di quelli non iscritti, tutti **sola lettura**, senza cambi a dati o tuning EA. Compilazione separata M55c e test Mac necessari.

## Regole funzionali vincolanti per il controller finale

### Iscrizione = un posto reale per ogni adolescente, giocabile o NPC
- Un adolescente giocabile entra dal medesimo selettore «Prepara iscrizione» già funzionante. Non si aggiunge automaticamente: l'utente sceglie classe e posti.
- **8 studenti TOTALI per Classe 1/2/3**, senza quote extra per giocabili. Es. Classe 1 = 3 giocabili + 5 NPC.
- Se l'utente accompagna 2, 3 o 4 Sim adolescenti dello stesso nucleo, tutti possono partecipare al giorno scolastico EA, ma la loro *assegnazione a una nostra aula* richiede iscrizione. Possono occupare classi diverse.
- I giocabili **non vengono invitati a un job NPC**; il controller li riconosce sul lotto, li associa alla classe del registro, e implementerà routing in aula alla lavagna pertinente.
- Teen giocabile non iscritto: avviso di classe non assegnata; non forzare iscrizione. EA può farlo partecipare, ma non deve diventare un sedile extra della classe gestita.
- Se entrambe le classi hanno 8/8 NPC iscritti, per aggiungere 3 giocabili liberare/spostare 3 posti oppure abilitare Classe 3. Solo dopo la nuova spunta la selezione vale nel prossimo giorno di scuola (se scolastica attiva).
- Con cambio di famiglia, un ex-giocabile rimane iscritto ma va trattato come altro Sim non controllato se non è l'attuale nucleo attivo. Nessun doppione; legare tutto all'ID univoco Sim + slot, non ai nomi.

### Controller della presenza reale (NON ancora implementato da M55b/c)
- Un'unica lista autorevole di SimID dal registro persistente per ciascun giorno, con conversione giocabile/NPC dinamica e rispetto di genere/specie/età.
- Trovare i filtri/ruoli e le situazioni ufficiali **EA High School Years**, non limitarsi a creare una situazione aggiuntiva per ogni Sim, perché EA continuerà a scegliere NPC dal suo roster. Analizzare il filtro dei Core NPCs e della scelta compagni; in alcuni casi EA richiede ruoli speciali (cheer/football/chess/computer/mean).
- Integrare un controllo sicuro della selezione dei partecipanti EA, sostituendo la lista invece di generare NPC ogni giorno, senza rimuovere alcun Sim dal save. Bloccare attivazione in presenza di altri mod controller dello stesso liceo; non entrare in guerra con More Students, Sonozaki HS o altri override.
- Diagnosi fisica: contare chi è effettivamente instanziato nel lotto e nel contesto della situazione, non confondere un ID situazione creata con presenza reale, non contare l'iscrizione nel registro come presenza.
- Solo dopo aver verificato con successo classi 1 e 2 pilotate realmente implementare la Classe 3 tramite terza lavagna/docente/situation autonoma. Una scuola EA senza mod ha solo due aule standard, ma soluzioni con controllo dell'infrastruttura possono creare altre aule. Non dichiarare terza aula reale finché non è testata.
- Mantieni pranzo, esami, prom e graduation EA e la possibilità di seguire più figli adolescenti da famiglia attiva.

### Personale reale EA (NON ancora implementato da M55b/c)
- Associa il registro M54 al ruolo di preside (1), docente per classe (1, 2, 3), bidelli (massimo 2), mensa (massimo 3).
- La semplice assegnazione nel file `Personale_slot_*.json` **non fa** diventare il Sim insegnante/dirigente EA: il controller dovrà sostituire/fornire l'incarico nel `SituationJob` corretto, verificare i filtri del lotto e che il Sim compaia fisicamente. Nessun ruolo duplicato.
- Studiare eventuali capacità effettive di EA (staff 2 mensa, 1 janitor, ecc.) e allargare solo con modifiche testate e senza rompere i ruoli EA.

## Test successivo che risolve il blocco logico attuale

Dalla schermata di casa `CONTROLLO_AVVIATO` è corretto, ma non diagnostico. Serve **una sola schermata del menu «Consulta presenze automatiche» dal lotto del liceo mentre si svolge la scuola**, dopo almeno 15 minuti Sim non in pausa. La nuova versione M55c mostrerebbe:
- `ATTESA: Situazione EA liceo Base_Student non rilevata`: occorre integrare filtro e trigger diverso;
- `ERRORE: ...`: correggere API/slot/orologio;
- `GIORNATA_ELABORATA` con richieste >0 ma studenti non presenti: inviti EA non bastano; occorre controllare il roster EA ufficiale;
- `Non iscritti:...` per i giocabili: l'iscrizione manuale (posti dentro 8) va configurata prima di pretendere la loro aula.

Non promuovere la release finché il test in gioco del controller EA non conferma la presenza fisica di studenti e personale reali.
