# M146 — Sorgenti EA aggiuntive ricevute il 4 novembre 2026

## Provenienza e verifica
L'utente ha inviato `zipnuovo4novembre.zip`, verificato direttamente come ZIP Sims 4 Studio: 4 XML tuning originali (2 Interaction, 1 Buff, 1 Situation), un SimData e file metadati Mac `__MACOSX` da ignorare. Queste sono **evidenze di tuning statico**, non prova del comportamento in gioco.

| Type | Nome EA | GUID |
|---|---|---|
| Interaction | `super_HighSchool_Active_CreateBook_Class` | 276782 |
| Interaction | `super_HighSchool_Active_UseBook_Class` | 276784 |
| Buff | `buff_Role_Highschool_Active_Player_AttendClass` | 276710 |
| Situation | `situation_Vendor_CafeteriaStation_HighSchool` | 278011 |

I quattro GUID e i nomi sono verificati negli attributi `s` e `n` degli XML esportati. La raccolta richiesta all'utente e' completa.

## Flusso giocabile EA confermato dagli XML
1. Il buff nascosto del giocabile `276710` elenca in `target_super_affordances` `276774 super_HighSchool_Active_Whiteboard_Class_Start`, ristretto agli oggetti con tag `Func_HighSchool_Active_Whiteboard`. Dunque il buff fornisce già un percorso originale verso la lavagna senza richiedere una seconda interazione inventata.
2. `276782 CreateBook_Class` genera un workbook nell'inventario e continua con `276784 UseBook_Class` sul `CreatedObject`. Le sue constraint ammettono `posture_Sit` e `posture_Stand`: non impone seduta al banco.
3. `276784 UseBook_Class` include `conditional_actions` che escono con `EXIT_NATURALLY` quando viene rimosso il buff `276710` del giocabile. Analoghe condizioni per NPC usano `276312`, `304592` e test di ore `279717/279723`. La gestione corretta della fine lezione deve privilegiare la disattivazione EA del ruolo/buff, non una cancellazione arbitraria di azioni in corso.
4. `276784` esprime preferenze per `SEATING_DESK=30` e `SURFACE_DESK=30` ma NON prenota un banco specifico: sedere non equivale a esservi obbligato. Eventuali riserve di 8 posti vanno progettate a livello dei target / job / route, con attenzione alla disposizione reale delle stanze.
5. Il buff `276710` azzera i moltiplicatori di autonomia dei motivi divertimento, fame e socialità: probabile inibizione della distrazione in lezione, senza dimostrazione di un routing puntuale.

## Mensa EA
`278011 situation_Vendor_CafeteriaStation_HighSchool` e' una `TendObjectSituation`: la coppia job/role del vendor e' `278010 situationJob_MarketStalls_Vendor_CafeteriaStation_HighSchool` / `278009 marketStalls_Roles_Vendor_CafeteriaStation_HighSchool`. La fase iniziale osserva `133181 marketStalls_Open` e passa al `tend_state` con timeout 540. Non e' un job di partecipazione degli studenti e non dimostra che gli NPC comprino o si siedano. Evitare di modificarlo finche' non sia dimostrato il collo di bottiglia reale delle interazioni degli studenti.

## Implicazioni per il passo successivo M146
- **Non introdurre un nuovo controller che spinga alla cieca `UseBook`:** e' una continuazione nativa della creazione quaderno; il collegamento `276710 -> 276774` già esiste.
- Usare la prova M145d (16/16 registrati, tutti istanziati alle 8:10, classe 2 in ritardo) per intervenire su **tempi, ruoli EA e targeting effettivo delle due lavagne**, preservando M145d `applied=True` sulle 8 materie.
- Distinguere l'assegnazione del registro, la presenza sul lotto, il job EA, la richiesta di inizio lezione, l'azione attiva, e il banco fisicamente occupato. Sono verifiche separate.
- Per fine giornata, osservare la perdita del buff/role EA, l'annullamento naturale dell'interazione e le eventuali richieste gia' in coda. Non forzare l'uscita dopo le 15 finche' non e' stato verificato chi invia gli ordini.
- Il file `MHS_M145_REPORT_COMPLETO.json` dell'ultimo test contiene **133 snapshots, ultima osservazione 14:09:11**, anche se `mhs145.report` e' stato eseguito alle 15:05. In M145 `_m141_capture` rifiuta campioni quando `in_school()=False` e `_m141_stop_trace` cancella il timer; la diagnostica M146 deve registrare una **chiusura terminale esplicita** (orologio, zona, flag scuola, contatore, cause stop) quando il monitor si interrompe, altrimenti l'assenza di dati viene scambiata per assenza di un comportamento.
- L'ultimo report M145d mostra `initial_native_accepted` Classe 1 `queued=False/EA_REJECTED` e Classe 2 `queued=True/EA_ACCEPTED`; i ruoli giocabili della seconda lezione non risultano sempre presenti. Serve correlare **origine e motivi del rifiuto** con i test nativi senza alterare la compatibilita' Zerbu.
- Prima di una build completa, predisporre test regressivi per due lezioni, 16 identità non duplicate, correttezza lavagna, nessun tentativo di nuova lezione dopo la fine, autospegnimento del monitor e ripristino dei tuning; niente dichiarazione di successo reale senza verifica Mac in partita.

## Non serve un'altra esportazione generale
Esistono gia' nel progetto i dati del vecchio Archivio(2).zip da 1067 XML (vedi docs/PASSO_76_MAPPA_SCHEDULE_EA_ARCHIVIO_2.md), il codice EA `weekly_schedule_zone_director.py` nella Library utente, gli XML delle otto lezioni e i file di questo ZIP. Non chiedere nuovamente estrazioni generaliste.
