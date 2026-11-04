# M96 — Contare esattamente le richieste studente EA 8+8, non quelle casuali

Origine: prova delle 10:03 del 1/11/2026, dove 16 iscritti al registro
hanno prodotto solo 3 iscritti nel liceo e 8 adolescenti EA estranei.
Dalle 3 chiamate Base 277733 di M58 non si deducono 16 inviti;
gli altri teen venivano assegnati da EA, non dal registro MHS.

## Punto di intervento confermato nel Python originale EA

Il file `weekly_schedule_zone_director.py` fornito dall'utente
definisce `WeeklyScheduleDay.get_long_term_situation_count`, che
legge il minimo e il massimo dal tuning e sottrae i Sim giocabili
previsti dai modificatori. `WeeklyScheduleDay.start_long_term_situation`
esegue `random.random.randint(min_count,max_count)`, creando a
ogni iterazione una `SituationGuestList` vuota.

`src/m96_scheduler/mhs96_exact_school_count.py` contiene una patch
**opt-in non installata** del metodo classmethod, solo per i due
calendari liceali EA `277657` e `279958` e la situazione Base
`277733`. Con il piano completo produce `(N,N)`, dove
`N=16 - giocabili - assegnati core`; nessun ricalcolo casuale e
nessuna seconda sottrazione dei Sim giocabili.

## Condizioni inderogabili del progetto

- 8 iscritti distinti C1 e 8 iscritti distinti C2.
- Membri di `core`, `playable` e `normal_npcs` disgiunti
  e insieme uguali agli stessi 16 del registro.
- `M92 full_cohort_plan` completato e filtri EA verificati.
- **I ruoli speciali devono essere prenotati e bloccati PRIMA
  delle prime convocazioni EA.** Contare gli occupanti già spawnati
  è troppo tardi: la situazione CoreClassNPCs può iniziare dopo
  il conteggio Base.
- Provider di runtime verifica zona liceo, save-slot, giorno, studenti
  idonei, ruoli e disponibilità fisica di posti; non utilizzare
  il solo GUID del filtro come prova di eleggibilità.
- Gli altri calendari/situazioni restano EA originali.
- M89/M90 deve evitare che una diciassettesima richiesta Base
  senza guest crei un compagno non iscritto.

L'iniezione del calendario, la prenotazione anticipata dei
cinque ruoli Core e la capienza reale del lotto **non sono
ancora implementate in una build di gioco**. M96 al momento
è codice e test offline: non consegnare questo file Python
come mod installabile e non sostituire M94.

## Test

`python -m unittest tests.test_m96_exact_school_count
tests.test_m90_m89_bridge tests.test_m89_precreate_hook
tests.test_m92_atomic_16 -v`

Questi test non sono una simulazione del motore del gioco:
verificano i contratti di ingresso e il preservare il
comportamento EA quando non c'è un piano verificato.
