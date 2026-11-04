# M104 — Verdetto nel gioco: filtro intercettato, presenze NON risolte

Data della prova: 2 novembre 2026, liceo di Copperdale, salvataggio 11.
Prova M104 con 16 iscritti (Classe 1 = 8, Classe 2 = 8), inclusi
i 3 adolescenti giocabili. La M104 è stata armata a casa e verificata
al liceo fra le 10:19 e le 10:26.

## Osservazioni effettive

File utente:
- `MHS_M104_NATIVO_FILTRO_EA(1).json`;
- `MHS_M85_PRESENZE_RUOLI_EA(5).json`;
- `MHS_M85_PRESENZE_RUOLI_EA(6).json`;
- `MHS_M58_SITUAZIONI_DIAGNOSTICA(10).json`;
- `MHS_M94_FILTRI_LICEO_EA(5).json`.

**Filtro:** `phase=NATIVE_EA_BASE_FILTER_CONSTRAINED`,
`matching_filter_guid=280516`, `allowed_count=13`.
La M104 ha alterato gli argomenti di UNA chiamata EA di
`submit_matching_filter`. Nessuna nuova situazione EA e nessun
`SituationGuestList` modificato. Questo è un successo
**del collegamento al filtro**, NON una prova di arrivo causato
dalla mod.

**Presenze effettive:**
- iscritti: 16;
- iscritti presenti sul lotto: **4/16**;
- iscritti nelle situazioni scolastiche EA: **4/16**;
- per classe: Classe 1 **1**, Classe 2 **3**;
- non iscritti nelle situazioni scolastiche EA: **7**;
- M104 osserva 1 NPC iscritto fisicamente presente, mentre gli altri
  3 presenti sono i giocabili; il report non prova che tale NPC sia
  stato selezionato dalla specifica richiesta intercettata;
- `seated_in_correct_class_verified=false`.

**Situazioni EA diagnosticate:** 3 chiamate della situazione
studenti 277733, 1 Core 298052, 1 personale 298096,
1 mensa 278011. I contatori non rappresentano partecipanti.
I filtri di sei lavori scolastici sono letti correttamente,
tutti con `auto_min=1` e `auto_max=1` per ciascun job
Base/Cheer/Chess/Football/Computer/Mean Sim. Questi metadati
da soli non provano la capacità di 16 partecipanti.
I contatori di M57 dicono `constraint_success=0` perché
l'intervento M104 è separato dal monitoraggio M57: NON usare
quel contatore per negare il successo dell'intercettazione.

## Verdetto

**M104 dimostra che una richiesta originale EA può essere
limitata ai nostri NPC. NON dimostra che un nuovo NPC arrivi
grazie alla modifica e NON migliora il risultato delle presenze
(ancora 4 iscritti e 7 extra).**

La strategia degli esperimenti con UN SOLO posto o invito
(M99, M101d, M102, M104) si ferma qui: non fornire alla
giocatrice nuove build di sola diagnostica o richiedere di
ripetere lo stesso giorno scolastico.

## Decisione architetturale successiva

Non passare da un unico filtro a una promessa di 13 NPC spawned
senza prima controllare le fonti EA native:
1. Ricostruire **tutte** le richieste/student jobs originali
   del giorno scolastico, non solo una Base matching call.
2. Verificare la capacità disponibile per studenti, gli
   eventuali limiti della zona e i job per le 2 lezioni.
3. Identificare come EA riempie i cinque ruoli speciali,
   dato che gli estranei spesso arrivano tramite filtri
   separati, e come sostituire i NON iscritti senza
   distruggere il calendario scolastico.
4. Usare l'esistente `M92 full_cohort_plan` come gate
   **atomico**: nessuna release 16/16 se gli slot
   originali, i ruoli, il tempo di lezione e la capienza
   non sono dimostrati.
5. Solo allora implementare un vero controller del roster
   per **tutti** i posti del liceo (non M104 ripetuta),
   con test separati prima della prova Mac nel gioco.

Nessuna prova odierna dimostra che 16 studenti esatti
possano rimanere presenti e divisi stabilmente 8+8:
trattarla come requisito ancora aperto, non come risultato.


## Decisione implementativa dopo audit EA del 2 novembre

Da `assets/ea_2026_11_01/277657.xml` e `279958.xml`, **il
numero vanilla di situazioni Base Student è 6–6 prima dei modificatori**
sugli studenti giocabili. Non equivale alla quantità finale di NPC.

Da `assets/ea_2026_11_01/304561.xml` e `304563.xml`, la prima
lezione ha un massimo normale di 6 studenti NPC, ulteriormente
riducibile da modificatori: occorre coordinare gli aggiornamenti
delle fasi al nuovo massimo di 8, non soltanto aumentare il
numero di situazioni base.

Gli incarichi Core class 298052 comprendono cinque ruoli per
studenti (cheer, chess, football, computer, mean) e due docenti.
I **cinque occupanti effettivi** NON sono provati dal tuning:
vanno scelti nel registro MHS, verificati con i rispettivi
filtri EA e vincolati prima dello spawn.

### Contratto preciso di una giornata con tre adolescenti giocabili

Quando e SOLO quando i cinque ruoli speciali sono realmente
prenotati a cinque iscritti distinti, il conteggio obiettivo è:

- 3 giocabili accompagnati = 3;
- 5 studenti scelti per ruoli speciali EA = 5;
- 8 altri NPC iscritti per Base Student = 8;
- **totale 16 iscritti, non 16 ulteriori situazioni Base**.

Se i cinque ruoli speciali non possono essere prenotati,
questa equazione non è garantita. In quel caso **bloccare
l'override**: non presupporre che il gioco assegni automaticamente
cinque iscritti ai ruoli.

Il modello `M92` già convalida l'intero set di 16; `M96`
già contiene la funzione `approved_base_count` (non attiva
nel gioco). I test integrati
`tests/test_full_16_school_day_contract.py` ora verificano
**insieme** i due componenti e il piano M97, impedendo di
autorizzare il conteggio 8 senza prova di riserva anticipata
dei cinque ruoli. La suite GitHub `m96_school_dispatcher_logic`
deve passare prima di qualunque nuovo runtime.

### Sviluppo restante, prima di qualsiasi ulteriore prova nel gioco

1. Collegare i cinque filtri Core EA alle cinque assegnazioni
   esplicite `MHS97_RuoliSpeciali_slot_<salvataggio>.json`
   **prima** dello spin-up; preservare i filtri EA quando
   l'assegnazione non è completa e lasciare MHS disattiva.
2. Attivare la quantità esatta di situazioni Base dal
   calendario EA, non da un comando tardivo, rispettando
   il piano atomico e i modificatori vanilla.
3. Allineare le due fasi di lezione 8/8 alle stesse identità,
   evitando di assegnare una persona a entrambi i job.
4. Verificare e adattare il vero limite di Sim istanziati
   sul lotto, conteggiando anche almeno 2 insegnanti,
   preside, bidello e mensa (**16 studenti + 5
   membri del personale = almeno 21 Sim**, senza
   ospiti ulteriori). Il limite esatto della versione
   Mac e di eventuali altre mod richiede prova;
   non inferirlo dal `max_participants=20` delle
   singole situazioni.
5. Nessuna nuova build installabile finché la soluzione
   integrata non supera test di selezione/staff/fasi,
   verifica del budget fisico e controllo di rollback.

**Stato reale:** completo test di CONTRATTO statico, non
controller EA installato. Non chiedere alla giocatrice
nuove prove M99–M104 e non dichiarare risolto 16/16.
