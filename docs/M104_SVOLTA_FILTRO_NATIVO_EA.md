# M104 — Cambio di architettura: lasciare a EA le convocazioni

## Decisione presa dopo M99–M102

Due approcci hanno fallito nel gioco:
- M99 ha creato una situazione scolastica **aggiuntiva** con Baby Ariel
  nella guest list, senza farla arrivare.
- M101d/M102 hanno modificato **la guest list di una situazione
  originale EA** per Rahul Chopra. 12 dei 13 NPC iscritti hanno
  superato il filtro EA, ma Rahul non è stato materializzato neppure
  quando la situazione rimaneva attiva.

Il secondo report dimostra che la selezione del candidato e l'invito
sono corretti; **non dimostra** che il Bouncer abbia assegnato un Sim
alla situazione. M102 ha trovato 40 bucket (liste) di richieste
Bouncer, **non 40 studenti**. Un'ulteriore diagnostica passiva
M103 è stata avviata ma NON è inclusa in M104.

## Nuova ipotesi strutturale

Gli inviti `SituationGuestList(invite_only=True)` bypassano o
interferiscono con la modalità con cui EA risolve normalmente il posto
di studente nel Bouncer. Non lo possiamo ancora affermare come causa.

Invece di aggiungere una situazione o sostituire la guest list, M104
intercetta **una sola** chiamata EA originale
`SimFilterService.submit_matching_filter` eseguita dal Bouncer
per il filtro **Base Student 280516**. Sostituisce solamente
`sim_constraints` con gli ID dei 13 NPC iscritti (meno quelli già
sul lotto) e disattiva le opzioni di fallback casuale di QUELLA
chiamata. EA mantiene la propria guest list, SituationManager,
scheduling, assegnazione Bouncer, regole di spawn e gli altri
argomenti originali.

La M57 originale aveva un intercettore di filtri lasciato in
isolamento (`MHS_EA_FILTER_CONSTRAINTS_ENABLED=False`). M104 usa
un wrapper separato, opt-in, che **non abilita** gli override
M57 per personale, club, rivali o altri ruoli. L'applicazione è
limitata a:
- salvataggio e giorno scolastico verificati;
- viaggio da casa verso un altro lotto;
- una vera chiamata del Bouncer durante lo spawn;
- filtro Base Student 280516 e metodo **matching**, non altri
  filtri o `submit_filter` generici;
- esattamente 2 classi di 8 studenti, 3 giocabili e 13 NPC
  iscritti e idonei come adolescenti umani.

Se le condizioni non sono dimostrate, EA non viene modificata.
Il comando `mhs104.off` disarma il prototipo.

## Criterio del prossimo UNICO test

Solo dopo compilazione Python 3.7 Mac verificata, su copia
del salvataggio, usare M104 IN ALTERNATIVA alla M102 e
precedenti. Prima del viaggio a liceo:
`mhs104.arm`. Al liceo:
`mhs104.check` e `Consulta presenze automatiche`.

Report: `MY_HIGH_SCHOOL_M25_TEST_DATA/MHS_M104_NATIVO_FILTRO_EA.json`
e `MHS_M85_PRESENZE_RUOLI_EA.json`.

**Pass:** report conferma filtro nativo limitato E almeno
un NPC iscritto è realmente nel lotto/in una situazione EA
(non basta essere nella guest list).

**Fail:** non è osservato nessun intervento nel filtro
originale o nessun NPC selezionato entra. In quel caso
FERMARSI: riprodurre il codice di selezione Bouncer/EA e
valutare altre tecniche quali tuning SimFilter o ruoli
scolastici, non proporre altre dieci versioni diagnostiche.

La presenza di un NPC NON dimostra ancora 16/16 studenti,
8 per classe o una terza classe. Questi sono passaggi
successivi, subordinati al successo del controllo nativo
della selezione e alla capacità reale del lotto.

## Sorgenti
- `src/m104_native/mhs104_native_policy.py`
- `src/m104_native/mhs104_native_school_filter.py`
- `tooling/build_mhs104_native_filter.py`
- `tests/test_m104_native_filter_policy.py`
- `tests/test_mhs104_native_release.py`
