# M129 — Nuove estrazioni EA: sedute, lavagna, giocabili

Fonte: archivio originale Sims 4 Studio fornito dall'utente, `ESTRAZIONI AGGIUNTIVE.zip`. Sono stati esaminati 4 XML.

## super_HighSchool_Active_Whiteboard_Attend_Art (293197)
- `_constraints`: `cone` con `min_radius=2`, `max_radius=15`, `angle=100`; `facing=180`; linea di vista temporanea `max_line_of_sight_radius=15`.
- `posture_preferences`: `prefer_surface=True`, con costi `SitOnGround=100`, `Kneel=30`, `Stand=40`, `CrossLegged=29`.
- `posture_target_preference`: SURFACE_DESK 50; SEATING_DESK 30; DINING_TABLE 15; SEATING_DINING 10; SEATING_BED 5; SOFA 5; altri. **Sono preferenze, non vincoli di seduta al banco scolastico**.
- `super_affordance_compatibility` include `super_HighSchool_Active_CreateBook_Class` (276782) e `super_HighSchool_Active_UseBook_Class` (276784). Da analizzare per stabilire il flusso di seduta.

## super_HighSchool_Active_Whiteboard_Class_Start (276774)
- `_static_commodities`: `staticCommodity_HighSchool_Active_NPC_GoToObject` (275940).
- `basic_liabilities` include `critical_priority`. Non significa che questo avvii prima delle 10.
- `outcome` test_based: le continuazioni comprendono Attend_Art (293197), Attend_Business (293198), Attend_ComputerScience (293200), Attend_ForeignLanguage (293199), Attend_LanguageArts (293196), Attend_Math (293193), Attend_Science (293194), Attend_SocialStudies (293195), AttendClass_ExamPrep (296636); su exam day `AttendExam` (276671).
- **Non risulta in questi dati un automatismo che assegni 8 posti distinti agli 8 SimID della classe MHS.**

## staticCommodity_HighSchool_Active_Phase_Class (276316)
- Tuning `StaticCommodity` quasi vuoto, solo `ad_data=4`. Non espone nel proprio XML un'ora di convocazione, target di banco, posto riservato o istruzione di routing. Non attribuirgli poteri che il tuning non mostra.

## role_HighSchool_Active_Player_Phases_AttendClass (278610)
- Buffs: `Buff_Role_Appropriateness_NoCallToMeal` (101052), `buff_Route_UsePhone` (273647), `buff_Role_Highschool_Active_Player_AttendClass` (276710).
- `_off_lot_autonomy_buff`: `buff_offLotAutonomyMod_OnLotOnly` (38292).
- Il ruolo giocabile non contiene, nel tuning qui letto, una regola diretta di banco o di aula. Per Sandro e Sofia occorre ispezionare il buff **276710**; non applicare l'interazione NPC ai giocabili.

## Stato e conseguenze
M127 ha evidenziato alle 9:40 e alle 9:55 studenti Classe 2 con target lavagna di Classe 1; M128 audit live ha trovato 9 tratti EA incoerenti, ma il primo comando di allineamento si è fermato senza modifiche; revisione M128 compilata con fallback mutator SimInfo, ancora da validare in partita.

### Prossime azioni tecniche
1. Verificare `mhs128.verifica` -> `mhs128.allinea` -> `mhs128.verifica` sulla copia di salvataggio prima della preparazione.
2. Se la disomogeneità delle lavagne persiste dopo la correzione tratti, ispezionare gli *stati* EA effettivi delle lavagne.
3. Studiare tuning `super_HighSchool_Active_CreateBook_Class` (276782) e `super_HighSchool_Active_UseBook_Class` (276784); testare come EA seleziona postura e superficie.
4. Studiare tuning `buff_Role_Highschool_Active_Player_AttendClass` (276710) per i giocabili.
5. Non dichiarare seduta 8+8 alle 10 finché non sia osservata realmente. No modifica ai cicli EA né sostituzione del roster.
