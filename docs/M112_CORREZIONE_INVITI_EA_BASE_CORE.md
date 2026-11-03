# M112 — Prima correzione mirata del roster, 3 novembre 2026

**Obiettivo pratico:** correggere la causa mostrata dalla M111: solo 4
iscritti su 16 presenti alle 10:33, con altri 7 teen e solo 3 Base +
5 Core NPC collocati nei job di lezione EA.

**Stato:** moduli M108 corretti e testati *offline* in Python 3.7,
**non** runtime Mac autorizzato, **non** controller 16/16.
Solo ramo `feature/m55-presenze-studente-test`; `main` intatto.

## Correzione A — guest list EA già riempita di NPC casuali

Modificato `src/m108_native_roster/mhs108_native_invitation.py`:
`SchoolNativeGuestSession._guest_list` può ora elaborare la
guest list *originale* EA quando questa contiene già NPC estranei
nei ruoli studente **Base 277894 o Core 278965, 278966, 278967,
278968, 303765**.

Prima: se la lista conteneva uno studente vanilla, il prototipo rifiutava
del tutto l'operazione. Adesso, SOLO con il segnale verificato
`original_ea_school_guest_takeover_verified=true` e con contesto
di chiamata scuola/save/day/zone valido:
- i vecchi guest dei soli job studente originali vengono esclusi
  dal nuovo clone (la guest list EA di origine **non viene mutata**);
- nella lista clonata entrano uno degli otto ID **Base** del registro
  oppure i cinque NPC **Core manualmente assegnati**, con
  `accept_alternate_sim=false`;
- gli insegnanti rimangono, mantenendo ruolo e identità originali;
- ospiti/job inattesi, duplicati nello stesso job, teacher iscritto
  come adolescente e contesti non verificati => **rifiuto**;
- l'adattatore `mhs108_native_precreate` continua a invocare il
  metodo nativo EA una volta sola, mantenendo rollback e invarianti
  originali. Nessuna generazione casuale da MHS.

Questa non è una licenza per cancellare ospiti in altre situazioni o
assegnare automaticamente i cinque ruoli speciali.

## Correzione B — le tre situazioni Base realmente osservate da EA

M110 ha registrato da vero EA `(3,3)` per Situation Base `277733`.
M111 ha trovato **tre Sim** nei job Base `277894`, più cinque Core.

Modificato `src/m108_native_roster/mhs108_native_base_count.py`:
il callback originale `WeeklyScheduleDay.get_long_term_situation_count`
continua a essere chiamato una volta sola, poi il wrapper conserva
internamente **il valore originale restituito nella stessa chiamata**.
Se il valore è esattamente `(3,3)`, i GUID delle due schedule scolastiche
e la situazione Base coincidono, il piano Core è già congelato e ogni
gate runtime preesistente è stato verificato, può PROPORRE `(8,8)`.

Non assume che `3 = 6 - 3 playable`. Non estende il conteggio ad altri
calendari/ruoli. Una semplice chiamata alla funzione pura con un
valore `(3,3)` NON autorizza la modifica: il nuovo ingresso usa la
ricevuta del metodo originale all'interno dello specifico wrapper.

## Prove automatiche effettive

- `tests/test_m112_native_guest_takeover.py` (10 test nuovi).
- `tests/test_m112_native_count_and_admission.py` (4 test nuovi).
- Rieseguite anche le suite M108: inviti, precreate, Base count.
- GitHub Actions Python3.7 dedicata:
  https://github.com/iliyanadg/MyHighSchool/actions/runs/41679868871
  **conclusione success**.
- Il test integrato offline crea esattamente 8 inviti Base + 5 Core
  da liste originali già occupate e verifica 13 ID selezionati,
  senza alterare gli originali. **Nessun test in-game di 16 spawn.**

## Prossima integrazione necessaria per una beta correttiva vera

Non distribuire una nuova diagnostica che ripeta M111. Occorre un
**unico controller di attivazione scolastica** che, prima che EA crei le
situazioni mattutine:

1. rilegga il registro per-save e identifichi i tre playable + tredici
   NPC; i cinque Core vanno presi SOLO dal registro esplicito
   `mhs97_core_role_store.CoreRoleStore`. Se mancano ruoli manuali,
   BLOCCARE e chiedere di configurarli, senza assegnare automaticamente.
2. identifichi realmente gli owner EA (M109), il primo inizio calendario
   e l'identità save/lotto/giorno (M110), senza affermare automaticamente
   che i precedenti log autorizzino la nuova sessione.
3. verifichi prima dell'installazione i filtri nativi degli NPC scelti,
   l'ammissione mirata nel Bouncer, il blocco di fallback casuale e il
   soft cap NPC: questi gate non sono ancora tutti alimentati da
   sorgenti **live** verificabili. Non passing flag sintetici `True`.
4. installi in modo **atomico** i soli hook compatibili (Base count,
   precreate, school_filter_scope, no_show_guard, unified lessons,
   post-Bouncer observer) con rollback; il ramo M109 ne contiene
   già l'ordinamento e i test offline.
5. acquisisca l'assegnazione reale 13 NPC + 3 playable e i job
   corretti per ciascuna classe; poi, **separatamente**, verifichi
   seduta e routing ai banchi EA.

Il primo step che cambia il comportamento del gioco sarà quindi
l'attivazione nativa integrata, non un'altra osservazione. **La M112
qui non ha una .ts4script da installare** e non è una mod completa.
