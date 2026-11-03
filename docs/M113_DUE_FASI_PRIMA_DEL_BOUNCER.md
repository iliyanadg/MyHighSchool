# M113 — Attivazione scolastica in due fasi (offline, non ancora installabile)

## Perché serviva

M111 ha mostrato 4 iscritti su 16 sul lotto e nessun iscritto nel
job della propria classe alle 10:33. M112 propone di sostituire gli
inviti EA casuali Base/Core e il numero di situazioni Base da 3 a 8,
ma mancava il momento corretto dell'intervento.

A casa conosciamo save, giorno, 16 iscritti, tre giocabili e cinque
ruoli Core scelti; NON conosciamo l'ID del lotto scolastico. Dopo
il viaggio, il Bouncer può già aver selezionato gli NPC.

## Implementazione del modello di controller M113

Il file src/m113_controller/mhs113_early_school_entry.py:

1. Congela i 16 iscritti (8+8), i 3 giocabili e i 5 ruoli Core
   manuali, senza assegnarne automaticamente altri.
2. Dal lotto di casa installa UN wrapper dormiente sul metodo
   originale WeeklyScheduleDay.get_long_term_situation_count.
   Ogni chiamata fuori scuola passa invariata.
3. Alla prima invocazione nativa Base 277733 su calendario
   277657/279958 osserva il valore originale (3,3). Chiama
   sempre EA una sola volta, prima di qualsiasi altra azione.
4. Verifica i campi richiesti dal futuro provider live: stessa
   identità save/day, nuova school_zone, provenienza del callback,
   finestra prima dello schedule e i gate M109.
5. Solo dopo può costruire il manifesto M108 con school_zone
   corretto e congelare le prenotazioni Core.
6. Installa in modo atomico i cinque stage rimanenti:
   native_precreate, school_filter_scope, no_show_guard,
   unified_lessons, post_bouncer_observer; registra i rollback
   PRIMA di ogni installazione.
7. Se tutti riescono, propone il valore Base (8,8).
   Se una fase fallisce, restituisce l'originale e ripristina
   gli interventi precedenti. Non tocca altri hook.
8. Supporta l'eventuale secondo calendario EA sullo stesso lotto,
   senza creare un'altra sessione e senza cambiare il conteggio
   quando sono già partiti gli inviti Base.

Il file src/m113_controller/mhs113_live_home_bridge.py:

- legge il registro MHS attivo, i dati dei Sim adolescenti
  e i 5 ruoli Core dal ponte M105/M97 già esistente;
- verifica lo slot reale non-scratch, il giorno EA e il lotto casa;
- blocca famiglie/salvataggi/ruoli/registro non corrispondenti;
- non installa hook, non genera NPC e non salva modifiche.

## Limiti REALI ancora aperti

Questi moduli sono un MODELLO offline, non un controller attivo.
I test Python3.7 eseguono callback EA finti e veri moduli M108
per l'invito su manager sintetici: non certificano spawn reali.

Per una prima beta correttiva serve collegare e verificare:
- provider con provenance save/day/zone da chiamate EA originali;
- session_factory con guest/job nativi realmente risolti;
- stage_graph_factory con hook M108 e relativi rollback reali;
- filtro mirato nel Bouncer, non-show e capienza NPC;
- report post-Bouncer dei 13 NPC precisi più tre giocabili,
  con successiva prova routing ai banchi.

Le prove dei 5 Core devono utilizzare solo il registro M97,
senza promuovere un Sim a un ruolo non scelto.
Non è autorizzato impostare gate finti a true nel gioco.

Il workflow .github/workflows/m113-school-entry-integration.yml
verifica i moduli con Python 3.7 e non crea alcun file installabile.
Non installare M113 adesso. Ramo sperimentale separato da main.

## Collegamento reale agli oggetti invito EA

Aggiunto src/m113_controller/mhs113_native_guest_factory.py.
Con import al momento dell'uso, legge da
services.get_instance_manager(Types.SITUATION_JOB) gli OGGETTI EA
originali per i sei job scolastici (Base 277894, Core 278965,
278966, 278967, 278968, 303765), verifica i loro guid64
e carica il costruttore originale
situations.situation_guest_list.SituationGuestInfo con la
finalita SituationInvitationPurpose.INVITED.

Usa questi oggetti nativi per creare SchoolNativeGuestSession,
senza scegliere altri Sim, inviare inviti, installare wrapper,
creare situazioni o alterare il salvataggio. Se un job manca,
il GUID è sbagliato oppure manca il costruttore EA, blocca
la preparazione e non utilizza oggetti fittizi.

Test: tests/test_m113_native_guest_factory.py (4 casi offline,
oggetti EA emulati). Questo risolve il percorso del
session_factory nativo, NON l'origine/gate Bouncer e NON
l'attivazione installabile.
