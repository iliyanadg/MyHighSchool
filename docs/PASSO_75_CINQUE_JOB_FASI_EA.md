# Passo 75 — I cinque Situation Job di fase EA non invitano nuovi Sim (31/10/2026)

## Documentazione della fonte
L'utente ha esportato con Sims 4 Studio dalla propria installazione The Sims 4 per Mac (GameVersion 1.129.39.1230) **cinque SituationJobTuning e cinque SimData**:
- `job_HighSchool_Active_NPC_Phases_Student1` **277919**
- `job_HighSchool_Active_NPC_Phases_Student2` **280777**
- `job_HighSchool_Active_NPC_Phases_Student3` **297169**
- `job_HighSchool_Active_NPC_Phases_Teacher1` **277918**
- `job_HighSchool_Active_NPC_Phases_Teacher2` **297170**

Ogni XML dei cinque job contiene precisamente:
```xml
<T n="filter">15940<!--sim_filter_blank_do_not_touch--></T>
<U n="sim_auto_invite">
  <T n="lower_bound">0</T>
  <T n="upper_bound">0</T>
</U>
```

Condividono inoltre `goal_scoring=10`, cinque commodity in intervallo 75–100 (bladder, energy, fun, hunger, hygiene), i tre filtri di provenienza geografica (`260612`, `290171`, `203033`) e filtro di modificatore zona no ghosts `380099`. I cinque SimData hanno `recommended_objects` vuoto e non introducono informazioni aggiuntive di selezione.

## Interpretazione limitata a quanto prova il tuning
- **Fatto:** Nessuno di questi cinque job di fase chiede direttamente nuovi NPC attraverso `sim_auto_invite` o un filtro selettivo specifico (usa filtro vuoto).
- **Ipotesi da verificare:** le situazioni EA della giornata passano Sim già istanziati/assegnati ai job di fase, anziché creare nuovi compagni durante il cambio di fase.
- **Non dimostrato:** che `Student3` sia una terza aula; potrebbe distinguere un gruppo o una fase interna, ma per capirlo serve il tuning della situazione che assegna questi job.
- **Implicazione per il controller:** intervenire su questi cinque `filter=15940` non permette una selezione individuale affidabile; in particolare non modificare il filtro globale vuoto. I job iniziali nel passo 74 rimangono un meccanismo separato con auto-invite 1–1 e filtro specifico.

## Unica richiesta di analisi successiva
In Sims 4 Studio, Tools > Extract Tuning, cercare **`situation_HighSchool_Active_NPC_Phases`**. Se appare più di un risultato, chiedere **screenshot della lista prima di scaricare tutto**, poi selezionare i tuning `SituationTuning` che assegnano i job 277919, 280777, 297169, 277918, 297170. Lo scopo è capire la logica di assegnazione nelle fasi e in quali situazioni si collocano i gruppi.

Non cambiare M57d, non creare test build e non aggiungere tratti nascosti ai Sim prima dell'analisi dei riferimenti di situazione. Conservare i file del registro e test già funzionanti.
