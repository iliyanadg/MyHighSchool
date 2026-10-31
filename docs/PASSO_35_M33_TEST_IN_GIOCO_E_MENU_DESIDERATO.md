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

## Aggiornamento 31 ottobre 2026, ore 01:30 — anteprima trasferimento e richiesta pausa
- Il comando `mhs32.transferpreview` sulla M33 ha funzionato in gioco: un solo Sim **Amarachi Darong** da Classe 1 a Classe 3; Classe 1 prevista **1/8**, Classe 3 prevista **1/8**. È un'anteprima, **non** una scrittura del JSON.
- **Nuovo requisito NON negoziabile dell'utente:** ogni operazione gestionale di MY HIGH SCHOOL (iscrizione, rimozione, trasferimento, consultazione e conferma) deve poter essere selezionata e confermata **anche quando il tempo in The Sims 4 è in pausa**, senza avviare l'orologio.
- La M33 usa attualmente `ImmediateSuperInteraction` e il picker è stato eseguito dopo aver tolto la pausa: non dichiarare supporto alla pausa finché un nuovo meccanismo non è stato verificato nel client reale.
- **Secondo requisito UX:** conferma della modifica e aggiornamento del registro tramite UI di gioco, senza dipendere da `*.commit conferma` digitati in console. Prevedere conferma esplicita e rollback, mantenendo l'anteprima prima di scrivere.
- **Test di accettazione futuro:** gioco in pausa → interagire con PC/cassetta postale → selezionare Sim → confermare tramite UI → vedere subito il nuovo registro nello stesso slot mantenendo il tempo fermo; verificare annullamento e persistenza dopo riavvio; **nessuna cancellazione di Sim**.
- Durante gli attuali test M33 NON usare commit; le operazioni console restano provvisorie e, se confermate, modificano il JSON esterno anche quando il .save non è salvato.

## Aggiornamento Mac 31/10 ore 01:33: confermati Annulla + Consulta Classe 1
- L'utente ha eseguito `mhs32.transfercancel` in M33. La console mostra `Trasferimento annullato. Nessun dato scritto.` (Amarachi Darong era solo in preview, non trasferita).
- Con gioco ripreso, `Consulta iscritti - Classe 1` apre davvero il selettore fotografico UI nella M33. Lo screenshot mostra **Amarachi Darong** e **Baby Ariel**, entrambi e soltanto i 2 iscritti Classe 1. Titolo/descrizione indicano sola consultazione, nessuna modifica al registro.
- I controlli successivi da completare senza commit: consulta Classe 2, classe 3 vuota, rimuovi Classe 1 e verifica preview `mhs27.removepreview`, iscrizione Classe 3 e `mhs25.preview`, `mhs29.audit`, `mhs29.find Ariel`, `mhs28.roster` finale. Ricordare che oggi le immediate interactions vanno eseguite a tempo avviato; il requisito futuro è funzionamento anche in pausa.

## Aggiornamento Mac 31/10 ore 01:37 — consultazione classi 2 e 3, annullamento rimozione
- L'utente ha eseguito `mhs27.removecancel`: la console indica `M27: rimozione annullata senza scrittura.` Nessuno studente è stato rimosso.
- In M33, `Consulta iscritti - Classe 2` apre una finestra con **soltanto Sofia Abrantes e Sofia Bjergsen**, entrambe con foto e nome. Verifica in gioco positiva.
- `Consulta iscritti - Classe 3` non apre nessuna finestra perché Classe 3 è ancora vuota; è il comportamento deliberato di `open_view_picker` con `EMPTY | Classe 3` (da confermare eventualmente in diagnostica). Non confondere con errore di apertura dei picker.
- **Miglioramento UX richiesto per release successiva**: se registro della classe vuoto, mostrare una notifica esplicita «La Classe 3 non ha ancora studenti iscritti», anziché nessuna reazione alla voce di consultazione.
- Resta da testare il picker di iscrizione nella Classe 3 con `mhs25.preview` e solo successivamente la ricerca e l'audit senza scritture: `mhs29.find Ariel`, `mhs29.audit`, `mhs28.roster`.
