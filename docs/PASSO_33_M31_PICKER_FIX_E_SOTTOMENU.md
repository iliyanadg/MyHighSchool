# Passo 33 — Diagnosi effettiva M29, correzione cumulativa M31 (31 ottobre 2026)

## Verifica M29 fatta nel gioco reale Mac
- Menu sulla cassetta postale presente con le 9 opzioni di Classe 1/2/3.
- `mhs28.roster` legge lo slot 11: Classe 1=2/8, Classe 2=2/8, Classe 3=0/8.
- I tre picker di iscrizione si aprono e consentono di selezionare adolescenti (nessuna iscrizione salvata in questa verifica).
- **Consulta iscritti** e **Rimuovi studenti** non aprono la finestra in nessuna classe.
- `mhs27.report` e `mhs29.report` danno entrambi esattamente:
  `ERROR | AttributeError: 'ImmutableSlots' object has no attribute 'get_max_selectable'`
- `EMPTY | Classe 3` e corretto per il registro vuoto.
- Nessuna modifica al JSON generata dai tentativi di apertura.

## Causa e patch
La fabbrica comune `_dialog_factory` in `src/m27_remove_ui/mhs27_remove_ui.py` costruiva `max_selectable` mediante `make_immutable_slots_class`, secondo una vecchia guida del 2015. Il gioco reale invoca invece `get_max_selectable()` sull'oggetto: l'ImmutableSlots non lo implementa.

La M31 **rimuove l'override** `max_selectable=allowed`: `UiSimPicker.TunableFactory().default` usa la propria regola nativa di selezione. Le righe vengono tuttora filtrate **soltanto** in base agli iscritti alla singola classe, limite di otto nel registro; `RemovalService` ricontrolla gli ID prima di qualsiasi scrittura. Questa scelta elimina l'oggetto incompatibile, ma il comportamento reale del nuovo popup va verificato.

Aggiunto regression test che simula la chiamata a `get_max_selectable()` del runtime e rifiuta un override manuale.

## Bundle M31
- Tutti i nove moduli Python di M30 + correzione M27, e tutte le 23 risorse della M30.
- **MY HIGH SCHOOL → Classe 1/2/3 → iscrivi, consulta, rimuovi** (sottomenu M30 non ancora testati nel gioco).
- Il formato del JSON e gli iscritti di slot 11 non vengono modificati.
- Solo file sperimentali `MHS_M31_SOTTOMENU_PICKER_FIX_TEST.package` e `MHS_M31_SOTTOMENU_PICKER_FIX_TEST.ts4script`.

## Sicurezza e test
- **Non installare** M29/M30 in contemporanea a M31. Salvare i file vecchi fuori dalla Mods, lasciare v1.6 e XML Injector.
- Chiudere The Sims 4. Testare **solo una copia di partita separata**, con backup cartella `MY_HIGH_SCHOOL_M25_TEST_DATA`.
- Primo test non scrivente: menu annidato Classe 1/2/3; consulta Classe 1 (2 ritratti), rimuovi Classe 1 (2 ritratti). Non eseguire `mhs27.removecommit conferma`.
- Se il picker non compare, leggere `mhs27.report` e `mhs29.report`; non ripetere tutte le opzioni.
- Solo se la UI si apre correttamente: provare la selezione e `mhs27.removepreview`, nessun commit.
- Comandi `commit` scrivono subito un JSON **esterno al .save** e non sono annullati dalla semplice uscita senza salvare.
- Le classi sono un **registro** di studenti, non ancora la frequenza fisica del liceo EA.

## Stato
Build CI M31: https://github.com/iliyanadg/MyHighSchool/actions/runs/41145949022
Test automatici non equivalgono a funzionamento in-game.
