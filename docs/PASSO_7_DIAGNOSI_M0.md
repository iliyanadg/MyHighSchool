# Passo 7: diagnosi e prima correzione del menu M0 (solo sorgenti)

**Situazione verificata:** il gioco non si avviava con M0, ed è tornato ad avviarsi togliendo soltanto quel package. La causa esatta non è dimostrata.

## Due problemi individuati
1. Il package M0 conteneva 8 risorse, una categoria `PieMenuCategory` ma nessuna risorsa `SimData` associata. Tutte le 14 categorie nella copia di Sonozaki analizzata ne possiedono una. La differenza è reale, ma non è ancora una diagnosi definitiva del mancato avvio.
2. In M0, le due interazioni di conferma collocavano `basic_extras` direttamente sotto `ImmediateSuperInteraction`. Il pattern trovato in Sonozaki per mostrare una notifica passa da `outcome > single > actions > basic_extras`: abbiamo corretto questo posizionamento in **due file XML di esempio non compilati**.

## File creati
- `tooling/m0_tuning_audit.py`: controlla link tra categoria, picker, conferme e injector, oltre ai due problemi strutturali.
- `tests/test_m0_tuning_audit.py`: sei test di regressione che *si aspettano* errori nel M0 fallito.
- `src/experiments/m1_unbuilt/ConfirmClass1.xml` e `ConfirmClass2.xml`: notifiche spostate sotto l'outcome, **non installabili**.
- `src/experiments/m0_failed/resource_inventory.json`: inventario non proprietario della struttura del package fallito.

**Non è stato creato un nuovo package da mettere nella cartella Mods.** SimData, completezza dei tuning e caricamento nel gioco restano da verificare. GitHub Actions esegue solo controlli del codice.
