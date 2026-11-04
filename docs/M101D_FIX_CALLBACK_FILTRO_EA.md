# M101d — Corretto callback obbligatorio del filtro EA

## Prova sul Mac M101c

Alla scuola alle 10:13 del salvataggio di test, il JSON
`MHS_M101_UNO_SLOT_EA.json` ha riportato:

- 13 NPC iscritti considerati (`candidate_count=13`).
- Filtro EA `280516`.
- `exception_type=TypeError`.
- `exception_message="submit_filter() missing 1 required positional argument: 'callback'"`.
- `exception_location.function="_filtered"` in `mhs57_filter_runtime.py`.

La M101c richiedeva `submit_filter(sim_filter=filt, sim_constraints=ordinary, allow_yielding=False)`, omettendo l'argomento `callback`. Il wrapper M57d non è la causa: inoltra semplicemente alla API EA i parametri ricevuti.

## Modifica

La M101d chiama `submit_filter(callback=None, sim_filter=filt, sim_constraints=ordinary, allow_yielding=False)` per una richiesta sincrona. Nessun callback asincrono: la selezione deve avere una risposta *immediata* per sostituire in sicurezza uno slot scolastico originale prima dello spin-up EA.

Un test automatico simula la firma EA con il parametro `callback` obbligatorio e verifica che venga passato `None`. Se il filtro non dà subito veri risultati con `SimInfo` e punteggio, M101d mantiene il comportamento originale EA, senza sostituzioni inventate.

Sono conservati: due aule con 8 iscritti ciascuna, tre adolescenti giocabili (Rosario, Sandro e Sofia), 13 NPC, una sola possibile sostituzione su una situazione originale del calendario EA e nessuna situazione aggiuntiva.

## Test Mac

Questa build è distinta da M101c: `MHS_M101D_CALLBACK_EA_MAC_TEST`.

1. Solo quando GitHub Actions conferma il successo della compilazione: scaricare il relativo Artifact.
2. Chiudere The Sims 4 e fare una copia del salvataggio.
3. Togliere i due file M101c dalla cartella Mods e mettere soltanto il .package e il .ts4script M101d.
4. In un nuovo giorno scolastico, a casa verso le 6:50: `mhs101.arm`.
5. Accompagnare Rosario, Sandro e Sofia a Copperdale.
6. Alle 10:00: `mhs101.check`. Inviare il report `MHS_M101_UNO_SLOT_EA.json` da `Documents/Electronic Arts/The Sims 4/MY_HIGH_SCHOOL_M25_TEST_DATA`.

**Non affermare che 13 NPC arrivino o che le classi siano sotto controllo prima della validazione in-game.** Una situazione accettata non equivale a uno studente arrivato o seduto in aula.
