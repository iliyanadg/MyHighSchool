# M98 — Menu nativo Ruoli speciali, macOS (solo scelta manuale)

**Obiettivo:** permettere all'utente di assegnare cinque studenti
adolescenti del registro MHS ai cinque ruoli speciali EA tramite
il menu nativo di The Sims 4. Mantiene la diagnostica M94.

## Cosa è implementato

La cartella principale `MY HIGH SCHOOL` contiene una nuova categoria
**Ruoli speciali**, con 11 azioni native:
- **Cheerleader:** Scegli/sostituisci; Rimuovi
- **Scacchi:** Scegli/sostituisci; Rimuovi
- **Football:** Scegli/sostituisci; Rimuovi
- **Informatica:** Scegli/sostituisci; Rimuovi
- **Sim perfido:** Scegli/sostituisci; Rimuovi
- **Riepilogo ruoli speciali**

Ogni selettore sceglie **un solo Sim**, tramite lo stesso
`UiSimPicker` funzionante del personale M53. Sono proposti
soltanto adolescenti umani **già iscritti** nelle due classi,
non appartenenti al nucleo giocabile attivo, e non assegnati
ad altro ruolo speciale. Cani, gatti, adulti, NPC fuori registro
e doppi incarichi vengono esclusi.

Il salvataggio nel file
`MY_HIGH_SCHOOL_M25_TEST_DATA/MHS97_RuoliSpeciali_slot_<numero>.json`
avviene solo dopo ✓ nel picker. X annulla; le modifiche a
registro/slot mentre il picker è aperto bloccano l'azione.
Il file è separato dai salvataggi EA. Una rimozione lascia il
posto vuoto: nessun rimpiazzo automatico.

## Compilazione Mac

`python -m tooling.build_mhs98_roles dist_m98/`
richiede Python 3.7; produce una coppia
`MHS_M98_RUOLI_SPECIALI_MAC_TEST.package` e
`MHS_M98_RUOLI_SPECIALI_MAC_TEST.ts4script`.
Il formato compila 76 risorse DBPF (63 di M85/M94 con il solo
injector e le 2 STBL aggiornate, più 1 categoria/SimData e
11 nuove interazioni); ZIP di 35 moduli Python3.7.
Le risorse del precedente menu restano conservate.

## Cosa NON fa M98

**Le assegnazioni sono provvisorie nel registro MHS.**
Non aggiunge automaticamente a EA i cinque Sim scelti;
non garantisce che passino i cinque filtri EA specifici.
Non manipola i filtri EA, non aumenta i posti,
non modifica i ruoli già spawnati nel giorno corrente,
non cambia i docenti, gli altri studenti o il prom.
**Non garantisce ancora 16 presenti e 8 in ciascuna aula**.

Il prossimo lavoro consiste nell'intercettare PRESTO i
filtri core originali EA, validare i cinque NPC per ruolo,
prenotare esattamente i loro posti e coordinare il numero di
inviti studenti Base M96 in modo atomico (nessun extra NPC).
Solo allora potrà essere costruita una beta di gestione
delle presenze effettive.

## Prova Mac raccomandata

1. Usare una copia del salvataggio, non il principale.
2. Rimuovere vecchia coppia M94 e inserire soltanto la
   nuova coppia M98 nel percorso `Mods`.
3. Da casa, PC o cassetta postale, aprire
   `MY HIGH SCHOOL > Ruoli speciali`.
4. Verificare il riepilogo e scegliere un iscritto
   adolescente umano per un ruolo; confermare con ✓.
5. Riaprire e verificare che il ruolo persista; togliere
   e verificare che si liberi senza scegliere NPC.
6. Verificare che la vecchia voce
   `Consulta presenze automatiche` continui a funzionare.

Il successo dei test di compilazione non equivale a un test
di gioco: prestare attenzione a eventuali LastException e
non installare simultaneamente M85, M94 e M98.
