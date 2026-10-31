# Passo 63 — M55: presenze automatiche di TUTTI gli studenti iscritti (test Mac)

## Decisione della creatrice — 31 ottobre 2026

La creatrice ha rifiutato l'approccio «un Sim alla volta» e ha richiesto una versione M55 **collettiva, automatica e quotidiana**: i ragazzi selezionati nel registro di Classe 1/2/3 devono essere richiamati alla scuola senza scegliere manualmente uno studente dal menu ogni volta.

## Realizzato nei sorgenti su branch dedicato

- Attivazione: MY HIGH SCHOOL deve essere attiva nelle impostazioni M34. Il registro esterno di ciascuno slot rimane immutato.
- Automa: dopo il caricamento di una zona il runtime installa un solo allarme di gioco che verifica ogni 5 minuti Sim se è già attiva una vera situazione `situation_HighSchool_Active_NPC_Base_Student` (GUID 277733).
- Solo nel contesto che presenta effettive situazioni scolastiche EA, pianifica una giornata per **tutti** gli iscritti alle 2 o 3 classi attive (massimo 8 per ciascuna, fino a 24). Esegue al massimo 3 richieste ogni allarme, riducendo il picco di situazioni create contemporaneamente.
- L'elenco viene congelato all'inizio della giornata: trasferimenti o nuove iscrizioni durante la scuola non cambiano la convocazione della giornata già pianificata; varranno dal giorno successivo.
- Per ogni studente verifica che esista ancora, sia umano e adolescente. Non genera sostituti casuali.
- I Sim della famiglia giocata non vengono convertiti in NPC scolastici dalla mod (richiedono il flusso EA dei liceali giocabili).
- Chi è già presente nella situazione EA non viene convocato nuovamente. Per gli altri il runtime usa la situazione base 277733 e il job EA 277894, con UNA richiesta per ciascun ID. Nessun retry nella stessa sessione di scuola anche se il motore rifiuta una richiesta.
- Il controllo per save-slot usa **due fonti EA attive**: il proto di persistenza e `client.account.save_slot_id`. Se dopo il viaggio la prima riporta 0, viene usata l'altra soltanto se non nulla e valida; se sono entrambe positive ma discordanti, la convocazione si blocca. Nessun riutilizzo di uno slot dalla partita precedente.
- Stato in memoria consultabile in `MY HIGH SCHOOL → Classe 1 → M55 - Consulta presenze automatiche`. Il messaggio mostra quanti sono stati richiesti, già presenti, giocabili, non idonei e non riusciti. Non è un registro storico delle assenze.
- Il `.package` conserva le 10 categorie Lot51/SimData e le interazioni funzionanti della M54. Aggiunge soltanto una interazione di consultazione, due localizzazioni e un injector aggiornato (63 risorse invece di 62). La `.ts4script` include i 19 moduli esistenti + pianificatore + automatismo + interfaccia = **22 moduli**. Va compilata per Python 3.7 attraverso GitHub Actions.
- Il tentativo di convocazione non cambia l'appartenenza alle aule tramite trait EA, non modifica i ruoli del personale EA, non riscrive la giornata di EA e non elimina situazioni dei liceali casuali.

## Limiti da non confondere con funzionalità collaudate

**Test automatici e codice non garantiscono che tutti i 24 Sim siano effettivamente presenti sul lotto.** Il motore di gioco può rifiutare le situazioni, imporre limiti di popolazione, generare i propri NPC, o cambiare ruoli EA. Anche il numero di aule è limitato: l'EP Vita da Liceali possiede nativamente due aule; i ragazzi di Classe 3 sono convocabili come Sim ma **non viene creata una terza lezione/una terza lavagna EA**. L'appartenenza a Classe 1/2 del nostro registro non pilota ancora l'assegnazione EA a una lavagna. Anche il personale M54 resta nel registro e non è ancora incaricato nel lotto EA. Per una mod completa come immaginata restano necessari un controller delle lezioni, lo staff reale e una politica per gli studenti spontanei di EA.

**Il runtime usa un hook sul caricamento della zona**: ogni aggiornamento del gioco va testato sul Mac. Se l'API di fine caricamento non esiste o entrambe le fonti di save-slot sono ignote/in conflitto, fallisce senza invocare alcun Sim; consultare lo stato. Nei test precedenti il proto poteva riportare 0 al liceo: la M55 ora consulta anche il valore corrente dell'account EA, **mai** un vecchio valore del modulo.

## Come testare quando GitHub Actions termina con successo

1. Eseguire le prime prove **solo in una partita di prova separata**. Fare copia della coppia M54 e della cartella `MY_HIGH_SCHOOL_M25_TEST_DATA`; non salvare sopra la partita narrativa principale.
2. Chiudere The Sims 4. Rimuovere la coppia M54 e installare **entrambi** i file M55 provenienti dalla stessa run CI riuscita. Non mescolare versioni.
3. Verificare MY HIGH SCHOOL attiva, Classe 1 e 2 popolate con Sim scelti; Classe 3 se richiesta.
4. Andare al liceo con una Sim giocabile durante la normale giornata scolastica e **non premere alcun comando per convocare persone**. L'automazione controlla quando EA ha avviato le situazioni scolastiche.
5. Aprire `MY HIGH SCHOOL → Classe 1 → M55 - Consulta presenze automatiche`. Controllare il riepilogo, quanti studenti sono apparsi realmente e se il gioco consente le lezioni.
6. In caso di slot non verificabile, eccezioni, problemi di freeze o schermi bloccati: uscire senza sovrascrivere il salvataggio di prova, tornare alla M54 e comunicare l'errore.

**Stato**: sorgenti per il comportamento collettivo in branch M55 e CI automatica. Test Mac, compatibilità con altre mod, convocazione fisica, capienze e 3 lezioni reali non ancora confermati. Non effettuare merge in main prima del test.
