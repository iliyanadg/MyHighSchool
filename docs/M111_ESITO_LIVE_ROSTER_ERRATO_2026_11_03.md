# M111 — prima prova reale di appartenenza EA, 3 novembre 2026

## Fonte e condizioni
- Rapporto consegnato dalla giocatrice:
  `MHS_M111_NATIVE_SCHOOL_JOB_READBACK.json`, creato con
  `mhs111.arm` da casa e `mhs111.check` durante la prima lezione.
- Orario visibile nello screenshot: mercoledì, 10:33.
- `status=SINGLE_PHASE_JOB_MEMBERSHIPS_DIFFER`.
- Stesso salvataggio/giorno: `capture_same_save_day=true`.
- `roster_slot=11`, calendario originale EA
  `school_schedule_guid=277657`.
- `zone_spinup_assignment_flag_known=true`,
  `zone_spinup_assignment_flag_observed=true`. Questo *non*
  è prova indipendente che il Bouncer abbia terminato i job tardivi.
- `untrusted_observation_reasons=[]`,
  `wrong_native_job_guids=[]` (gli otto job osservati sono
  strutturalmente corretti per le situazioni EA che li contengono).
- `game_modified=false`, `no_ea_hooks_installed_by_m111=true`.

## Conteggio degli adolescenti e appartenenza ai job

| Misura osservata alle 10:33 | Risultato |
|---|---:|
| Studenti iscritti nel registro MHS | 16 (8+8) |
| Adolescenti umani istanziati sul lotto | 11 |
| Iscritti MHS istanziati | 4 |
| Iscritti MHS NON istanziati | 12 |
| Adolescenti istanziati ma NON iscritti | 7 |
| Iscritti nella **propria** aula tramite job nativi EA | **0** |
| Iscritti in job aula EA **sbagliato** | **1** |
| Adolescenti non iscritti in job aula EA | **7** |
| Situazione/ruolo Base `277733 / 277894` | 3 |
| Situazione Core `298052`, cinque job speciali | 5 |
| Job nativi lezione Classe 1 `304565/304703` | 3 |
| Job nativi lezione Classe 2 `304567` | 5 |

La riconciliazione calcolata è:
- dei 16 iscritti, **12 assenti**; 4 presenti fisicamente;
- otto adolescenti hanno job lezione EA, **7 non iscritti** e
  **1 iscritto alla Classe 1 erroneamente in Classe 2**;
- quindi nessuno dei 16 è nei job EA della classe MHS corretta.
- I job Base/Core osservati (3+5) coprono gli otto adolescenti
  osservati nei job lezione, ma non provano otto posti di banco né
  tutti gli adolescenti potenzialmente idonei del salvataggio.

**Questi sono conteggi provenienti dal gioco, non dai test sintetici.**
Non aggiungere nel repository i SimID personali del report; le
categorie e i contatori sono sufficienti per guidare la correzione.

## Quale causa il report ESCLUDE e quale indica

La prima causa è **a monte della seduta/blackboard routing**:
l'ammissione/assegnazione di adolescenti nei ruoli Base/Core e nella
situazione lezione EA non segue i 16 ID precisi del registro MHS.
Ci sono solo tre ruoli Base e cinque Core osservati; non sono i
13 NPC scelti più i tre giocabili a formare la scolaresca.

Il rapporto NON prova:
- che EA abbia un limite fisso di 11 Sim sul lotto;
- che il numero Base `(3,3)` sia esattamente `6-3 playable`;
- perché gli altri 12 iscritti non siano istanziati (filtro, richiesta,
  cap, sostituzione, eleggibilità restano cause distinte);
- che i cinque speciali Core siano assegnati ai futuri cinque
  NPC corretti (al momento sono NPC non iscritti);
- che al termine della seconda lezione il comportamento sia identico.

## Correzione mirata, senza rifare M110/M111

1. **Prima della generazione NPC del mattino** leggere il registro
   salvataggio con 16 ID, individuare i 3 giocabili realmente iscritti,
   e mappare i 13 NPC precisi a 5 ruoli Core e 8 inviti Base.
   Riutilizzare il manifesto verificato
   `mhs108_native_invitation.prepare_fixed_manifest`:
   NON inventare studenti o selezionarne altri in modo casuale.
2. **Sulle sole richieste originali EA** Base/Core per il liceo,
   vincolare inviti e filtri *prima* della decisione Bouncer.
   Riutilizzare `mhs108_native_precreate` e
   `mhs108_school_filter_scope` come candidati, senza installare
   moduli offline che non abbiano tutti i gates runtime reali.
3. **Capienza**, distinguere l'evidenza reale
   `get_long_term_situation_count(277733)=(3,3)`
   dal tuning storico di sei richieste. Il prototipo
   `mhs108_native_base_count` non può essere armato passando
   `ea_original_playable_adjustment=3` come assunzione.
   Verificare separatamente l'interazione con Bouncer soft cap.
4. **No-show**, impedire la conversione in richieste casuali
   `clone_for_replace` SOLO per inviti di studenti scelti e
   verificati, con rollback sicuro; mai per gli altri ruoli.
5. **Dopo l'assegnazione EA**, leggere gli effettivi membri dei job
   scolastici usando M111. Separare questo controllo dalla
   seduta fisica in aula e dalla verifica della giornata intera.

Il passo successivo NON è un'altra giornata diagnostica identica:
la prossima modifica al codice deve riguardare ammissione Base/Core
e filtro Bouncer dei soli 13 adolescenti scelti, usando i vincoli
sopra, poi una prova mirata su salvataggio di test.

**Stato:** errore esatto di roster/assegnazione confermato;
controller correttivo in gioco ancora non validato.
