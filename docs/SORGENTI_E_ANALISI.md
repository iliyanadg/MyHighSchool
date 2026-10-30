# Inventario dei sorgenti disponibili e percorso di lavoro

- **Base locale validata per l'avvio:** `MY_HIGH_SCHOOL_v1_6_Scelta_Aula_Giocabili.ts4script`. Il gioco si apre con questo script, ma non prova che tutte le sue funzioni siano corrette.
- **Sorgenti originali v1.6:** cartella `MY_HIGH_SCHOOL_v1_6_Scelta_Aula_Giocabili_SORGENTI` nell'archivio fornito dall'utente. In repository abbiamo importato per primo `mhs_registry.py`.
- **Prototipi v1.11 / v1.12 / v1.13:** materiale storico, non validato come versione finale. Non sostituire automaticamente la v1.6.
- **M0 menu:** originali XML in `src/experiments/m0_failed/`, etichettati *NON INSTALLARE*. Il gioco non si avviava con il relativo package.
- **Primi due prototipi UI:** falliti all'avvio; i sorgenti sono archiviati separatamente dall'utente.
- **Riferimenti EA:** `simulation.zip`, `core.zip`, tuning EA estratti e modulo picker; non includerli in questo repository.
- **Riferimento di terzi Sonozaki 2.2.1:** usare per analisi e confronto tecnico; non caricare il suo codice proprietario.

## Regole del progetto
1. Prima si studia il formato tuning/SimData, poi si genera un package con tool verificati.
2. Static tests **non dimostrano** che The Sims 4 si avvii né che la UI sia operativa.
3. Nessun nuovo file da mettere in Mods prima di una revisione esplicita, documentata e separata.
4. Nel repository: soltanto codice originale del progetto, documentazione e test.
5. Primo obiettivo tecnico: aprire il menu a cerchio sulla cassetta postale *senza bloccare l'avvio*.
