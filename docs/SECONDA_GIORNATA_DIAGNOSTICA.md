# Seconda giornata: esito osservato e diagnostica aggiunta

La prima giornata della build `0dffc10` ha confermato in gioco che entrambe
le classi arrivano a otto seduti. La revisione seguente aggiunge soltanto
osservazioni: il filtro della lavagna, gli inviti degli studenti, le regole
di richiesta, gli orari e le situazioni EA conservano il loro comportamento.
Non viene dichiarata una versione stabile.

## Cosa dimostra il report ricevuto

Il report contiene 38 campioni; tutti i 16 studenti sono istanziati dalle
08:15 simulate. Alle 10:15 sono seduti 8/6, alle 10:30 8/8; alle 14:18 7/7,
alle 14:33 8/8. Le posizioni soddisfano la misura di vicinanza alle due lavagne
validate; non sono una prenotazione dei banchi o prova di completamento.

I quattro ritardatari sono NPC: due Classe 2 al mattino e uno per classe al
pomeriggio. Nei campioni del ritardo hanno tutti job, ruolo e tratto coerenti:
Classe 1 job 277919 / ruolo 276361 / tratto Class1 presente; Classe 2 job
280777 / ruolo 304569 / tratto Class1 assente. Stanno eseguendo AttendClass_NPC
sulla propria lavagna. Nel mattino si vedono spostamenti dal piano inferiore;
nel pomeriggio i due restano alle stesse coordinate dalle 13:36 alle 14:18,
passando da stand/idle all'interazione di lezione. Il report non espone il
progresso del routing, la prenotazione dei posti o il motivo di questa attesa.
Non attribuire una causa certa a porte, sedie, mod di terzi o filtri dei job.

Nessuna azione di lezione campionata punta alla lavagna opposta. Un'interazione
di scherzo prima della lezione usa l'altra lavagna: non è un ingresso in aula
errato. I 373 controlli e 71 rifiuti sono valutazioni di candidati: non provano
71 ordini di movimento sbagliati. Un altro NPC Classe 2 mantiene temporaneamente
Class1 tra 09:45 e 10:00, poi è allineato alle 10:15; è distinto dai ritardatari.
Per questo NPC il riepilogo conta anche quattro campioni seduti vicino alla
lavagna opposta: sono quattro istantanee dello stesso momento 10:00, con
sit_Passive su una sedia a (393,38; 151; 507,40). Il criterio è geometrico,
senza identificazione della stanza: non prova quattro ingressi né una lezione
nell'altra aula. Alle 10:15 è seduto presso la lavagna corretta con Class1 assente.

Alle 11:00 e 15:02 i job di lezione non sono più osservati; nell'ultimo campione
non risultano azioni di lezione attive. È compatibile con la chiusura naturale.
Non certifica il punteggio, gli obiettivi della carriera o il ritorno a casa.
L'evento chiamato end_of_day_report è generato dal comando, non dal termine EA.

Gli orari dei campioni sono del TimeService processato. Il report finale è
15:02:19, con GameClock 15:05:49 e scarto 3,51 minuti; alle 14:00 lo scarto
è 15,13, alle 14:18 è 1,90. Questo rende necessario conservare entrambi gli
orologi, ma non dimostra che lo scarto causi i posti vuoti.

Per il pranzo sono campionati 12 dei 13 NPC mentre mangiano: otto almeno una
volta seduti e quattro soltanto in piedi. Il tredicesimo non ha un pasto
campionato; non si può concludere che abbia saltato il pranzo. Non risultano
incidenti disciplinari campionati, senza garanzia sugli intervalli non osservati.

Il riepilogo storico actual_class_action_samples non riconosce tutti i mixer
NPC né il loro genitore. Leggere anche running_parent_actions: un mixer React
o UsePhone sotto AttendClass_NPC non è prova di un'assenza dalla lezione.

## Personale: funzione ancora aperta

Il menu M53 salva StaffStore/Personale_slot_*.json. Il controller conserva
gli invitati EA dei due docenti; non legge il registro per reclutare docenti,
preside, bidello o addetti mensa. Questa è una funzione non collegata, distinta
da un eventuale conflitto con altre mod. Il report della prima giornata non
contiene né il personale atteso né tutti gli attori reali: non si possono
inventare nomi o confronti individuali.

La mappa verificata è: Core 298052 con docenti 277895/278963; Venue 298096
con preside 278223 e bidello 290196; mensa 278011 con vendor 278010. I filtri
faculty verificati richiedono anche tratti nascosti specifici; i job prevedono
sostituzioni EA in caso di assenza. Un semplice invito esplicito non basta a
garantire la selezione. Prima di collegare il reclutamento occorre verificare
idoneità e disponibilità dei prescelti, trasferimento ai job di fase e
comportamento delle sostituzioni. Non assegnare tratti o carriere a tentativi.

Il menu ammette fino a tre addetti mensa e due bidelli; ciò non dimostra che
la situazione EA disponga di altrettanti posti. Non prendere arbitrariamente
il primo nominativo né considerare una terza classe supportata da questa build.

## Nuovi dati, senza interventi sugli NPC

La revisione a 50 moduli aggiunge mhs_school_readback. Nelle finestre
09:30–10:30 e 13:30–14:30 registra ogni tre minuti simulati nomi, posizione,
postura, trait Class1, target, coda e appartenenze Base/Core/preparazione/lezione.
I campioni aggiuntivi sono separati dai dati usati dalle politiche di richiesta;
il diario completo rimane a 15 minuti. Limite 64 campioni aggiuntivi per giorno.

Alla cadenza del diario completo registra il personale salvato e gli effettivi
job EA, con i nomi, senza duplicare lo stesso docente tra Core e lezione.
Una lettura incompleta viene segnalata e non certifica una corrispondenza.
Gli errori sono riportati senza interrompere la scuola. Nessun dato personale
ricevuto è distribuito nello ZIP.

## Procedura

1. Conservare lo ZIP e una copia del report del primo collaudo come backup:
   l'esportazione successiva usa lo stesso nome del report. A gioco chiuso sostituire
   la coppia unificata con quella della revisione diagnostica: una sola coppia
   in Mods, niente vecchio M148 e niente duplicati. Conservare saves e tutti i JSON.
2. Aprire da casa la copia del salvataggio. Lasciare stessi studenti, personale
   scelto e altre mod, per confrontare le giornate. Non riarmare da console.
3. Seguire il normale ingresso EA. Annotare i seduti all'inizio delle due
   lezioni e osservare gli accessi alle aule senza impartire ordini di recupero.
4. Annotare il messaggio di fine giornata e gli obiettivi mostrati dal gioco.
   Esportare mhs148.report prima di lasciare il lotto, quando la lezione è finita.
   Il nome del file completo resta MHS_CLASSROOM_CONTROL_REPORT_COMPLETO.json.

Questa revisione misura la differenza del personale: non la presenta come
risolta. Non garantisce puntualità, compatibilità universale o assegnazioni EA
complete. Per eventuali interventi sul percorso occorrono prove del punto
di attesa, preservando i requisiti e la conclusione naturale della lezione.
