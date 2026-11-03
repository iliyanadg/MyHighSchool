# M110 — seconda prova completa nel gioco, 3 novembre 2026

## Risultato e sicurezza

La giocatrice ha eseguito `mhs110.start` a casa, verificato con
`mhs110.status` alle 07:00 (`OBSERVING`, 0 eventi), accompagnato i
giocabili al liceo e verificato alle 08:11 (`OBSERVING`, 90 eventi).
Alle 15:02, con il gioco in pausa e ancora sul lotto scolastico, ha
verificato `OBSERVING`, 356 eventi su 356 conservati, quindi ha eseguito
`mhs110.stop`: la console ha confermato il ripristino degli originali.

File originale fornito: `MHS_M110_NATIVE_EA_CALL_TRACE(2).json`.

Campi reali del report:
- `status = INACTIVE`, `errors = []`
- `temporary_runtime_wrappers_active = false`
- `runtime_descriptors_temporarily_modified = false`
- `event_total = 356`, `events_kept = 356`
- `event_details_truncated = false` (limite 1024)
- numero di chiamate **in ingresso**:
  `create_situation = 83`, `try_start = 87`,
  `get_long_term_situation_count = 8`.
- 83 ritorni `create_situation` classificati `POSITIVE_INT`;
  59 ritorni `try_start` classificati `POSITIVE_INT` e 28 `NONE`.
  Questi sono risultati di funzioni, **NON** prova di effettiva
  presenza o assegnazione dei Sim.

## Prova diretta del conteggio calendario

`WeeklyScheduleDay.get_long_term_situation_count` ha restituito
esattamente le seguenti coppie su **due** calendari EA:

| calendario EA | situation GUID | ritorno EA |
|---|---|---|
| 277657 | 277733 (Base) | (3, 3) |
| 277657 | 298052 (Core) | (1, 1) |
| 277657 | 298096 | (1, 1) |
| 277657 | 278011 | (1, 1) |
| 279958 | 277733 (Base) | (3, 3) |
| 279958 | 298052 (Core) | (1, 1) |
| 279958 | 298096 | (1, 1) |
| 279958 | 278011 | (1, 1) |

In particolare, **Base = (3,3)** è ora una osservazione REALE, non
un'ipotesi. Il prototipo `mhs108_native_base_count` imposta
`EA_TUNED_BASE_COUNT=6` e richiede una deduzione giocabili 0..3
*indipendentemente verificata*. Un ritorno `(3,3)` da solo NON dimostra
che si debba impostare `ea_original_playable_adjustment=3`. Non
bypassare quella protezione con un flag `True` fittizio.

## Fasi lezioni EA (data GUID -> situation GUID)

Ogni coppia sotto è stata vista **due volte**, ma il report non contiene
timestamp in-game per evento; quindi non etichettare i due tentativi come
due lezioni distinte senza correlazione al tempo del gioco.

| data GUID | situation GUID correlata | ritorni `try_start` | osservazione |
|---|---|---|---|
| 293642 | 293815 | 2 POSITIVE_INT | preparazione Classe 1 WithTrait |
| 293644 | 304701 | 2 NONE | preparazione Classe 1 NoTrait, nessuna create corrispondente |
| 297773 | 297774 | 2 POSITIVE_INT | preparazione Classe 2 |
| 304563 | 304565 | 2 POSITIVE_INT | lezione Classe 1 WithTrait |
| 304561 | 304703 | 2 NONE | lezione Classe 1 NoTrait, nessuna create corrispondente |
| 304570 | 304567 | 2 POSITIVE_INT | lezione Classe 2 |

Sono osservate 3 chiamate `create_situation(277733)` e 1 chiamata
`create_situation(298052)`, entrambe con ritorno `POSITIVE_INT`.
Il conteggio `get_long_term_situation_count` è effettuato due volte
(su due schedule GUID), ma le singole creazioni Base non equivalgono
automaticamente a slot/personaggi assegnati.

## Cosa abbiamo DIMOSTRATO e cosa no

Confermato:
- `mhs110.start` rimane attivo attraversando il cambio di lotto;
- il codice di tracciamento raccoglie l'intera sequenza fino alle 15:02
  senza overflow;
- le chiamate EA per preparazione e lezioni di Classe 1 e Classe 2
  passano effettivamente per `try_start` e `create_situation`;
- `mhs110.stop` ha ripristinato i descrittori originali senza errori.

NON confermato:
- gli inviti siano stati accettati/assegnati dal Bouncer;
- siano presenti 16 iscritti esatti, 8 per ogni classe e zero estranei;
- la presenza di 16 adolescenti sui lotti e i loro job EA;
- lezione seduta o routing in due aule stabili;
- l'assenza di hook di terzi (solo una diagnostica separata controllava
  marker MHS noti).

## Prossimo intervento: sviluppo, non ripetizione della M110

Usare questi **GUID e conteggi verificati** come fixtures di regressione
nel controller M108/M109. Il prossimo segnale utile è un'osservazione
POST-BOUNCER con `SituationManager.get` e
`BaseSituation.all_sims_in_job_gen` per le situazioni reali e i job
originali: `mhs108_post_bouncer_audit` e
`mhs108_16_student_reconciliation` già definiscono i controlli,
ma mancano ancora un provider live e la barriera della fase Bouncer.

Non richiedere una TERZA giornata M110. Non dichiarare la mod 16/16
funzionante da un log di creazione situazioni.
