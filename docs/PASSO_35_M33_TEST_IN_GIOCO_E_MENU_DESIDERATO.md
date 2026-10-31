# 31 ottobre 2026 — Verifica effettiva M33 su Mac e prossimi controlli

## Confermato dalla giocatrice
- Rimuovendo la coppia M32 dalla Mods, il menu della cassetta postale è tornato a essere cliccabile. Better Exceptions M32 segnalava una categoria non valida.
- Dopo aver installato la coppia M33, il menu «MY HIGH SCHOOL (M33 TEST)» si apre regolarmente dalla cassetta postale, comprese le voci della seconda pagina.
- Sono visibili Consulta iscritti 1/2/3, Rimuovi studenti 1/2/3, Prepara iscrizione 1/2/3 e tutte le sei operazioni «Classe X - Trasferisci in Classe Y».
- La selezione di un trasferimento NON ha prodotto una proposta: il comando `mhs32.transferpreview` mostra «M32: nessun trasferimento preparato». Non sappiamo ancora se non è stato aperto un picker, se la scelta non è stata confermata o se c'è un errore in callback. Usare `mhs32.report` per diagnosticare PRIMA di modificare codice.
- Non risultano confermate scritture al JSON in questo giro; menu aperto non significa che gestione dati funzioni.

## TEST DA COMPLETARE (tutti senza commit)
1. `mhs28.roster` = controllo dell'attuale registro per slot. Snapshot precedente: slot 11, Classe 1 2/8 (Baby Ariel, Amarachi Darong), Classe 2 2/8 (Sofia Bjergsen, Sofia Abrantes), Classe 3 0/8.
2. Trasferisci Classe 1 → Classe 3, seleziona e conferma la foto solo se il picker appare, poi `mhs32.report`, `mhs32.transferpreview`; **non** `transfercommit`. Se non si apre alcuna finestra fotografica, fare subito `mhs32.report`.
3. Consulta iscritti 1 e 2: apertura con i ritratti giusti; Classe 3 vuota deve segnalare EMPTY. Se non si apre `mhs29.report`.
4. Rimuovi studenti Classe 1: visualizzare solo gli iscritti Classe 1, selezione e `mhs27.removepreview`; mai `removecommit`. Se fallisce `mhs27.report`.
5. Prepara iscrizione Classi 1/2/3: finestre adolescenti; `mhs25.preview` dopo la selezione; mai `mhs25.commit`.
6. Controlli sola lettura `mhs29.audit`, `mhs29.find Ariel`, `mhs28.roster` dopo i test.
7. Controllo finale: il registro deve rimanere invariato, salvo precedenti scritture deliberate.

## REQUISITO UX CONFERMATO — NON PERDERLO
**Versione finale:**
`MY HIGH SCHOOL → Classe 1 / Classe 2 / Classe 3 → menu delle operazioni di quella classe`.
Dentro ogni classe: Iscrivi studenti; Consulta iscritti; Rimuovi studenti; Trasferisci verso ciascuna delle altre due classi. Nel tempo: gestione insegnante e aula/lavagna assegnata, eventuali opzioni pertinenti.
NON mantenere l'attuale menu piatto come progetto UX finale: è solo un workaround di compatibilità.

Le PieMenuCategory figlie M30/M32 hanno bloccato l'intero menu della cassetta. Una futura implementazione annidata deve verificare che gli ID categoria siano registrati nella UI del gioco con XML e SimData corretti. Evitare di dichiarare riuscita sulla sola base di test Python.

## SICUREZZA
Tutti i comandi `*commit conferma` scrivono immediatamente sul JSON esterno di test; uscire da The Sims 4 senza salvare NON annulla quelle scritture. Per le prove attuali non usare commit, pulizia o undo. La frequenza reale alle scuole EA e la presenza nelle 3 aule NON sono ancora implementate.

## Aggiornamento prova M33 trasferimento — ore 01:27, 31/10/2026
- Dopo aver **tolto la pausa**, l'interazione della cassetta postale «Classe 1 - Trasferisci in Classe 3» è stata effettivamente eseguita: i comandi delle interazioni ImmediateSuperInteraction erano in attesa mentre il gioco era in pausa.
- Screenshot dell'utente del comando `mhs32.report`: `OPEN | Classe 1 -> 3 | 2 candidati` seguito da `READY | 1 studenti da Classe 1 a Classe 3. Usa mhs32.transferpreview`.
- Dunque il picker fotografico del trasferimento **si apre** e produce una selezione preparata in memoria con un iscritto della Classe 1. Non è stato ancora confermato alcun `commit` al registro esterno; la convalida di `mhs32.transferpreview` è il prossimo test.
- Per gli altri picker M33, **togliere la pausa prima di concludere che il comando non funziona**. Usare console di diagnostica dedicata se non compare la finestra dopo che il gioco è in esecuzione.
- Rimane prioritario per l'UX finale il menu annidato MY HIGH SCHOOL → Classe 1/2/3 → operazioni, senza reintrodurre categorie invalide.
