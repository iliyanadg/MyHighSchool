# MY HIGH SCHOOL — correzione classi e personale, salvataggio 15

## Evidenza reale: report 6 novembre 2026 (slot 15)

- Tutti i 16 iscritti erano sul lotto prima dell'inizio delle lezioni.
- Zelmira Gomes e Sofia Abrantes, entrambe Classe 2, risultavano
  ancora con il tratto EA Classe 1 alle 09:30–09:57; il tratto era
  corretto dalle 10:00. Quindi la sincronizzazione in fase di
  preparazione arrivava troppo tardi per alcune convocazioni.
- Nei ruoli EA: 2 professori, preside, Gianluca Ferraro e Agnes
  Crumplebottom; Bjorn Bjergsen, Alex Moyer e Alessia Sanna NON erano
  presenti nei rispettivi job.
- L'invito straordinario per Bjorn tramite seconda situazione Venue EA
  298096 non restituiva un ID situazione e non risultava un secondo
  custode realmente in servizio.
- La lettura dei banconi verificava 0 stazioni, pur con i banconi
  visibili; la precedente rilevazione interrogava solamente
  `object_manager.get_all()` e richiedeva un nome HighSchool esplicito.
- Simulazione lenta osservata nel report: fino a ~37 minuti di distanza
  fra orologio visibile e orologio processato, quindi i tempi delle
  registrazioni devono essere letti con attenzione.

## Modifiche di questa build

1. **Pre-scuola**: all'inizio di ogni nuova giornata MHS sincronizza il
   tratto Classe 1/2 dei 16 iscritti PRIMA delle situazioni EA di
   preparazione. Lo riconvalida per ogni distinta preparazione mattutina.
   Mai correggere classi per Sim non iscritti.
2. **Banconi mensa**: rileva gli oggetti reali anche tramite
   `object_manager.values()`; ammette gli oggetti
   `CafeteriaStation` senza obbligare una stringa `HighSchool` nel
   nome, ma esclude le postazioni tipiche dell'università e gli arredi
   generici. Una vera postazione EA riconosciuta può autorizzare altre
   postazioni di definizione identica.
3. **EA cafeteria schedule**: quando EA richiede il numero delle proprie
   situazioni TendObject 278011 e i banconi verificati sono sufficienti,
   il controller può richiedere 2/3 situazioni nel calendario nativo,
   assegnando a ognuna **esattamente** Agnes, poi Alex, poi Alessia
   secondo il registro. Se una creazione fallisce non sceglie un NPC
   casuale per il posto aggiuntivo.
4. **Secondo custode**: si conserva l'invito esatto, ma il tentativo di
   secondo incarico native Venue usa anche le parole chiave standard
   `user_facing=False` e `creation_source` (con fallback di
   compatibilità). Se EA rifiuta, il report deve continuare a dire che
   Bjorn NON è in servizio.
5. **Report**: include data e risultato della sincronizzazione anticipata
   delle classi, conteggi EA richiesti per la mensa e motivi di blocco
   della rilevazione dei banconi.

## Stato delle garanzie

**Test automatici offline != collaudo in gioco.** Questa build non può
certificare il secondo custode o i 3 vendor contemporanei senza osservare
le appartenenze ai job EA in una giornata scolastica nuova.
Non aggiunge due bidelli a caso, non scavalca il salvataggio con nome,
non modifica le iscrizioni, non forza il movimento dei Sim giocabili,
non cancella o altera le situazioni principali di lezioni/EA.

## Accettazione in una sola giornata

Conservare una copia della build precedente, del salvataggio e dei file
MHS. Nel salvataggio 15, da casa usare `mhs148.arm`; alla successiva
giornata scolastica controllare verso le 10:15 le due aule da 8 e
al momento del pranzo le tre postazioni. Dopo le 15:00 creare
`mhs148.report` ed esaminare l'unico file
`MHS_CLASSROOM_CONTROL_REPORT_COMPLETO.json`.
Confermare i lavoratori esclusivamente in
`school_staff.samples[].comparison`; nessuna ricevuta di invito o
conteggio del calendario prova che siano realmente attivi.

## Miglioria identificazione mensa (EP12, verifica tuning EA)

Un controllo sui tuning ufficiali di *Vita da Liceali* ha identificato:
- GameObject tuning **277994**, `object_marketStalls_CafeteriaStation_HighSchool`.
- Situazione originale **278011**,
  `situation_Vendor_CafeteriaStation_HighSchool`.
- Tag esatto di ricerca delle postazioni della situazione 278011:
  **`Func_HighSchool_Active_CafeteriaStation`**.

La build riconosce prima questo tag sull'oggetto del lotto, e anche
l'identificativo di tuning originale. I numeri delle definizioni OBJD sono
distinti dal tuning id, per questo non devono essere confusi. Se il gioco
non espone nessuno di questi dati, la build mantiene il blocco di sicurezza,
conservando almeno il primo lavoratore e spiegando nel report il motivo.

Nel nuovo report `school_staff.native_cafeteria_schedule_probes` include
`native_tagged_stations_found`, `ea_hsy_objects_found` e
`ea_hsy_tuning_id`. Sono prove del riconoscimento dei banconi, **non**
una certificazione che 3 dipendenti lavorino contemporaneamente: questo
si misura nei veri job di servizio EA.
