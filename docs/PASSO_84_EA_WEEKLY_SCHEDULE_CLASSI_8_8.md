# Passo 84 — EA WeeklyScheduleSituationData: selezione Sim e capienza classe

## Evidenza originale già disponibile

Riletta la sorgente EA `weekly_schedule_zone_director.py` già caricata nella
Library durante i test della versione Mac 1.129.39.1230.

La classe `WeeklyScheduleSituationData` dichiara:
- `job_assignments`: riferimenti ai SituationJob da riempire, test sui Sim
  candidati e intervallo `sim_count` con min/max;
- `upper_bound_count_modifiers`: sottraggono dal massimo i Sim già
  assegnati a specifiche combinazioni situazione/job nello stesso periodo;
- un processo **in due passate** descritto dal codice: prima riempie i
  posti minimi usando i Sim istanziati che superano i test; successivamente
  prova a riempire fino al massimo. `try_start` riceve anche
  `sims`, `additional_sim_ids`, `situation_job_count`.
- I check relativi ai posti minimi e upper bound possono impedire
  l'avvio di una fase se non sono soddisfatti. Non attribuire tutte le
  aule vuote a un filtro: occorre preservare la coerenza min/max e gli
  idonei disponibili.

La **differenza essenziale** rispetto al primo tentativo M57/M60:
la selezione dei Sim a monte, il loro effettivo arrivo sul lotto e la
successiva assegnazione ai job delle fasi EA sono operazioni separate.
Forzare un elenco di ID sul `SimFilterService` non assicura che quei
Sim siano istanziati/idonei quando la classe viene costruita; la
build di isolamento M58 ha ripristinato gli studenti casuali seduti
alle 10:00.

## Altri XML EA originali già verificati

- `situation_HighSchool_Active_NPC_Base_Student` (277733):
  situazione `CustomStatesSituation`, job default `277894`,
  role state `289897`, duration `660`, max participants `20`.
  **max_participants=20 non è il numero di inviti**: non dimostra
  la capacità di chiamare 16 iscritti.
- `job_HighSchool_Active_Base_NPC_Student` (277894):
  filtro `280516`, più varie regole di outfit.
- `filter_HighSchool_Active_Student` (280516):
  controlli di blacklist per Sim speciali, carriera liceale `9541`,
  ghost/hidden/famiglie e scoring del tratto classe `293779`.
  **Non equivale al controllo 'età adolescente'**.
- Da M82 More Students: override di `WeeklyScheduleDay` e dei
  `WeeklyScheduleSituationData` delle due lezioni, ma non prova della
  compatibilità con questa patch. Non installare quegli override in MHS.

## Matrice di verifica M84

| Passaggio | Evidenza | Mancante per soluzione completa |
| --- | --- | --- |
| Registro C1=8 C2=8 | MHS, verificato in gioco | Nessuno per la persistenza |
| Filtri EA attuali | XML 280516/277894 | Eligibility vera di ogni Sim nel save |
| Creazione Base Student | XML 277733, diagnostica M58 | Numero reale di richieste, timing e identità |
| Partecipazione alla classe | Sorgente WeeklyScheduleSituationData | Mapping esatto di C1/C2 ai job fase del giorno |
| Limiti gruppi | Tuning storici More Students 18/24/40 | XML EA attuali originali di tutte le fasi |
| Lezioni alle 10:00 | M58 isolamento, verifica utente | Conservare, controllare 14:00 e successivi |
| Personale | Registro MHS | Inserimento nei job EA reali |

## Decisione di ingegneria

1. Manteniamo la build [M58 isolamento](https://github.com/iliyanadg/MyHighSchool/actions/runs/41257486408) come riferimento senza regressioni.
2. **Non** produrre ora un override vecchio di 277657/279958: prima occorre
   confronto sui tuning EA correnti delle fasi 293642/293644,
   304561/304563, 297773, 304570.
3. Separare esplicitamente il piano di spawn/roster, la capacità/occupazione
   delle situazioni Base Student e il routing verso le due aule.
4. Gli `upper_bound_count_modifiers` devono essere inclusi nell'audit:
   se già occupati, i posti possono diminuire anche quando il limite
   massimo appare sufficientemente alto.
5. Un futuro intervento MHS sui Sim va eseguito con fallback, senza nuove
   situazioni additive duplicate, e validato per l'effettiva presenza
   alle 10:00 e alle 14:00, non per i soli contatori di richieste.

**Stato**: studio delle API EA concluso per lo scheduling; tuning originali
delle fasi da recuperare/verificare. Nessuna build M84 installabile.
