# Passo 18B — Diagnostica M1: SOLO high bit dello snippet

**Prova reale del primo M1, 30 ottobre 2026:** The Sims 4 avvia il lotto,
`XML Injector Test` appare sulla cassetta postale, ma `MY HIGH SCHOOL
(PROVA)` è assente. Nessun `lastException` o `lastUIException` nuovo
era visibile nella ricerca Finder. L'utente ha poi rimosso M1 dalla Mods.

## Errore trovato nel sorgente
L'instance del nostro `XmlInjector` snippet era il FNV-64 esatto del nome
`Iliyana:MHS_M1_Mailbox_Injector` **senza il bit alto**, in contrasto
con la convenzione spiegata dalla documentazione XML Injector.

Prima: `0x1E510F5C25302095` = `2184544182686720149`

Corretto: `0x9E510F5C25302095` = `11407916219541495957`

Il sorgente GitHub `Injector.xml` e i suoi test sono stati corretti.

## Secondo package diagnostico
È stato prodotto localmente un nuovo file con **UNA SOLA DIFFERENZA** rispetto
a `MHS_M1_MENU_SOLO_TEST.package`: il valore `s` nel XML Injector snippet
e il corrispondente Instance ID nel DBPF `0x7DF2169C`.
Tutte le **altre otto risorse** sono identiche byte per byte quando estratte
e decompresse, incluse categoria/SimData, picker, conferme e STBL IT/EN.

- Nome: `MHS_M1_DIAGNOSTICA_HIGHBIT_SOLO_TEST.package`.
- Size: **3458 bytes**.
- SHA-256: `e552fde3f1e8cc5398a945ca514c3f0d5da1effc273a8722a030aed98f4bc8f4`.
- Archivio per la user: `MHS_M1_DIAGNOSTICA_HIGHBIT_CON_ISTRUZIONI.zip`
  (prodotto nell'ambiente della chat, non aggiunto al repository).
- Inventario: 9 risorse, nessun duplicato; DBPF 2.1 index minor 3;
  1 categoria, 1 SimData binaria, 4 interaction, 1 snippet, 2 STBL.

**Questa è una prova controllata, non una build funzionante confermata.**
Il cambiamento è necessario per rispettare la convenzione dell'XML Injector,
ma non sappiamo ancora se risolverà l'intero problema.

Prova graduale su una **nuova partita**, mantenendo XML Injector 4.2,
lasciando la v1.6 invariata e senza il vecchio M1. Non salvare se il menu
o l'avvio hanno problemi.

Riferimento: issue #1.
