# M99 — Perché Baby Ariel non è arrivata dopo EA=True?

## Prova reale che ha motivato questo intervento

Lunedì nel gioco, a Copperdale, 16 iscritti MHS (Rosario,
Sandro e Sofia giocabili, più 13 NPC) hanno prodotto solo 4
iscritti presenti e 7 studenti non iscritti. Su comando
`mhs61.pilot`, EA ha **accettato** una situazione per Baby Ariel,
Classe 1 (`EA: True`), ma circa 37 minuti Sim più tardi
`mhs61.check` indicava ancora **non presente sul lotto**.

Questo prova che la vecchia diagnostica non distingue
l'accettazione di una richiesta dall'effettiva creazione
e mantenimento della situazione e dall'apparizione del Sim.
Non prova ancora che il problema sia la capienza, il bouncer,
un filtro o un errore di spawn.

## Cosa aggiunge M99

- La coppia package/script `MHS_M99_TRACCIA_INVITO_MAC_TEST`
  conserva i **63 record del precedente pacchetto M94**.
- Il codice M61 normale è mantenuto intatto per la build M94.
  Solo la M99 include un `mhs61_pilot_command.py` aggiornato
  e il nuovo `mhs99_situation_trace.py`.
- `mhs61.pilot`: ancora **un solo tentativo per giorno/lotto**,
  richiede le guardie scolastiche e un Sim iscritto idoneo,
  registra ora l'ID numerico della situazione EA restituita
  da `SituationManager.create_situation`.
- Dopo la richiesta, un allarme di **sola osservazione** ogni
  5 minuti Sim (massimo 60 minuti) salva in automatico
  `MHS_M99_INVITO_STUDENTE_TRACE.json` in
  `Documents/Electronic Arts/The Sims 4/MY_HIGH_SCHOOL_M25_TEST_DATA/`.
- `mhs61.check`: come prima, verifica se il Sim è presente.
- **`mhs61.trace`**: verifica su richiesta il nome e lo stato,
  e aggiorna il report.
- Il report distingue, quando le API EA disponibili lo
  consentono: ID della situazione, situazione ancora esistente
  o non trovata, Sim fisicamente presente, lista dei
  partecipanti, e appartenenza del Sim a **quella specifica
  situazione**. Valori UNKNOWN non vengono spacciati per errori.

## Come provare su Mac (copia salvataggio)

1. Chiudere il gioco e utilizzare una copia del salvataggio.
2. Rimuovere **entrambi** i file M94 dalla cartella Mods;
   mettere solo i due file M99 nel percorso Mods. Non installare
   M94, M98 e M99 insieme.
3. Avviare The Sims 4, accompagnare Rosario, Sandro e Sofia
   al liceo in un nuovo giorno scolastico, con MHS attiva.
4. Con la console `Control + Maiusc + C`, eseguire UNA VOLTA
   `mhs61.pilot` durante le lezioni.
5. Lasciare scorrere 30–60 minuti Sim. Facoltativamente
   eseguire `mhs61.trace`.
6. Inviare `MHS_M99_INVITO_STUDENTE_TRACE.json`.
   Non serve ripetere la prova più volte nello stesso giorno.

**Non è possibile ricostruire retroattivamente l'ID della
situazione della vecchia prova M94**, perché allora il comando
registrava soltanto il nome scelto e un booleano EA=True.

## Che cosa NON è risolto

M99 non aumenta la capienza, non modifica il calendario,
non sostituisce i 7 NPC extra e non impone ancora 13 presenze.
Serve a scoprire in quale fase fallisce una richiesta esplicita:
- situazione EA mancante: richiesta non più mantenuta;
- situazione presente + Sim assente: il motore EA non ha
  ancora materializzato quel Sim;
- Sim presente ma senza appartenenza verificata:
  non possiamo dichiarare che sia a scuola grazie a MHS.

Qualsiasi scelta di soluzione definitiva (gestione bouncer,
restrizioni di capacità, sostituzione pre-spawn di tutti
gli NPC) deve seguire a queste osservazioni.
