# M126 — Ingresso anticipato, due classi da 8: prima beta EA Mac

## Baseline verificata nel gioco (M123–M125)

Le convocazioni sono state confermate in partita:
- 13/13 NPC Base e Core nei ruoli originali EA;
- 16/16 adolescenti iscritti e nei job delle lezioni della classe del registro;
- zero extra e nessuna assegnazione alla classe sbagliata nei job EA;
- ma visivamente **solo 12 studenti seduti su 16 alle 10:32**
  nella M125: Classe 1 = 5 seduti, Classe 2 = 7.
- `mhs125.candidati=0` e il JSON M125 mostrava
  16 azioni scolastiche in esecuzione. Dunque non c'è evidenza
  che la causa prevalente sia una singola interazione concorrente.

Obiettivo reale: studenti del registro MHS presenti e seduti
**già all'inizio della lezione**, senza spostare l'orario
ufficiale di EA, senza cambiare le classi e senza extra.

## Intervento nuovo

La M126 mantiene lo stesso controller di ammissione da M121
(8 Base + 5 Core), gli stessi inviti alle lezioni da M123
e i lettori di M124–M125.

In più, nella **prima situazione originale EA di preparazione**
per ciascuna classe, propone una guest list di **otto SimID**
del registro, non di Sims scelti da EA a caso:
- Classe 1: originale EA `293815` o `304701` (percorsi alternativi);
- Classe 2: originale EA `297774`;
- Job studente della preparazione: `277919`;
- preserva ospiti staff nei job EA conosciuti;
- il filtro originale EA viene applicato solo ai SimID NPC
  appropriati, senza sostituire i giocabili.

Se manca l'API, c'è un ruolo inatteso nella guest list,
un secondo percorso Classe 1 tenta di duplicare la preparazione,
o il roster 2x8 non è unico, la situazione EA originale
rimane invariata (fail closed).

`mhs126.status` mostra:
- `prep_create=0..2/2`, `prep_filter`, `prep_refused`;
- `EA_base_present` e `EA_core_present`;
- `lezioni_proiettate` e `lezione_job`.

`mhs126.prepara` legge i veri ruoli EA preparazione,
mentre `mhs126.classi` legge i veri ruoli EA di lezione.

## Limiti e corretta interpretazione

Questa versione è la **prima prova sperimentale di ingresso
anticipato tramite situazioni EA native**. I test offline
**NON** provano ancora:
- che gli 8 Sim vengano assegnati a un job EA già alle 9:40;
- che EA conservi le situazioni di preparazione fino all'inizio;
- che gli studenti raggiungano fisicamente il banco per le 10;
- che le aule e professori corrispondano al registro o che
  il comportamento sia stabile su più giorni.

Non abbiamo ancora un controllo automatico sicuro per
misurare i banchi occupati; il conteggio della seduta
resta una verifica visiva distinta dal job EA.

## Procedura Mac in una giornata di test

1. Chiudere The Sims 4, tenere una copia del salvataggio.
   Rimuovere M125 e le precedenti beta EA da Mods,
   ma conservare il menu/registro stabile MHS.
2. Scaricare:
   https://github.com/iliyanadg/MyHighSchool/actions/runs/41731696807
   artefatto `MHS_M126_EA_EARLY_PREPARATION_MAC_EXPERIMENTAL`.
   Installare **solo**
   `MHS_M126_INGRESSO_ANTICIPATO_MAC_BETA.ts4script`.
3. Da casa, prima del liceo: `mhs126.arm`.
4. Appena arrivati al liceo (circa 8:00):
   `mhs126.status`.
5. Alle 9:40 (o prima del suono):
   `mhs126.status`, poi `mhs126.prepara`.
6. Alle **10:00/10:05** durante l'inizio della lezione:
   `mhs126.classi` e conta visivamente gli studenti
   **già seduti** in Aula 1 e Aula 2.
7. Eventualmente `mhs126.status` alle 10:05,
   e manda screenshot.
8. Alla fine `mhs126.stop`, chiudi gioco. Non salvare
   sul salvataggio principale.

## Qualità di build
Python 3.7 Mac, **48 test offline superati**;
archivio di dodici moduli con controllo di firma e presenza
di `mhs126.arm`, `mhs126.prepara`, `mhs126.status`,
`mhs126.classi`, `mhs126.stop`.
Workflow SUCCESS:
https://github.com/iliyanadg/MyHighSchool/actions/runs/41731696807

Branch sperimentale: `feature/m55-presenze-studente-test`.
`main` stabile non è stato modificato.
