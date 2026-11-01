# Capienza originale delle fasi lezioni EA — 1 novembre 2026

Sei XML originali esportati dall'installazione Mac dell'utente e ricevuti in chat.

| Tuning | Fase | Job studente | EA upper bound | Proposta |
|---|---|---|---:|---:|
| 293642 | GoToClass1 WithTrait | 277919 | 6 | 8 |
| 293644 | GoToClass1 NoTrait | 277919 | 6 | 8 |
| 304561 | AttendClass1 NoTrait | 277919 | 6 | 8 |
| 304563 | AttendClass1 WithTrait | 277919 | 6 | 8 |
| 297773 | Background GoToClass Others | 277919 | 8 | mantenere 8 |
| 304570 | Background AttendClass Others | 280777 | 8 | mantenere 8 |

**Importante**: i limiti 6/8 si riferiscono a gruppi/ruoli *delle fasi*, non al totale dei Sim convocati nel lotto. Non sommare 6+8 e non assumere che alzare a 8 risolva 16/16.

I modificatori `upper_bound_count_modifiers` presenti nei file rimangono invariati, come i test dei ruoli base, il trait `293779` e i ruoli docente/preside. Inoltre le fasi GoToClass e AttendClass non provano da sole una corrispondenza con l'aula fisica 1/2 del registro.

In questa sessione è stato creato e validato localmente il prototipo `MHS_8x8_FASI_EA_PROTOTIPO_NON_INSTALLARE.package` con sole 4 risorse XML identificate dai TGI originari `0x7DF2169C:0x00000035`. **Non fa ancora parte di un rilascio giocabile, non installarlo come soluzione di convocazione.**

Per una vera build dei 16 iscritti mancano ancora: count del WeeklyScheduleDay delle situazioni base, idoneità filtro EA effettiva, limite spawn nel lotto, collegamento runtime all'intero registro, validazione C1/C2 nelle fasi, test in gioco. Non usare More Students vecchio in parallelo.
