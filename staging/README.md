# Importazione sorgenti v1.6 (procedura una tantum)

Questa cartella serve esclusivamente per ricevere **l'archivio preparato e verificato** con i sette moduli originali ancora mancanti.

Caricare `v1_6_missing_sources.tar.gz` qui tramite GitHub. Il workflow `.github/workflows/import-v1_6.yml`:
1. controlla il checksum SHA-256 dell'intero archivio;
2. verifica esattamente sette nomi di file e i singoli SHA-256;
3. estrae i **sorgenti testuali** in `src/legacy_v1_6/` senza sovrascrivere file preesistenti;
4. esegue compilazione Python e i test offline;
5. crea un commit con i sette file e rimuove l'archivio temporaneo.

**Non contiene una mod installabile.** I test Python non certificano l'avvio o le funzioni di The Sims 4.

Se un controllo fallisce, l'importazione si interrompe senza modificare i sorgenti su `main`.
