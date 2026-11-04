# M137 — Compatibilità lavagna classe 2 con Zerbu GTS5: evidenza runtime

## Dati reali del gioco
Il report M136 `MHS_M136_TEST_EA_GIOCABILI.json` alle 10:05 identifica nel `test_globals` di `super_HighSchool_Active_Whiteboard_Class_Start` 276774 uno snippet sovrascritto nel runtime:
`Zerbu_GTS5_WhiteboardStudentTestSnippet` (tuning GUID 279071).

La struttura osservata contiene quattro percorsi:
1. `SimInfoTest(npc=False)` + `StateTest` (lavagna Classe1).
2. `TraitTest` (whitelist `trait_HighSchool_Active_Class1Student`) + `StateTest` (lavagna Classe1).
3. `SimInfoTest(npc=True)` + `TraitTest` (blacklist tratto Classe1) + `StateTest` (lavagna Classe2).
4. `SituationJobTest` che richiede `Zerbu_GTS5_ElementaryStudentBase`.

L'utente ha osservato in gioco che i tre studenti giocabili possono selezionare solamente la lavagna della Classe 1, mai la lavagna della Classe 2; alle 10:20 l'aula 1 conteneva 8 seduti (incluso un giocabile). Questa osservazione è coerente con la disuguaglianza tra ramo `npc=False` Classe1 e ramo `npc=True` Classe2.

Da M134: due giocabili iscritti alla Classe2 sono in situazione EA 304567, ruolo 280777; giocabile Classe1 in situazione 304565 ruolo 277919. Situazioni registrate correttamente. La ragione `SituationJobTest` riscontrata da M132 può essere spiegata dal ramo aggiuntivo Zerbu per la scuola elementare quando gli altri rami falliscono. La diagnostica non dimostra quale singola alternativa abbia causato il fallimento: non affermare una causalità più stretta di quella supportata.

## Direzione di correzione
Non modificare il registro, i ruoli EA, i filtri NPC o la lavagna 1. Preparare una patch di compatibilità separata **solo per l'interazione 276774 e solo i giocabili iscritti a MHS Classe2**, preservando gli NPC e i percorsi Zerbu Elementary. Serve un ramo positivo controllato per:
- Sim giocabile, adolescente, iscritto alla Classe2 del salvataggio corrente;
- situazione originale di lezione Classe2 con ruolo 280777;
- bersaglio verificato come lavagna con `state_HighSchool_Active_Whiteboard_Class2_True` 276077;
- la stessa gestione della finestra di lezione EA e nessun bypass dei restanti test/azioni.
Non rimuovere globalmente `npc=True` e non rimuovere test Zerbu Elementary. Se le API di combinazione dei test EA non sono attendibili, rifiutare l'installazione automatica e non forzare la situazione.

## Criteri di successo
1. Da giocabile iscritto Classe2, lavagna 2 selezionabile nelle ore di lezione e lavagna 1 non selezionabile per quel Sim;
2. I tre adolescenti giocabili seguono ciascuno la loro classe nel registro MHS;
3. Otto iscritti corretti fisicamente seduti per aula entro le 10:00;
4. NPC liceali e Zerbu Elementary continuano a funzionare; salvataggi separati.
Testare su copia del salvataggio. Il codice non è ancora stato corretto: questo documento è un risultato diagnostico verificato.
