# M100 — Dal fallito invito aggiuntivo alla sostituzione di uno slot EA

## Evidenza M99 dal salvataggio 11

La prova esplicita con **Baby Ariel** ha creato situazione EA
`81653491254559472`, tuning `277733`, con la persona
`568605179472727670` realmente inserita nella **guest list**.
Il JSON M99 contiene **14 osservazioni**, tutte con:
- `situation_lookup=FOUND`, `situation_active=true`;
- `guest_sim_ids` contenente Baby Ariel;
- `on_lot=false`;
- `situation_member_ids=null` e `in_school_situation=null`.

Questo **NON** dimostra che il Bouncer abbia completato
l'assegnazione; dimostra che una richiesta esplicita in una
NUOVA situazione fuori dal calendario non fa necessariamente
apparire lo studente, anche se la situazione rimane attiva.

I report M58/M85 nello stesso salvataggio mostrano 16 iscritti
(8+8), quattro presenti in situazioni EA, sette altri adolescenti
non iscritti. Tre iscritti sono i giocabili Rosario, Sandro, Sofia.
Quindi non trattare tutti e quattro come successi della mod.

## Scelta di sviluppo

**Non aggiungere ulteriori situazioni come `mhs61.pilot`.**
Una situazione aggiuntiva può trovarsi senza slot Bouncer,
o con un Sim non idoneo ai filtri, anche dopo `EA: True`.
Il report non distingue ancora queste possibili cause.

La M100 usa **solo una situazione Base original EA 277733**,
quando il calendario la crea con guest list vuota:
1. Verificare lotto liceale, salvataggio, giorno, MY HIGH SCHOOL.
2. Leggere le due classi effettive, 8 iscritti univoci ciascuna,
   includendo i giocabili nei 16 totali.
3. Escludere giocabili e Sim già presenti sul lotto.
4. Ottenere dall'API EA il RISULTATO VERIFICATO del vero
   SimFilter scolastico **280516**, non dedurlo dall'età.
5. Scegliere un ID in quella intersezione, non per forza il
   primo nel registro (Baby Ariel potrebbe non essere idonea).
6. Sostituire la lista vuota durante **la stessa** chiamata
   EA `create_situation` tramite M88/M89, una sola volta nel
   giorno, senza una nuova situazione.
7. Conservare il report del tentativo e verificare nel gioco
   che EA lo abbia istanziato; se non accade, non attivare
   sostituzioni per gli altri dodici NPC.

## Stato nel repository

`src/m100_precreate/mhs100_one_slot_policy.py` e
`tests/test_m100_one_slot_policy.py` implementano soltanto
il contratto puro di selezione preventiva e i test. **Non
sono installati dalla M99 e non sono una release Mac.**
Mancano l'aggancio runtime al vero calendario del liceo,
la raccolta di veri risultati EA SimFilter 280516 e
un test nel gioco. Mai affermare che 16 presenze o
la capienza delle due aule siano state risolte.

La M99 già installata va conservata fino all'esistenza
di una nuova build verificata. Nessuna nuova prova
identica con `mhs61.pilot` serve a questa fase.
