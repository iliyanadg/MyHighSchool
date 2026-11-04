# Passo 78 — Analisi API EA create_situation e primo gate M58

## API consultate
Analizzate le implementazioni EA di riferimento in `sil3nt884/sims4_python`:
- `EA/simulation/situations/situation_manager.py`, metodo `SituationManager.create_situation(self, situation_type, guest_list=None, user_facing=True, ...)`.
- `EA/simulation/situations/situation_guest_list.py`, `SituationGuestList.guest_info_gen()`, `get_guest_infos_for_job(job_type)`, `get_invited_sim_ids()`, `clone()`, `SituationGuestInfo.construct_from_purpose(sim_id, job_type, invitation_purpose)`.

**Avvertenza:** questa decompilazione pubblica dimostra la forma della API, ma potrebbe non essere identica alla build Mac 1.129.39.1230. Non attivare hook live senza verificare la signature nella versione installata.

## Primo codice M58 disponibile ora
- `src/m58_selection/mhs58_base_plan.py`: piano pure Python per 6 situazioni base con un invito/job, distinguendo Sim giocabili, core, non idonei e i candidati oltre la capienza vaniglia.
- `tests/test_m58_base_plan.py`: test offline di capacità 6 e sicurezza.
- `src/m58_selection/mhs58_guest_policy.py`: gate pure Python, controlla una richiesta di situazione in base a GUID, job guest list e zona/scuola verificata; non consente interventi sui job core e staff, non sostituisce inviti EA già specifici, non tocca situazioni non liceali.
- `tests/test_m58_guest_policy.py`: verifica la decisione di sicurezza.

**Non è stata creata una build M58 giocabile** e non è presente un hook che riscriva le guest list. Il gate torna `candidate` solo come decisione di ammissibilità, non come prova di presenza.

## CI / limite
La GitHub Action `Offline source tests (not a game validation)` sul ramo feature ha prodotto ripetutamente `failure`; per i job consultati GitHub restituisce `steps:null`, `logs_url:null` e il recupero log `BlobNotFound`. Non dedurre da questi risultati quali test siano falliti. Non dichiarare test superati. Serve una nuova verifica offline riproducibile prima di qualunque compilazione M58.

## Prossimo intervento progettato
- Confrontare la versione corrente del `SituationManager` e del `WeeklySchedule` per il gioco dell'utente, idealmente con un bridge EA read-only (senza patch) che identifichi creazioni reali delle situazioni 277733, 298052, 298096 e job ospiti (SimID 0 vs espliciti).
- Separare il contatore delle situazioni effettivamente create dai job di fase e dalle persone presenti sul lotto; quindi solo dopo implementare selezione M58 con rollback.
- Conservare M57d, M54 main, rosters e il resto del gioco invariati.
