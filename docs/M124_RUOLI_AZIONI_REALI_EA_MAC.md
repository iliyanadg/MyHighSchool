# M124 — Role State e azioni EA per tutti i 16 iscritti (Mac)

## Problema reale, 3 novembre 2026

La M123 ha dato in gioco `EA_base_present=8/8`,
`EA_core_present=5/5`, `lezioni_proiettate=2/2`,
`lezione_job=C1:8/8,extra=0|C2:8/8,extra=0`
e `mhs123.classi`: `EA_classe1=8/8`,
`EA_classe2=8/8`, `giocabili_istanziati=3/3`,
`iscritti_istanziati=16/16`, `classe_sbagliata=0`,
`extra_nelle_lezioni=0`.

**Ma la verifica fisica alle 10:32 è diversa:**
Classe 1 (Giuliano Papanice) 6 studenti, Classe 2
(Angelo Morlind) 6 studenti; Raul Chopra e Nayon Specter
erano nel corridoio, Lady Sofia Brantes e Lutz Lopez al
computer al piano inferiore. Quindi i job EA sono giusti,
ma la partecipazione fisica/interazione no.

## Nuova lettura M124

La M124 eredita **integralmente il controller della M123**
per inviti Base/Core, liste di lezione e filtro EA originale.
Non riscrive né elimina il registro.

Il nuovo `mhs124_lesson_action_readback.py` legge
per ogni adolescente iscritto, **in sola lettura**:
- classe 1 o 2 prevista dal registro MHS;
- le situazioni EA di lezione originali realmente attribuite;
- il `SituationJob` EA assegnato;
- `BaseSituation.get_current_role_state_for_sim(sim)`;
- `BaseSituation.get_current_role_state_instance_for_sim(sim)`;
- `sim.queue.running`, se disponibile;
- l'eventuale coda `sim.queue._queue` se esposta come lista
  o tupla, al massimo cinque elementi;
- problemi di istanziazione / API mancanti, senza dedurre
  che il Sim sia seduto o assegnato all'aula fisica.

Queste API `get_current_role_state_for_sim` e
`get_current_role_state_instance_for_sim` provengono
dal file EA originale `base_situation.py` che l'utente
aveva già fornito. La lettura dei job usa gli stessi
GUID reali e gli stessi controlli della M122.

## Come provare su Mac

1. Fare una COPIA del salvataggio di test.
   Rimuovere M123 e tutte le precedenti beta EA da Mods.
   Lasciare la mod stabile del registro e installare solo
   `MHS_M124_RUOLI_AZIONI_MAC_BETA.ts4script` come beta.
2. Da casa prima della scuola: `mhs124.arm`.
3. Al liceo alle 10:30: `mhs124.classi`, poi
   `mhs124.azioni`. Questo mostra il numero di
   Sim con job di lezione corretto e le azioni correnti,
   senza fingere di sapere chi è seduto.
4. Digitare `mhs124.dettagli`. Produce:
   `Documents/Electronic Arts/The Sims 4/
   MY_HIGH_SCHOOL_M25_TEST_DATA/
   MHS_M124_LEZIONI_RUOLI_AZIONI.json`
5. Inviare il JSON (non serve una nuova prova per persona).
   Potremo correlare i Sim ai ruoli originali e alle azioni
   che li mantengono nei corridoi o ai computer.
6. Terminare la prova con `mhs124.stop` e chiudere
   il gioco; non salvare modifiche di questo test sul
   salvataggio principale.

## Limiti

M124 **NON annulla azioni, NON sposta Sim, NON cambia
posti a sedere e NON applica forzature di autonomia**.
Il codice originale EA mostra i role states, ma finché
non abbiamo i valori effettivi dei role/interaction ID
di quei Sim in partita, non sappiamo quale interazione
EA sia corretto riavviare. Forzare un affordance generico
o teletrasportare il Sim rischierebbe di rovinare le
lezioni invece di correggerle.

Test automatici offline Python 3.7 ≠ prova nel gioco.
Il ramo `main` stabile è intatto.
