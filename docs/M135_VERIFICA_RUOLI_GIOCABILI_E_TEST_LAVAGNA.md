# M135 — Ruoli EA dei giocabili: conclusione verificata

Dati forniti dall'utente da MHS_M134_RUOLI_EA_GIOCABILI.json, giorno EA 3 alle 10:07, save slot 11.

- Giocabile Classe2 ID 568605179484009778: situazione originale 304567, job EA 280777.
- Giocabile Classe1 ID 568605179485058376: situazione originale 304565, job EA 277919.
- Giocabile Classe2 ID 568605179488204115: situazione originale 304567, job EA 280777.
- I tre Sim sono istanziati e il metodo di lettura delle situazioni ha funzionato. Nessuna modifica in gioco.

**Conclusione verificata:** non manca l'appartenenza alla situazione di lezione nativa EA e non serve assegnare ciecamente il job 277919 ai giocabili della Classe2. Il messaggio originario `SituationJobTest: Sim does not have required situation job` viene dal percorso di test dell'interazione della lavagna, non prova che il Sim sia estraneo alla sua lezione.

La situazione native della Classe2 usa job 280777 mentre quella della Classe1 usa job 277919; il percorso dell'interazione `super_HighSchool_Active_Whiteboard_Class_Start` 276774 con `test_globals` che referenzia lo snippet 279071 non è simmetrico: nello snippet 279071 un ramo Classe2 richiede esplicitamente NPC True, mentre il ramo Classe1 ha un trait whitelist. Questo non prova ancora che sia l'unico blocco; lo snippet non contiene un SituationJobTest.

**Prossimo intervento circoscritto:** ispezionare nel runtime le istanze effettive di `SituationJobTest` nel TestList (inclusi eventuali contributi di mod esterne) e le relative liste dei job richiesti; confrontare i GUID con 280777 e 277919, senza rimuovere globalmente i test o cambiare l'iscrizione. Solo se la corrispondenza e chiara creare alternativa player Classe2 protetta da registro MHS + board Class2 + job nativo.

Nota: nel report `affordance_test_metadata` il TestList include anche un test di WickedWhims, cioe il runtime ha un'interazione patchata da una mod terza; questo **non** e prova che la mod causi il rifiuto.

Non dichiarare che 8/8 ruoli equivalgono a 8/8 studenti fisicamente seduti alle 10:00. Il test M134 e un readback dei ruoli, non una verifica di posti.
