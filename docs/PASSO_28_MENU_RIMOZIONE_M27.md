# Passo 28 — Nuove voci 'Rimuovi studenti', build sperimentale M27

La user ha chiesto **Rimuovi studenti — Classe 1** e
**Rimuovi studenti — Classe 2**. Le nuove opzioni devono mostrare solo
le foto e i nomi dei Sim effettivamente iscritti in quella classe,
selezionare 1–8, e consentire di rimuoverli dal registro **senza
eliminare il Sim**.

## Implementazione sorgente
- `src/m27_remove_ui/mhs27_remove_ui.py`: due
  `ImmediateSuperInteraction` nuove per il menu della cassetta,
  registrate in XML Injector e stessa categoria M25.
- Per mostrare il picker crea un `UiSimPicker` usando
  `candidate_rows(roster, classe, lookup)` dell'M26,
  cioè esclusivamente chi figura nell'elenco salvato di quella classe.
  La UI dinamica evita di assegnare tratti nascosti ai Sim.
- Click su ✓ prepara `_PENDING` e controlla slot e snapshot
  del registro prima di accettare i risultati.
- `mhs27.removepreview` mostra il riepilogo senza scrittura.
- `mhs27.removecommit conferma` rimuove gli iscritti, non i personaggi,
  nel **medesimo file JSON della M25**, per poter utilizzare le quattro
  iscrizioni della prova precedente. Il commit è atomico e non
  modifica le iscrizioni dell'altra classe.
- `mhs27.removecancel` annulla il gruppo preparato;
  `mhs27.report` registra gli errori del dialogo senza salvare.
- `tooling/build_m27_removal.py` genera .package 11 risorse
  (le 9 di M25, modificando SOLO snippet e due STBL; nuove 2
  interazioni) e .ts4script con M25+M2+M26+M27 compilati Python 3.7.
  Le funzioni già testate in M25 restano byte-identiche.
- `tests/test_m27_remove_ui.py` verifica 2 filtri, annullamento,
  blocco di ID di altre classi e altri slot, nessuna scrittura prima
  del commit e presenza nel DBPF.

## Avvertenze importanti
- **Il metodo UiSimPicker del 2026 non è ancora verificato nel gioco.**
  La base è un esempio originale documentato da scumbumbo:
  https://modthesims.info/t/547251
  Se l'API è cambiata, il popup potrebbe non aprirsi; in questo caso
  `mhs27.report` permette di rilevare l'errore senza scrivere file.
- Questo è un prototipo per il salvataggio **test** già riconosciuto.
  Non installarlo contemporaneamente a M25 perché duplicano menu e
  import dei moduli Python.
- Il registro JSON resta esterno al file .save; Save As e restore
  non sono sincronizzati. Non usarlo nella partita principale.
- La notifica arancione M25 è un bug distinto, ancora aperto.
- La rimozione non modifica EA school situations, ruoli o presenze.

## Prova in-game prevista
1. Con gioco chiuso rimuovere SOLO la coppia M25 dalla Mods,
   lasciare la v1.6 e XML Injector invariati.
2. Installare SOLO la coppia M27 compilata Python3.7.
3. Avviare la stessa partita di prova e controllare `mhs25.roster`.
4. Cassetta postale → M27 TEST → Rimuovi studenti Classe 1.
5. Deve comparire un picker di **soli 2 iscritti della Classe 1**;
   se non compare: `mhs27.report`, non salvare nulla.
6. Se compare, scegliere un Sim, premere ✓, usare
   `mhs27.removepreview` senza eseguire commit fino a verifica.
