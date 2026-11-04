# Audit e integrazione Classroom Control

**Seguito dell'audit:** ricevuti i quattro file EA e l'inventario richiesti.
La revisione corrente aggiunge il filtro per NPC basato sul registro, il
dispatch dei test limitato agli iscritti nel liceo e la lettura reale delle
code. Vedere [contratti EA verificati](EA_CONTRATTI_CLASSROOM_CONTROL.md) e
[primo collaudo](PRIMO_COLLAUDO_CLASSROOM_CONTROL.md). I quattro file non
devono essere richiesti nuovamente né distribuiti.

Data: 4 novembre 2026. Base analizzata: branch
`feature/m148-dual-clock-low-impact`, commit
`06076c816dea23df8f86e9e875f00f5eda2aefe3`.
Lavoro sul branch separato `feature/classroom-control-unified`; nessun reset di
main, versione stabile o dato del giocatore.

## Evidenze e storia

| Fase | Capacità conservate | Limite delle evidenze |
| --- | --- | --- |
| M54 | Menu, iscrizioni/trasferimenti/rimozioni persistenti, personale umano | Conferma Mac del 31 ottobre; il registro personale non assegna da solo incarichi EA |
| M55–M104 | Studio inviti, slot, filtri e ruoli Base/Core; M98 aggiunge scelte manuali dei ruoli | Diversi controller alternativi, non componenti da caricare tutti insieme |
| M105–M121 | Inserimento nei posti originali EA, selezioni Base/Core | Impostazione sperimentale 3 giocabili + 5 Core + 8 Base |
| M122–M139 | Proiezione classi, preparazione, tratti, lavagne e adapter EA/Zerbu | Job e invito non provano presenza fisica o lezione completata |
| M140–M147 | Interazioni originali, due lezioni, ingresso anticipato e riarmo registro | Tentativi accettati non equivalgono a seduta; ciclo giornaliero incompleto |
| M148 | Due orologi osservati, campioni completi ogni 15 minuti e scritture ridotte | Misura il ritardo; non dimostra che il ritardo causi il 7/8 |

Sono stati consultati anche i documenti relativi ai 1.067 XML già studiati e
alle successive estrazioni. In questo checkout sono presenti dieci XML EA
originali, non l'archivio completo: documentazione e file disponibili sono
evidenze diverse. Non occorre ripetere indiscriminatamente tutte le estrazioni.

## Catena effettiva

1. `RosterStore`, `SettingsStore` e identità slot determinano classi e attivazione.
2. Il controller intercetta le chiamate **originali** di creazione EA. Proietta
   gli iscritti nei job Base/Core e poi nelle fasi preparazione/lezione.
3. Il Bouncer riceve richieste con identità precisa; non vengono create
   situazioni scolastiche parallele per riempire posti.
4. Il tratto EA Class1Student viene allineato alla classe iscritta. Gli adapter
   delle lavagne intervengono sulle forme EA/Zerbu riconosciute.
5. I giocabili usano Class_Start e continuazioni native; gli NPC restano nel
   percorso EA. Una richiesta accettata non è prova che l'azione venga eseguita.
6. Il diario distingue istanza, azione, postura e target. La fine e gli obiettivi
   restano di EA: nessun completamento artificiale, teletrasporto o cambio orario.

## Rapporto M148 ricevuto in questa sessione

Il file privato del giocatore resta fuori Git. Contiene 38 campioni, nessun
errore di osservazione dichiarato e tre giocabili effettivi.

| Ora simulata osservata | Evidenza |
| --- | --- |
| 08:16 | Tutti i 16 iscritti hanno già un'istanza sul lotto |
| 09:37 e 09:52 | Un NPC iscritto alla Classe 2 esegue AttendClass_NPC con target la lavagna identificata come Classe 1 |
| 09:52 | Il divario degli orologi è 0,03 minuti: lavagna errata anche con orologi allineati |
| 10:16 e 10:31 | Postura seduta osservata: Classe 1 = 8, Classe 2 = 7; l'NPC è ancora in piedi |
| 10:46 | L'NPC è seduto presso la propria aula; entrambe le classi hanno otto posture sedute osservate |
| 14:00 | Classe 2 = 7 posture sedute; questa volta il giocabile in piedi sta già eseguendo la materia EA sulla lavagna corretta |
| 14:16 | Otto posture sedute osservate in entrambe le classi |

Questa sessione **non mostra una mancata convocazione iniziale**. Mostra un
target iniziale errato per un NPC e un ritardo di seduta di un giocabile nel
pomeriggio. Non consente di scegliere tra tratto cambiato dopo l'allineamento,
vecchia interazione rimasta in coda o altra selezione EA/terze parti: manca il
readback del tratto e dei job NPC al momento della scelta errata. Il nuovo
diario legge i job effettivi di tutti i 16 iscritti, mantenendo il campionamento
completo limitato a 15 minuti. Il rapporto non certifica da solo completamento,
esami, punizioni o eventi.

