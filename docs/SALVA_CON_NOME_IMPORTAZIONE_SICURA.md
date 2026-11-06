# MY HIGH SCHOOL — Recupero configurazione dopo «Salva con nome»

**Funzione in questa revisione:** importare nella nuova partita, in modo
non distruttivo, i 4 file esterni della precedente partita:
- `Registro_slot_ID.json` (studenti)
- `Impostazioni_slot_ID.json` (gestione scolastica)
- `Personale_slot_ID.json` (professori, preside, bidelli, mensa)
- `MHS97_RuoliSpeciali_slot_ID.json` (cinque studenti con ruoli speciali)

Gli ID del nuovo salvataggio sono differenti; la mod non legge il
registro della partita precedente per errore, ma ricostruisce gli
stessi quattro record con il **nuovo ID del salvataggio**.

## Un solo intervento nel gioco

1. Conserva una copia di sicurezza di `saves` e dell'intera cartella
   `MY_HIGH_SCHOOL_M25_TEST_DATA`. Installa soltanto la coppia build di
   questa revisione. La precedente build resta un fallback.
2. **Carica la nuova partita creata con «Salva con nome».** Per eseguire
   una copia persistente, entra prima nella tua casa anziche caricare
   direttamente il liceo: la partita deve esporre uno slot EA reale,
   non un possibile slot temporaneo usato durante i viaggi.
3. Da casa apri la console ed esegui **`mhs148.copia`**. Se la mod
   trova un'unica partita originale compatibile, importa o completa
   automaticamente i quattro registri. Non devi riscegliere 16 studenti,
   5 ruoli speciali, professori, preside, bidelli e mensa.
4. Se compare **`MULTIPLE_SOURCE_SAVES_CHOOSE_SLOT`**, esegui
   **`mhs148.sorgenti`** e osserva l'elenco degli ID delle partite
   precedenti compatibili. Quindi indica quella corretta:
   **`mhs148.copia_da 41`** (41 e solo un ID di esempio).
5. Se il risultato segnala successo, da casa esegui `mhs148.arm`.
   Le assegnazioni avranno effetto nella **prossima giornata scolastica**.

## Salvaguardie

- Prima di scrivere, ogni Sim dei 16 iscritti e ogni lavoratore deve
  esistere nel salvataggio corrente con eta/specie idonee. Sono richiesti
  due gruppi da 8, 5 NPC iscritti in 5 ruoli core e almeno un adolescente
  giocabile appartenente agli iscritti. Una partita diversa viene respinta.
- Il comando non sceglie automaticamente fra sorgenti ambigue.
- **Non sovrascrive mai** registri gia presenti. Se un file della nuova
  partita corrisponde esattamente ai dati da importare, lo conserva e
  aggiunge soltanto i file ancora mancanti. Se differisce, rifiuta la
  copia. E sempre possibile ripetere il comando senza duplicare.
- I file del salvataggio EA non sono mai toccati. I registri della partita
  originale restano invariati. L'annullamento delle modifiche al registro
  della partita originale non viene trasferito al nuovo salvataggio.
- Una partita caricata direttamente **a scuola durante la giornata** non
  puo recuperare retroattivamente gli inviti EA gia assegnati. Questo
  comando copia la configurazione per le giornate future, non teletrasporta
  studenti o crea situazioni scolastiche a meta giornata. Il recupero
  completo del gameplay in un caricamento diretto al liceo richiede
  ancora una soluzione separata e una verifica nel gioco.
- Il collaudo offline verifica schema, isolamento, idoneita, copia
  incompleta e rifiuto dell'overwrite, ma **non certifica** che i 16 Sim
  saranno presenti nella partita reale senza un test The Sims 4.
