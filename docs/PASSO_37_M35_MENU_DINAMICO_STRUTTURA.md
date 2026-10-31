# Passo 37 — M34 validata per persistenza / modello M35 del menu dinamico

**31/10/2026, dopo prova Mac reale.**

## Conferma della giocatrice
Al rientro nello stesso salvataggio di prova (slot 11) dopo chiusura e riavvio di The Sims 4, la console `mhs34.settings` mostra:
- `Gestione iscrizioni: DISATTIVA`
- `Classi disponibili: 2`
- `Classe 3 iscritti: 0`
- `Solo registro esterno, NON controlla ancora il liceo EA.`

Quindi la **persistenza su JSON delle impostazioni M34 è verificata nel client reale**.
Le sei verifiche principali M34 completate: default off/2, attiva, 2→3, 3→2 con Classe 3 vuota, disattiva, riavvio con off/2. Non è prova di funzionamento delle aule vere.

## Struttura esatta del menu finale richiesta
- `MY HIGH SCHOOL` è il primo pulsante.
- Quando il sistema è DISATTIVO, dentro appare solo `Attiva`. Nessuna opzione di iscrizione/modifica classe.
- Quando è ATTIVO, ci sono `Disattiva`, `Impostazioni`, `Classe 1`, `Classe 2` e `Classe 3` **solo se è attiva la modalità a 3 classi**.
- `Impostazioni` espone la scelta 2/3 classi. Se Classe 3 ha iscritti, non permettere 3→2 senza prima trasferirli/ritirarli (già verificato offline in M34).
- Dentro ogni Classe: `Iscrivi studenti`, `Consulta iscritti`, `Rimuovi studenti`, `Trasferisci in Classe X` per ogni altra classe attiva. Nessun pulsante della classe sbagliata.
- Ogni classe ha un limite fisso di **8 iscritti**. Le opzioni devono funzionare anche quando il tempo del gioco è in pausa, con anteprima e conferma grafica che aggiornano il registro senza passare dalla console.
- La voce `Consulta iscritti` con classe vuota deve avvisare esplicitamente «Nessuno studente iscritto» e non rimanere silenziosa.

## Cosa è stato implementato effettivamente ora
- `src/m35_menu/mhs35_menu_model.py`: modello dati puro **condizionale** per i menu: 2/3 classi, attiva/disattiva, operazioni limitate alla classe di origine; nessuna scrittura o API EA.
- `tests/test_m35_menu_model.py`: test automatici per menu disattivo, selezione 2/3, classe 3 vuota e isolamento slot, nessuna mutazione del registro.
- I test sono online nel workflow offline del repository (con esito positivo).
- **Non esiste ancora una build M35 installabile**. M34 rimane l'ultima build di test funzionante per il registro. Non dire all'utente di scaricare M35 e non presentare il modello come un vero menu in The Sims 4.

## Criticità da risolvere nella futura integrazione
- M30/M32 aveva 3 nuove PieMenuCategory con SimData, ma il client Mac ha segnalato **invalid category ID**, bloccando la cassetta postale. Deve essere risolta la registrazione dei riferimenti senza regredire all'interfaccia interamente non cliccabile.
- Le interazioni `ImmediateSuperInteraction` M33/M34 devono partire dal Sim e durante la pausa non vengono eseguite: il futuro sistema deve essere progettato con interazione UI realmente disponibile in pausa e non basata sulla coda del Sim.
- Per ora `mhs34.settings` gestisce **solo il JSON esterno** e non controlla la frequenza scolastica EA. Prima di presentarla come mod finita, implementare e testare le vere situazioni scolastiche, aule, insegnanti e roster persistente di frequenza.
- Il commit delle iscrizioni e rimozioni nella M34 usa ancora comandi della console; non scrivere dati finché non c'è copia di backup per partita di prova.

## Passaggio successivo
Progettare e verificare con un singolo test isolato il meccanismo compatibile con il client del menu annidato. Integrare il modello M35 con la UI una volta stabilito come fare, mantenendo la M34 funzionante come fallback. In parallelo, progettare il dialogo di conferma e azioni disponibili in pausa; non fingere che sia già disponibile.
