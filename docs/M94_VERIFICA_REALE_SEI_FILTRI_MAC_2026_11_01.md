# M94 — Verifica reale dei sei filtri EA su Mac, 1 novembre 2026

Fonte primaria: `MHS_M94_FILTRI_LICEO_EA.json` generato direttamente da
The Sims 4 del salvataggio dell'utente, durante una diagnostica effettuata
**da casa alle 06:58 del mercoledì di gioco**, non nel liceo.
Gli altri report sono `MHS_M58_SITUAZIONI_DIAGNOSTICA(5).json`
e `MHS_M85_PRESENZE_RUOLI_EA.json`.

## Dati originali osservati in gioco — 6/6 validi

| EA job ID | EA job | SimFilter GUID | sim_auto_invite min–max | Allow instantiated |
| --- | --- | --- | --- | --- |
| 277894 | Base Student | 280516 | 1–1 | True |
| 278965 | Cheer | 276592 | 1–1 | True |
| 278966 | Chess | **276596** | 1–1 | True |
| 278967 | Football | **276594** | 1–1 | True |
| 278968 | Computer | 276595 | 1–1 | True |
| 303765 | Mean Sim | 303766 | 1–1 | True |

**Importante:** le precedenti prove mock M94 avevano **scacchi e football
invertiti**. I dati dal gioco sono la fonte di verità; correggere mock
e selezione, senza assumere che l'ordine dei filtri segua i job ID.

In `src/m93_core/mhs93_verified_jobs.py` sono memorizzati i sei
valori esatti e una verifica restrittiva di snapshot EA che blocca
filtri nuovi/sconosciuti, identità duplicate e count non validi.
I nuovi test verificano esplicitamente l'inversione.

## Dati M85 / M58 nel medesimo test

- Registro MHS: 16 iscritti.
- `M58`: `installed=true`, `error=none`,
  `counts={}`; la sonda non ha osservato creazioni di situazioni
  liceali in quella visita da casa.
- `M59`: `filter_calls=12864`, `manifest_available=true`,
  `registered_missing_on_zone=16`, `registered_present_on_zone=0`,
  `school_filter_counts={}`. Queste chiamate sono filtri generici,
  NON prova di 12.864 richieste scolastiche.
- `M85`: `registered=16`, `registered_on_lot=0`,
  `registered_in_ea_school_situations=0`, `on_lot_per_class=[0,0]`,
  `seated_in_correct_class_verified=false`.

**Interpretazione corretta:** report effettuato a casa alle 06:58.
I contatori a zero non dimostrano un bug di partecipazione al liceo:
si riferiscono a una zona non scolastica. La prova dice che EA ha
caricato i sei tuning e che il registro rimane a 16, non che EA li
abbia chiamati oppure che siedano in aula. Nessun caso di successo
o fallimento in classe può essere inferito da questi report.

## Passo ingegneristico successivo

La tabella staticamente nota dei sei filtri non equivale alla mappa
dei Sim che occupano ruoli CoreClassNPCs; né stabilisce
quanti `weeklySchedule_HighSchool_Active_Main` inviti Base sono
necessari dopo i Sim giocabili. Il prossimo adapter richiede:

1. verifica sulla zona del liceo prima della scelta EA;
2. corrispondenza **ruolo speciale -> Sim iscritto** nel salvataggio;
3. prenotazione di esattamente `16 - played - core` slot Base
   senza richieste extra e senza selezione casuale fallback;
4. 8 posti e insegnanti per aula e test fisici alle 10:00/14:00.

La build M94 è una **diagnostica in sola lettura**; non attivare
M89/90 solo perché il report dice 6/6. Le due classi da otto studenti
non sono ancora state convalidate in-game.
