# M121 — Otto Base + cinque Core manuali (beta Mac)

## Prove REALI da cui parte
Nel test Mac M120 del 3 novembre 2026, il comando status ha
mostrato alle **8:12** e nuovamente alle **10:34**:
`EA_base_created=8/8`, `EA_base_present=8/8`,
`count_override=1`, `native_count=(3,3)`, `filter=8`,
`missing=none`, `error=none`.

Si tratta di un risultato reale nel gioco per gli OTTO ruoli EA
Base. Non attesta le lezioni, la distribuzione nelle due aule
né i cinque Core.

## Nuova beta M121

`src/m121_all_npc/mhs121_thirteen_npc_trial.py`
riutilizza il meccanismo della M120 per gli otto Base.
Aggiunge una sola situazione originale EA Core `298052`.

- Recupera **esattamente i cinque ID scelti manualmente** dal
  registro `MHS97_RuoliSpeciali_slot_*.json` del salvataggio.
  Non crea, inventa o ridistribuisce automaticamente ruoli.
- Risolve i cinque `SituationJob` nativi Core di EA:
  `278965`, `278966`, `278967`, `278968`, `303765`.
- Durante la creazione della prima situazione EA Core,
  clona l'originale guest list, preserva gli ospiti docente
  `277895`/`278963`, rimpiazza **solo** gli ospiti con
  job studente Core con i cinque SimID precisi.
  Un ruolo duplicato, sconosciuto o senza oggetto EA causa
  rifiuto senza cancellare la lista originale.
- Usa il filtro EA originale `TunableSimFilter.BLANK_FILTER`
  soltanto su richieste mirate di quegli studenti con
  stesso Situation/Job/ID e vincolo su singolo Sim.
- Mantiene l'override Base nativo da `(3,3)` a `(8,8)`
  e l'invito di otto Base già verificato con M120.
- `mhs121.status` legge separatamente:
  `EA_base_created`, `EA_base_present`,
  `EA_core_created`, `EA_core_present`, `core_filter`,
  `missing_core_jobs` ed eventuali errori.
- `mhs121.stop` ripristina i metodi EA originali e
  non cambia i file del registro MHS.

## Prova Mac (SOLO copia salvataggio)

1. Chiudere The Sims 4 e conservare una COPIA del salvataggio.
2. Rimuovere da Mods le diagnostiche M111 e le beta M119/M120:
   non devono convivere con M121. Conservare la mod stabile
   che gestisce il menu/registro MHS.
3. Scaricare l'artefatto
   `MHS_M121_THIRTEEN_NPC_MAC_EXPERIMENTAL` da:
   https://github.com/iliyanadg/MyHighSchool/actions/runs/41708432871
   Estrarre `MHS_M121_TREDICI_NPC_MAC_BETA.ts4script` in Mods.
4. A casa, con 2 classi da 8 attive e tre teen giocabili
   iscritti, usare `mhs121.arm`. Il registro M97 deve avere
   cinque studenti NPC speciali differenti già scelti.
5. Al liceo, subito dopo arrivo, `mhs121.status`.
   Mandare uno screenshot. Verso le 10:30 ripetere lo stesso
   comando per confrontare stabilità dei job.
6. Chiudere il test con `mhs121.stop` e riavviare
   prima di qualunque altra beta.

## Limiti importanti
**La M121 è compilata e testata su ambiente simulato**, non
ancora verificata nel gioco. Nel test GitHub Actions Python 3.7
sono passati **12 test** che includono regressioni M120:
https://github.com/iliyanadg/MyHighSchool/actions/runs/41708432871

Anche il possibile risultato `8/8 Base + 5/5 Core` conferma
soltanto appartenenza degli ID nei rispettivi ruoli EA al
momento del controllo. Non dimostra tre playable nel job di
lezione né due aule da otto studenti seduti. La chiamata
EA Core può fallire indipendentemente dalla Base; il report
permette di distinguerle.

Il branch `main` non è stato alterato.
