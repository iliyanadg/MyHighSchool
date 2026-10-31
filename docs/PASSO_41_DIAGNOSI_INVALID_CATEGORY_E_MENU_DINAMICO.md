# Passo 41 — 31 ottobre 2026, 03:38: M36 invalid category ID e nuove M37–M39

## Bug sul Mac riportato dalla giocatrice
Dopo aver sostituito M35B con M36, la cassetta postale ha smesso di aprire il menu. Il report Better Exceptions v3.17 riporta:
`This UI Exception was caused by interactions with an invalid category ID`
e `Found 0 Interaction Mod out of 2452 total files`. Quest'ultima frase **non prova** che la mod sia funzionante o che non ci sia un problema: l'eccezione UI è reale. La M36 **non deve essere reinstallata**.

M35B, prima del collegamento gerarchico, era stata verificata e mostrava il proprio menu `Classe 1 - M35 PROVA` con due opzioni e i due iscritti corretti. Quindi l'errore è correlato alla modifica del collegamento padre/figlio introdotta in M36.

## Ricerche sulle categorie e SimData
- Guida di riferimento: https://thesims4moddersreference.org/tutorials/creating-a-pie-menu/ — una PieMenuCategory usa tuning + SimData; il parent è una categoria esistente e va configurato correttamente.
- Discussione Mod The Sims https://db.modthesims.info/showthread.php?t=581879 — la risposta del giugno 2025 ribadisce che `_parent` deve corrispondere nella SimData e le risorse XML/SimData devono avere stesso Instance ID.
- Esempio codice in https://github.com/derneuere/HistorianCareer cita ID istanza PMC a 31 bit, mentre ID troppo grandi possono fallire per il resolver UI.
- Le ricerche orientate al forum Sims 4 Studio hanno trovato riferimento a vecchi thread sui pie menu tramite https://modthesims.info/showthread.php?t=645711; nessuna fonte esterna garantisce che la nostra specifica combinazione root/category sia compatibile con il client 2026.

## Ipotesi concreta
M36 scriveva il riferimento `_parent=14567074618947653827` nel tuning e nel campo a 64 bit 0x5C della SimData di Classe 1. Il menu radice usa ancora quell'ID storico molto grande, mentre la sottocategoria Classe 1 era già 31-bit. **Questa è un'ipotesi di causa**, non una certezza: i test statici precedenti validavano solo presenza di XML/SimData, non la capacità del runtime Olympus UI di risolvere il riferimento.

## Correzione sperimentale M37, compilata e con test offline superati
Workflow: https://github.com/iliyanadg/MyHighSchool/actions/runs/41161329214
Artifact: `MHS_M37_ROOT_31BIT_CLASSE1_SOLO_TEST`.
- Rigenerato un identificatore **31 bit** anche per il menu MY HIGH SCHOOL radice.
- Aggiornata l'identità Instance di XML/SimData del root, tutti i riferimenti delle interazioni principali e il parent XML/SimData di Classe 1; non rimangono riferimenti all'ID root storico.
- 2 PieMenuCategory + 2 SimData; 29 risorse; 13 script vecchi invariati.
- Tutti i test offline Python 3.7 superati. **Ancora NON testata in game**.
- Se M37 blocca la cassetta, chiudere senza salvare e ritornare alla M35B / M34.

## Menu completo preparato M38
Workflow: https://github.com/iliyanadg/MyHighSchool/actions/runs/41161487522
- Struttura `MY HIGH SCHOOL → Classe 1 / Classe 2 / Classe 3 / Impostazioni`.
- Le tre classi ricevono solo le proprie iscrizioni/consultazioni/rimozioni/trasferimenti; in `Impostazioni` ci sono 2↔3 classi; in root attiva/disattiva.
- 5 PieMenuCategory + 5 SimData, tutte con ID compatti; test offline superati.
- **Non installare prima che M37 sia stata validata**.
- M38 non ha ancora filtro dinamico in base allo stato.

## Menu dinamico preparato M39
Workflow: https://github.com/iliyanadg/MyHighSchool/actions/runs/41161791742
- Mantiene la gerarchia M38 e aggiunge un wrapper con logica di disponibilità a 19 interazioni; lascia invariato il supporto EA SimPickerInteraction.
- Logica testata offline: quando DISATTIVA solo `Attiva`; quando ATTIVA/2 classi mostra 1+2 e `Abilita Classe 3`; quando ATTIVA/3 classi mostra tutte e `Disabilita Classe 3`. La persistenza per singolo save resta la M34.
- Nascondere le voci nel client dipende dal corretto uso di `_test` in game e **non è ancora verificato**; non installare finché non abbiamo isolato la validità dell'albero delle categorie.
- Alla scrittura l'applicazione conserva il blocco di Classe 3 occupata e la barriera RosterStore, ma il menu non controlla ancora la scuola EA.

## Requisiti ancora NON soddisfatti
1. Conferme via finestra gioco e scrittura senza console: i commit esistono nel codice ma solo tramite comandi console.
2. Utilizzo senza avviare l'orologio quando il gioco è in pausa: oggi le interazioni provate sono ImmediateSuperInteraction ed hanno richiesto tempo avviato.
3. Il liceo EA non è controllato, le presenze e le aule fisse non sono implementate.
4. La M39 non ha una verifica in-game; non dichiararla funzionante né raccomandarla come build stabile.

## Next game validation senza ripetere test vecchi
- Utente con save TEST slot 11: backup directory JSON registro; chiudere gioco; togliere M36 da Mods.
- Tenere M35B (o M34) come fallback noto funzionante fuori Mods.
- Solo coppia M37: avviare, cliccare cassetta in pausa, verificare se MY HIGH SCHOOL appare e se `Classe 1 - M35 PROVA` si trova sotto, senza toccare gli iscritti; in caso di UI Exception ritirare la coppia M37 e tornare a M35B.
- Se M37 supera questa singola verifica, non ri-testare gli altri picker già verificati; passare a gerarchia completa M39 e poi alle conferme grafiche e in pausa.

**Unica coppia MHS alla volta**. Nessun commit di studenti nei test di menu. Scritture su JSON esterno non seguono Salva/Senza salvare di The Sims 4.
