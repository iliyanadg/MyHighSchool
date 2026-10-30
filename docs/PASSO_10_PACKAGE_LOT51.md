# Passo 10 — Package esportato da Lot51: controllo effettivo

L'utente ha fornito `MHS_MainMenu_LOT51_TEST.package` direttamente da
Lot51 Tuning Builder. La copia binaria della prova è archiviata in
`tests/fixtures/lot51_category_only.dbpf` con un'estensione deliberatamente
diversa da `.package`, per **non confonderla con una build installabile**.

- Dimensione: **649 byte**.
- SHA-256: `ab2ecb3c51485d27f12dfbe5844df5e610e486abe88dce2395f1872872b53c3c`.
- Resource 1: **PieMenuCategory** (`0x03E9D964`, Group `0x00000000`).
- Resource 2: **SimData** (`0x545AC67A`, Group `0x00E9D967`), formato binario con firma `DATA`.
- Entrambe le risorse hanno lo stesso Instance ID `0xCA28A52FAEFBD0C3`
  (`14567074618947653827`).
- Entrambe sono compresse correttamente e le dimensioni decompressi tornano.

## Esito

**La SimData mancante nel vecchio M0 è ora disponibile in un export Lot51 con
categoria abbinata.** Gli attuali controlli statici del DBPF passano sul
file reale, oltre che sui pacchetti sintetici dei test. Tuttavia manca ancora
il resto della mod: interazioni, riferimenti all'oggetto cassetta postale,
testi STBL e controllo della compatibilità delle chiamate EA.

Questo file *da solo* non aggiunge alcuna voce funzionante nel gioco e
**non deve essere installato come prototipo pronto**. Non prova che il
precedente blocco d'avvio fosse dovuto solo alla SimData assente.

## Prossimo traguardo

Usare questo export Lot51 come **risorsa sorgente affidabile** e creare in un
ramo di sviluppo le interazioni *validate* e le stringhe mancanti. Il nuovo
pacchetto dovrà essere sottoposto a verifiche complete prima di qualsiasi
nuova prova in The Sims 4. Non copiare risorse EA o terze parti nel repo.
