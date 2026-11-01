# Passo 79 — Esito positivo del test di isolamento: lezioni EA alle 10:00

## Evidenza in gioco, 1 novembre 2026

L'utente riferisce che con la build di isolamento
[GitHub Actions 41257486408](https://github.com/iliyanadg/MyHighSchool/actions/runs/41257486408)
(M58, head `0bd4c780238698facee1add79829dfb029541214`), gli studenti
**sono seduti ai banchi alle 10:00** a Copperdale.

Confronto riferito in precedenza:
- **MY HIGH SCHOOL assente**: le lezioni EA si avviavano con studenti seduti alle 10:00.
- **Versione MY HIGH SCHOOL con restrizioni ai filtri EA**: studenti potevano apparire sul lotto, ma aule vuote.
- **Build di isolamento con restrizioni EA disattivate**: studenti seduti alle 10:00.

Conclusione limitata: la selezione pre-spawn dei filtri EA introdotta in M57/M60
è un forte sospettato dell'interferenza sul normale funzionamento scolastico.
La prova NON dimostra ancora che gli studenti seduti corrispondano ai 16 iscritti
nel registro o che personale, aula e situazione EA siano quelli previsti.
Non sono stati validati l'orario delle 14, la mensa o il prom in questa prova.

## Esatta configurazione della build che funziona

- `src/m57_selection/mhs57_filter_runtime.py`:
  `MHS_EA_FILTER_CONSTRAINTS_ENABLED=False`;
  i due wrapper `SimFilterService` registrano contatori ma inoltrano richieste EA
  senza applicare `apply_constraints`.
- `src/m55_attendance/mhs55_attendance_auto.py`: essendo installato l'hook M57,
  la guardia `mhs57_filter_runtime.installed()` impedisce le chiamate additive
  M55 `create_student_request`. Quindi **non** attribuire l'esito
  a convocazioni aggiuntive M55.
- Diagnostica `mhs58_situation_probe`: sola lettura sulle guest list e
  sulle create_situation, senza aggiunta o rimozione di invitati.
- Il pacchetto UI, registro e gestione del personale sono mantenuti;
  l'osservazione NON è un nuovo test funzionale dei menu.

## Vincolo di non regressione

**Non riattivare i vincoli M57/M60 di massa e non aumentare il numero di
situazioni Base Student in modo additivo.** Mantenere il comportamento EA delle
lezioni come baseline funzionante durante le prossime modifiche.

## Prossimo lavoro tecnico

1. Verificare con contatori/letture non invasive la differenza fra
   iscritti (C1=8, C2=8) e studenti in situazioni scolastiche EA reali.
2. Usare solo la API `SituationManager` / `SituationGuestList` già indagata
   nel Passo 78, dopo validazione di firma e lifecycle nel gioco attuale,
   per programmare la sostituzione selettiva di candidati negli **stessi**
   job/situazioni EA, senza interferire con la transizione alle lezioni.
3. Procedere incrementale: un solo studente NPC non-core, conferma di
   partecipazione a scuola e aula; poi ulteriori studenti e personale.
4. Separare sempre presenza sul lotto, ruolo EA corretto, assegnazione
   alla classe e presenza effettiva ai banchi. Non promettere 16/16.
5. Non alterare il registro, i menu verificati, il salvataggio o `main`
   (M54 rollback).

### Riscontro atteso dal prossimo test

Una sola lettura diagnostica, non una nuova prova senza mod:
quanti iscritti risultano presenti sul lotto **e in job EA scolastico**,
senza interazione che li convochi. Se le lezioni si rompono, rollback alla
build 41257486408.
