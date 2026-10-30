# Passo 18 — Root cause candidate: snippet XML Injector senza high bit

L'utente ha testato la build M1 su una nuova partita con The Sims 4.
- The Sims 4 si avvia e entra nel lotto senza crash.
- `XML Injector Test` appare regolarmente sulla cassetta postale.
- `MY HIGH SCHOOL (PROVA)` NON appare, neppure aprendo altre scelte.
- I file `lastException` e `lastUIException` trovati nel Finder sono tutti
  antecedenti al test di stasera; assenza di nuovi file non significa
  assenza di ogni errore di tuning.

## Difetto reale nei sorgenti
Le istruzioni per il modder di XML Injector richiedono che
l'Instance ID dello snippet sia il **FNV-64 del nome con high bit impostato**.

Per `Iliyana:MHS_M1_Mailbox_Injector`:
- FNV-64 senza bit alto: `0x1E510F5C25302095`
  = `2184544182686720149` (**valore errato usato in M1**).
- FNV-64 con bit alto: `0x9E510F5C25302095`
  = `11407916219541495957` (**valore corretto**).

Fonte sulla convenzione degli snippet:
https://www.scribd.com/document/483740722/XML-Injector-Modder-s-Documentation

Il vecchio validatore controllava lo stesso numero sbagliato codificato
a mano: non poteva trovare il problema, nonostante i test verdi.

**Correzione applicata:** nuovo ID dentro `src/experiments/m1_unbuilt/Injector.xml`;
funzione `fnv64_highbit()` e verifica calcolata da `n` nel validatore;
nuovi test che bloccano espressamente il vecchio ID.

## Stato e limiti
Un ID che viola la convenzione di XML Injector è un **difetto documentato**,
ma senza test isolato non sappiamo ancora se fosse l'unica causa del menu
assente. Non affermare che l'assenza del menu è stata risolta nel gioco.

Non riutilizzare il package M1 precedente (sha256
`a3bb443e3fa24e85365be74074e7ef46bfb5b61f14535516e346209d58bacdc3c`).
Se prepariamo una build corretta, darle un nome diverso e fare un altro test
sul salvataggio di prova soltanto.

L'utente ha già rimosso il precedente M1 dalla cartella Mods. La v1.6
non è stata toccata.
