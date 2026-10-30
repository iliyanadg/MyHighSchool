# Passo 12 — Controllo sorgenti M1: interazioni e cassetta postale

Data: 30 ottobre 2026. **NESSUN package installabile prodotto.**

## Cosa abbiamo verificato direttamente

Nel materiale originale XML Injector v4.2 fornito dall'utente, l'esempio
`Scumbumbo_XmlInjector_AddInteractionTest_Modders.SnippetTuning.xml`
mostra il formato:

- `<I c="XmlInjector" i="snippet" m="xml_injector.snippet">`
- `add_interactions_to_objects` + `object_selection` in variante
  `object_list` con tuning cassetta postale **14940** e **133176**;
- un elenco `_super_affordances` dei tuning d'interazione da aggiungere.

La mod Sonozaki, studiata **solo come riferimento**, usa
`SimPickerInteraction` nativo (`interactions.base.picker_interaction`),
`actor_continuation` e `PieMenuCategory`. Sonozaki usa invece la libreria
Lot51 Core per l'iniezione: è un sistema alternativo, **da non mescolare**
con XML Injector.

## Cosa è stato aggiunto su GitHub
- `src/experiments/m1_unbuilt/Injector.xml`: snippet **originale** per M1
  che usa XML Injector v4.2, non Lot51 Core. Include solo le due cassette
  postali EA standard e a parete, non pretende copertura di ogni modello.
- `tooling/m1_mailbox_validation.py`: controlla struttura dello snippet,
  riferimenti alle due interazioni native e all'ID della nuova categoria.
- `tests/test_m1_mailbox_validation.py`: sei test, inclusi casi deliberatamente
  errati per verificare che il controllo blocchi link sbagliati.

## Cosa NON è ancora accertato
- La coerenza sintattica con lo snippet XML Injector **non garantisce**
  il caricamento corretto della mod.
- I due picker devono ancora essere validati integralmente secondo il TDESC
  e gli esempi di gioco **1.129.39.1230**, non soltanto attraverso i campi
  comparabili con Sonozaki.
- Il vecchio M0 falliva all'avvio per una ragione non confermata; la SimData
  mancante è un difetto verificato, ma **non prova** la causa.
- La copertura di tutte le cassette postali e del PC resta un traguardo
  successivo.
- Per testare in game serve prima un pacchetto completo con tuning, SimData,
  STBL e snippet, assemblato e verificato senza alterare la v1.6.

Nessuno dei file M1 deve essere installato nella cartella Mods.
