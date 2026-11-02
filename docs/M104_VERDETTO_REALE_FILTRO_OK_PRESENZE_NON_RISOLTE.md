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
