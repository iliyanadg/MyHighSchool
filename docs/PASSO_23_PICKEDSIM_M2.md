# Passo 23 — Recupero sicuro degli ID scelti dal SimPicker

**Stato: sorgenti e test, non installabile. Nessuna modifica alla v1.6.**

Nel prototipo M1 già verificato in gioco funzionano il menu,
il picker a 8 posti, le due continuazioni e le notifiche italiane.
Ma **nessun file M1 contiene una callback Python che salva gli ID**.

Fonti su partecipanti e continuazioni (distinguere dai nostri test):
- https://andirz.com/modding/participants-resolvers/
- https://sims-4-modding.fandom.com/wiki/Participant
- https://sims4communitylibrarywiki.readthedocs.io/en/latest/sims4communitylib.classes.interactions.html

Le fonti spiegano che `PickedSim` è il partecipante scelto tramite picker,
che può essere propagato nella continuation, e che le interazioni
espongono `get_participants()`. **NON garantiscono** che una singola
continuation contenga tutti gli otto Sim selezionati: è questo il
prossimo punto da verificare nel gioco prima di salvare.

## Cosa è stato realizzato
`src/m2_registry/mhs_m2_selection_probe.py`:
1. `collect_picked_ids(interaction, ParticipantType.PickedSim)`:
   legge esclusivamente `PickedSim`; ricava ID da `SimInfo` o `Sim`,
   non usa mai il Sim che apre il menu (`Actor`) o il target mailbox
   come se fossero uno studente. Blocca duplicati, ID sbagliati,
   numero zero o superiore a 8, valori mancanti.
2. `require_complete_selection(... expected_count,
   confirmation_of_full_batch)`: NON permette di scrivere se il numero
   ricevuto dal gioco non coincide con il **conteggio scelto verificato
   indipendentemente** oppure se la provenienza del batch non è certa.
3. `enroll_confirmed_batch(...)`: collegamento col
   `EnrollmentService` del passo 22; può scrivere su JSON separato
   soltanto se sono soddisfatte tutte le condizioni.
4. I test `tests/test_m2_selection_probe.py` includono scenari
   di selezioni complete/incomplete, Sim giocabili e NPC
   simulati, ID duplicati, adulti, selezione non certificata,
   salvataggio della partita non disponibile e file mai creati
   in caso di errore.

## Nota cruciale di implementazione
`confirmation_of_full_batch=True` nel test Python è un *dato
simulato*, NON prodotto dal gioco. Non abbiamo ancora estratto
l'informazione autorevole dal selettore nativo di The Sims 4. È
intenzionalmente impossibile attivare una scrittura vera finché non
avremo verificato questo dettaglio in-game.

**Prossimo passaggio:** costruire una sonda Python di sola lettura che
venga eseguita dalla continuation del picker M1 (in una build
diagnostica diversa da M1), e misurare quanti `PickedSim` arrivano
quando la persona ne seleziona 1, 3 e 8. Niente iscrizioni durante
questa prova. Soltanto se è garantita la completezza si collegherà
il pulsante ✓ al registro JSON; altrimenti servirà un callback
diretto al picker.
