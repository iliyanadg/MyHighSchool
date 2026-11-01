# Passo 83 — Compatibility gate 1.129.39.1230: vecchi mod come riferimenti, mai patch cieche

## Contesto al 1 novembre 2026

Fonte EA ufficiale, patch del **27/10/2026**:
https://www.ea.com/it/games/the-sims/the-sims-4/news/update-10-27-2026

Versione corrente Mac pubblicata da EA: **1.129.39.1230**; versione
confermata anche dal `GameVersion.txt` ricevuto in precedenza
dall'utente e dalla prova Mac M58.

EA segnala espressamente conflitti e problemi di stabilità dovuti a
mod obsolete. I package/script di Sonozaki Elementary e ksuihuh More
Students 18/24/40 analizzati nei Passi 81-82 sono **materiale storico
di studio**, non tuning/programmi verificati per la patch odierna.

## Cosa è stato sviluppato

- `src/m83_compatibility/mhs83_preflight.py`: modulo Python puro, senza
  import di servizi EA, injection, spawn, modifiche ai Sim o agli XML.
  **Blocca** versioni Mac diverse dalla patch documentata, controller
  liceo concorrenti, registri incompleti o duplicati, idoneità teenager
  non verificata, ruoli core già occupati/ambigui, o limiti non verificati.
- `tests/test_m83_preflight.py`: 8 test di controllo sulla patch attuale,
  registro C1=8 C2=8, studenti della famiglia giocabile, ruoli EA core,
  capienza NPC base, posti per entrambe le lezioni e isolamento di
  Sonozaki Elementary dai controller del liceo.
- `.github/workflows/m83-preflight.yml`: CI Python 3.7 **solo test
  offline**, senza generare package giocabili. I test sono stati anche
  eseguiti in un ambiente Python locale e sono passati. L'esito finale
  del job GitHub va verificato separatamente.

## Cosa significa il gate

Il gate costruisce un piano di 16 studenti SOLO quando riceve:
1. Versione Mac 1.129.39.1230;
2. Esattamente 8 ID univoci per ognuna delle due classi, nessun duplicato;
3. Verifica attuale di idoneità (umani adolescenti);
4. Distinzione esplicita tra giocabili iscritti, core role EA e NPC base;
5. Capienza reale **verificata da tuning corrente** delle situazioni
   EA Base Student (non presunta da vecchi mod);
6. Capienza **verificata** di `go_to_class_1`, `attend_class_1`,
   `go_to_class_2`, `attend_class_2`.

Se una prova manca: `BLOCKED`. Con tutti i dati presenti e coerenti:
`OFFLINE_PLAN_ONLY`, **mai** un'affermazione «sono arrivati 16 studenti».

Esempio sintetico per 2 iscritti giocabili, 2 core iscritti e 12
NPC iscritti: una configurazione con solo 6 posti EA Base Student è
**insufficiente**. Questo non significa che siano sempre 12 NPC:
dipende dagli ID e dai ruoli realmente verificati nel salvataggio.
La versione da 18 di ksuihuh non sostituisce questa verifica.

## Da NON fare

- Non includere nei nuovi file il codice compilato di Sonozaki/ksuihuh.
- Non riattivare le restrizioni globali M57/M60 che avevano lasciato le
  aule vuote.
- Non generare o installare un package sovrascrivendo `WeeklySchedule`
  soltanto perché un vecchio mod lo faceva.
- Non aumentare o modificare i job del prom e diploma se l'obiettivo
  immediato sono le lezioni normali.
- Non sovrapporre due `SituationJob` allo stesso NPC.
- Non modificare M58 isolamento:
  https://github.com/iliyanadg/MyHighSchool/actions/runs/41257486408

## Prossima milestone tecnica

**M84 — Verifica tuning EA correnti + profilo 8/8.**
Prima di emettere un nuovo package confrontare direttamente i tuning
**EA attuali** delle due fasi di lezione, schedule e situation job,
soprattutto gli id 277657, 279958, 293642/293644,
304561/304563, 297773, 304570, 277733, 277894,
298052 e 293779. Le descrizioni/ID di Passo 82 derivano da
override esterni: da soli NON provano l'attuale XML EA.

Poi progettare solo le modifiche minime necessarie, con TGI
espliciti, parità di struttura, test a livello di risorsa, fallback
e controllo delle lezioni alle 10:00/14:00. Solo in seguito
collegare il registro ai candidati EA e all'assegnazione aula.

## Stato del progetto

**M83: implementazione del gate offline su GitHub.**
**Nessuna nuova build di gioco in questo passo.**
La parte difficile — far comparire esattamente 16 studenti iscritti
nelle situazioni e nelle aule corrette — non è ancora risolta.
