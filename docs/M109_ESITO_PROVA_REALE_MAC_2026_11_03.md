# M109 — Riscontro reale dal gioco Mac, 3 novembre 2026

## Prova eseguita (non simulata)
L'utente ha installato **solo** il piccolo `MHS_M109_NATIVE_METHODS_READ_ONLY.ts4script`,
lanciato `mhs109.probe` in The Sims 4 e fornito il JSON prodotto dal
gioco `MHS_M109_NATIVE_METHODS_READ_ONLY.json`.

L'output della console e il JSON concordano:

- `method_count_available = 15` su `15`
- `hook_target_count_located_unverified = 6` su `6`
- `native_modules`: tutti i 6 moduli `EA_CLASS_LOADED`
- `problems = []`
- `known_mhs_hook_marker_count = 0` (SOLO marker riconosciuti dalla sonda)
- `status = METHOD_SHAPES_AVAILABLE_UNVERIFIED`

| Stage futuro M109 | Owner dichiarato nel gioco |
|---|---|
| `native_base_count` | `venues.weekly_schedule_zone_director.WeeklyScheduleDay` |
| `native_precreate` | `situations.situation_manager.SituationManager` |
| `school_filter_scope` | `situations.bouncer.bouncer_request.BouncerRequest` (`__init__` + `get_additional_filter_terms`, STESSO owner) |
| `no_show_guard` | `situations.bouncer.bouncer_request.BouncerRequest` |
| `unified_lessons` | `venues.weekly_schedule_zone_director.WeeklyScheduleSituationData` |
| `post_bouncer_observer` | `situations.situation_manager.SituationManager` |

Dettaglio verificato: `SituationManager.get` è dichiarato in
`indexed_manager.IndexedManager`. Serve alla lettura delle situazioni,
**non** è uno dei sei target da modificare.

## Cosa autorizza realmente questa prova

- Conferma che, in quella sessione e versione Mac del gioco, esistono le
  classi, i 15 metodi e i descrittori cercati. Non è un test sintetico.
- Non certifica l'origine della singola chiamata del calendario EA,
  l'ordine inviti Base/Core, l'effettiva accettazione Bouncer, i limiti NPC,
  i job reali, il tempo delle lezioni, l'aula, i posti a sedere o 16/16.
- `0 marker MHS` NON certifica l'assenza di altri controller di terze parti.
- `activation_authorized_by_game = false`,
  `runtime_hook_install_authorized = false`,
  `ea_live_provenance_verified = false`,
  `school_situation_assignment_verified = false`,
  `full_16_student_attendance_verified = false`.
- Non confondere `STAGE_TARGET_LOCATED_NOT_LIVE_VERIFIED` con
  `STAGE_INSTALLED` o `16_STUDENTS_VERIFIED`.

## Integrazione attuata dopo il JSON

Aggiunto `src/m109_activation/mhs109_live_owner_bridge.py`, che:
1. riceve oggetti classe Python dalla futura integrazione EA, NON nomi
   copiati dal JSON;
2. verifica il contratto dei 15 metodi e la coerenza dei sei stage;
3. risolve ciascuno dei sei owner Python reali lungo `__mro__`;
4. blocca owner cambiato, mancante, ereditato da una classe imprevista,
   diviso tra due classi o marcato da un hook MHS già noto;
5. restituisce esclusivamente riferimenti ai tipi Python, senza installare
   wrapper e senza impostare alcun flag di autorizzazione.

Questo collega la mappatura osservata al futuro
`M109NativeStage`, evitando di intervenire sulla classe sbagliata.
Non ha un entry point nel gioco, non è incluso nella diagnostica e non
è una nuova beta da installare.

Test:
`tests/test_m109_live_owner_bridge.py`, eseguito nel job Python 3.7
`m109_readonly_mac_probe` e nel normale `unittest discover`.

## Passo necessario per ottenere davvero le due classi da 8

Il prossimo adattatore runtime dovrà osservare **l'origine e la sequenza
effettiva dei callback EA durante una giornata scolastica** e collegare
quella prova all'identità del save/giorno/lotto. Successivamente sarà
necessario verificare separatamente le richieste Base/Core e l'assegnazione
dei job nel Bouncer, PRIMA di autorizzare qualsiasi modifica al calendario
o ai filtri. Una classe presente non prova che lo spawn avvenga.

Non installare insieme questa diagnostica e un altro controller MHS
sperimentale. Mantenere il rollback `main` M54 e il ramo sperimentale
distinti.
