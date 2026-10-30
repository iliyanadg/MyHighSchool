# Passo 27 — Rimozione studenti per singola classe (funzione richiesta)

Richiesta utente, 30 ottobre 2026, dopo la prima prova positiva di
trasferimento di uno studente tra le due classi.

## Comportamento desiderato del menu
`MY HIGH SCHOOL` deve distinguere:
- `Iscrivi / sposta studenti — Classe 1`
- `Iscrivi / sposta studenti — Classe 2`
- **`Rimuovi studenti — Classe 1`**
- **`Rimuovi studenti — Classe 2`**

Le due voci **Rimuovi** devono aprire un picker con foto e nomi
**soltanto degli studenti iscritti alla classe scelta**. Scelta multipla
1–8, con possibilità di annullare. Vuotare l'iscrizione libera
posti ma non cancella il Sim né lo aggiunge automaticamente a un'altra
classe. Può essere reiscritto in futuro.

## Primo codice sorgente (NON ANCORA MENU IN GAME)
`src/m26_withdrawal/mhs26_remove.py` offre:
- `class_member_ids`: elenco esatto di iscritti alla classe scelta;
- `candidate_rows`: passa al futuro picker solo le SimInfo
  corrispondenti a membri realmente iscritti, senza NPC esterni;
- `plan_removal`: rimozione in batch atomica; rifiuta ID di altra
  classe, duplicati, classe non valida e lista vuota; **nessuna
  eliminazione del personaggio**;
- `RemovalService.preview/commit`: nessuna scrittura dalla preview;
  commit solo se slot e fingerprint del registro non sono cambiati.
  File JSON esterno invariato fino al commit.

`tests/test_m26_withdrawal.py` copre le due classi, 1–8 studenti,
filter, batch erronei, rollback e reiscrizione.

## Stato
- La UI M25 e il relativo JSON rimangono **inalterati**.
- **Le due nuove opzioni del menu non esistono ancora nel package**:
  prima occorre creare e provare un SimPicker nativo filtrato con i
  soli registrati e associare una conferma di rimozione.
- L'ultimo screenshot dell'utente `mhs25.preview` mostra Classe 2,
  1 studente selezionato, **1 trasferimento PREPARATO**, totale
  previsto Classe 2 3/8. Non prova il commit di questo trasferimento,
  né quello inverso affermato dall'utente.
- Il JSON esterno non segue i restore/Save As di The Sims 4; M26 non
  corregge questo limite di persistenza.
- La notifica arancione non appare in M25 e resta bug separato.

## Prossimo passo
Creare due interazioni di menu per rimozione, una per ciascuna classe,
con selettore che mostra *solo* `candidate_rows`, poi testare in una
nuova partita di prova. **Non** far ripetere i test del registro M25
prima di aver verificato la UI di rimozione in codice.
