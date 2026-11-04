# M122 — 13 NPC Base/Core + lettura delle due vere lezioni EA

## Punto di partenza verificato in partita Mac

Con M121 il 3 novembre 2026 alle 8:14 e alle 10:32:
- `EA_base_created=8/8` e `EA_base_present=8/8`;
- `EA_core_created=1/1` e `EA_core_present=5/5`;
- `count_override=1`, `native_count=(3,3)`, `filter=13`;
- `missing_base=none`, `missing_core_jobs=none`, `error=none`.

Questo attesta **13 NPC nei job scolastici EA Base/Core** ai due istanti.
Non attesta lezioni né studenti seduti in due aule.

## Cosa cambia nella M122

Il nuovo script `mhs122_thirteen_npc_plus_classes.py` contiene
**lo stesso controller di ammissione della M121**: tutti e 8 i Base,
i 5 ruoli Core scelti manualmente, filtro EA originale e rollback.

Aggiunge `mhs122.classi` e `mhs122.prepara`: chiamano il
lettore in sola lettura `mhs122_classroom_job_readback.py`.

Il lettore usa gli originali EA:
`SituationManager.get_situations_sim_is_in(sim)` e
`BaseSituation.get_current_job_for_sim(sim)`, confermati
nel lavoro M109/M111. Distingue le situazioni delle lezioni:

- Classe 1: WithTrait `304565`, NoTrait `304703`, job teen `277919`;
- Classe 2: `304567`, job teen `280777`;
- preparazione Classe 1 `293815`/`304701`,
  Classe 2 `297774`, job `277919`.

Confronta ogni job con il SimID iscritto nella Classe 1/2
del registro per-save, controlla i tre giocabili effettivamente
istanziati, indica mancanti e assegnazioni alla classe errata.
Controlla anche gli adolescenti NON iscritti che EA potrebbe
avere messo nelle stesse situazioni di lezione. Una fonte
EA incompleta non può dare un falso 8+8.

## Prova Mac (solo COPIA del salvataggio)

1. Chiudere The Sims 4 e rimuovere il file M121 da Mods.
   Non installare M121 e M122 insieme. Conservare la stabile MHS.
2. Dal workflow M122 scaricare
   `MHS_M122_THIRTEEN_NPC_PLUS_CLASSROOM_MAC_EXPERIMENTAL`.
   Estrarre il solo `MHS_M122_TREDICI_NPC_MAC_BETA.ts4script`
   nella cartella Mods.
3. A casa prima della scuola: `mhs122.arm`.
4. Al liceo dopo arrivo: `mhs122.status` (verifica 13 NPC).
5. Alle **10:30**, durante una lezione: `mhs122.classi`.
   Leggere `EA_classe1`, `EA_classe2`,
   `giocabili_istanziati`, `mancanti_C1/C2`,
   `classe_sbagliata`, `extra_nelle_lezioni` e `stato`.
6. Facoltativo alle 9:30 per la preparazione: `mhs122.prepara`.
7. Alla fine: `mhs122.stop` e riavviare prima di altre beta.

## Cosa NON dimostra

- Non cambia i job delle lezioni né sposta studenti nelle due aule.
- Due set EA corretti non sono una prova di seduta fisica ai banchi.
- Il controllo dell'istanza non dimostra le coordinate del Sim.
- Non prova continuità per l'intera giornata o il giorno seguente.

La M122 è una **beta integrata modificante** soltanto per la
parte ammissione M121; la parte lezioni è **sola lettura**,
necessaria per conoscere esattamente quali job EA intervenire
senza sacrificare i 13 NPC già funzionanti. `main` è intatto.