È confermato anche un difetto indipendente: i quattro gruppi di richieste
iniziali riportano rifiuti/azioni protette, ma il recupero della M148 richiede
che una richiesta iniziale sia già stata accettata. Le richieste anticipate
accettate non alimentavano quel registro. La nuova gestione non esclude
permanentemente uno studente dopo il primo rifiuto.

## Correzioni della prima integrazione (58db915)

- Una sola coppia di file, 47 moduli Python unici e un solo controller.
  Il package conserva tutte le azioni M54, aggiungendo il menu M98 dei cinque
  ruoli manuali: 75 risorse e 11 coppie categoria/SimData. Nessun vecchio
  controller M55/M105/altro viene incluso.
- Giocabili derivati dal salvataggio; rimossa la quota fissa tre. Il numero
  Base è `16 - giocabili iscritti - 5 Core`. Nessuna identità personale nel codice.
- Reset della contabilità a cambio giorno prima degli eventi EA, anche a
  registro invariato. Nessuna distruzione o ricreazione forzata di situazioni.
- Proprietario unico del ciclo di caricamento zona, collegato all'attivazione
  persistente del menu; ripristino degli adapter quando si torna a casa.
  Il caricamento diretto di una giornata già iniziata richiede riattivazione
  da casa, anziché ricostruire inviti già eseguiti.
- Richieste native limitate per studente/periodo; rifiuti iniziali e istanze
  tardive restano eleggibili. Test EA obbligatorio, intervalli minimi e coda
  verificabile; punizioni, pasti, bisogni e lezioni in corso sono protetti.
- Adapter di lavagna installati solo nel contesto liceale e con rollback
  quando l'adapter delle materie non è riconosciuto. In caso incompatibile
  si conserva il flusso originale EA e si mostra il blocco.
- Compilazione CPython 3.7 con hash dei sorgenti, inventario dipendenze,
  controlli CRC/bytecode e archivi riproducibili. Il compilatore isolato con
  hash seed fisso evita variazioni marshal dovute all'internamento in Python 3.7.
  Gli header usano timestamp normalizzati: il caricatore ZIP reale di Python
  3.7 rifiuta i bytecode PEP 552 basati su hash. Un test importa effettivamente
  i moduli puri dall'archivio, oltre a leggerne e confrontarne il codice.
- Inventario Mods in sola lettura: collisioni di moduli, hash, file sconosciuti
  e dati da conservare; nessuna cancellazione o spostamento automatico.

## Limiti osservati nella prima integrazione

Non è una dichiarazione di release stabile o di 8/8 puntuali. Restano da
verificare nel gioco almeno due giornate, il target NPC errato, le continuazioni
EA, pranzo, esami, eventi, altri salvataggi, CC e Windows.

L'adapter attuale richiede cinque NPC iscritti assegnati manualmente ai cinque
ruoli Core nativi. Oltre undici giocabili iscritti rifiuta l'attivazione:
è un limite di questo adapter, non un limite provato di The Sims 4.

La prima integrazione modificava lo snippet lavagne globalmente nella zona: pur preservando il ramo Elementary
riconosciuto e ripristinandolo fuori scuola, non abbiamo ancora un contratto
EA verificato per limitarne ogni predicato al singolo Sim iscritto. Il nuovo
dispatch usa ora tale contratto, verificato sui file ricevuti, e conserva le
liste originali fuori ambito. La compatibilità completa nel gioco con
Zerbu Go to School/Sonozaki Elementary **non è ancora certificata**.
Il registro personale M54 è conservato; non è stato inventato un nuovo sistema
di assegnazione dei professori o del preside EA.

## Prerequisiti ricevuti e conservati privatamente

1. Ricevuto l'inventario reale delle Mods tramite `tooling/mod_inventory.py` e le
   istruzioni di `INSTALLAZIONE_PULITA_MAC.md`. Serve a identificare i file
   effettivi e le collisioni; i nomi installati non sono visibili dal cloud.
2. Ricevute dall'installazione Mac corrente le copie originali di
   `event_testing/tests.pyc`, `event_testing/resolver.pyc`,
   `event_testing/test_base.pyc` e `interactions/interaction_queue.pyc`, se
   presenti in `simulation.zip`. Servono per il contratto dei predicati per Sim
   e per leggere la coda senza inventare API. Sono file da analizzare
   privatamente, **non da aggiungere al repository o alla build**.
3. Riutilizzata la documentazione del precedente archivio con il tuning NPC
   `super_HighSchool_Active_AttendClass_NPC` **297779** e il test set
   `testSet_HighSchool_Active_PickWhiteboard_Student` **279071**. Sono già stati
   studiati nei documenti: riutilizzare l'esportazione esistente, non riesportare
   tutti i tuning.

Per recuperare gli script su Mac: Finder, applicazione The Sims 4 effettivamente
installata, **Mostra contenuto pacchetto**, cercare `simulation.zip`; lavorare su
una copia dell'archivio ed estrarre solo i percorsi indicati. Se i nomi differiscono,
fornire prima il solo elenco dei membri delle cartelle `event_testing/` e
`interactions/`, senza modificare l'installazione. Nessun salvataggio completo
è richiesto.
