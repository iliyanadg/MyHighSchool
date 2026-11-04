# M129 — Risultati di ESTRA..zip: quaderni e percorso dei giocabili

Archivio fornito dall'utente, quattro file effettivi:
- `super_HighSchool_Active_CreateBook_Class` (276782)
- `super_HighSchool_Active_UseBook_Class` (276784)
- `buff_Role_Highschool_Active_Player_AttendClass` (276710)
- Sim Data dello stesso buff

## EA originale: creazione quaderno

`super_HighSchool_Active_CreateBook_Class` (276782) ammette `posture_Sit` e `posture_Stand`. Crea un libro nell'inventario tramite due varianti condizionali per giorni d'esame e non d'esame; continuazione `super_HighSchool_Active_UseBook_Class` (276784), bersaglio `CreatedObject`. Quindi non è una routine che assegna un banco della stanza MHS.

## EA originale: uso quaderno

`super_HighSchool_Active_UseBook_Class` (276784): `posture_target_preference` include `SEATING_DESK=30`, `SURFACE_DESK=30`, `SEATING_DINING=10`, `DINING_TABLE=15`, `SEATING_BED=5`, `SEATING_SOFA=5`, ecc. `prefer_surface=True`. Sono preferenze e non garantiscono seduta al banco giusto. Sotto `conditional_actions` è presente il termine naturale su rimozione del buff NPC studenti 276312, buff NPC Classe 2 304592, buff giocabili 276710, e altri. **Non inferire che rimuovere il buff sia sicuro per affrettare il routing.**

## EA originale: buff giocabile

`buff_Role_Highschool_Active_Player_AttendClass` (276710) porta `target_super_affordances` = `super_HighSchool_Active_Whiteboard_Class_Start` (276774), con filtro per tag `Func_HighSchool_Active_Whiteboard`. Non restringe nel buff la lavagna a una classe MHS. `autonomy_modifier` assegna punteggio 0 ai motivi Fun/Hunger/Social; ciò non equivale a imporre un'azione di seduta.

La presenza di Sim Data di questo buff nel pacchetto non fornisce ulteriori istruzioni di routing.

## Conseguenze e sequenza sicura

1. Confermare correzione M128 allineamento 9 tratti classe, poi controllare ancora lavagne/test EA; senza conferma non attribuire a banchi l'intero difetto.
2. Distinguere tutti e tre i livelli per ogni SimID: registro MHS -> lavagna EA -> vero banco occupato (non semplicemente postura Sit).
3. NPC: scegliere/limitare correttamente lavagna sulla base della classe registrata e tratti EA.
4. Giocabili: strada separata tramite `Whiteboard_Class_Start`; il buff giocabile non forza ingresso automatico.
5. Per garantire seduta entro le 10 servirà un intervento specifico sulla scelta/routing verso 8 banchi liberi fisici in ogni aula PRIMA dell'orario EA; questi quattro XML **non dimostrano un'API concreta** per prenotare/forzare otto banchi, perciò non inventare una chiamata di runtime né promettere 8+8 puntuali.
6. Verificare su copia di salvataggio la capienza di banchi utilizzabili, percorso libero, player non interrotti, eventuali altri mod conflittuali.

Stato: analisi tuning completata; nessuna nuova beta correttiva dei banchi compilata o verificata in partita.
