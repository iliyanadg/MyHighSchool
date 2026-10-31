# Passo 61 — M53: «Personale scolastico» scegliendo esclusivamente Sim esistenti

Decisione confermata dalla creatrice, dopo la M52 verificata nel gioco su Mac:

- Usare **soltanto «Scegli Sim esistente»** (giovani adulti, adulti, anziani), comprese famiglie non giocate / NPC fuori dalle famiglie giocate, tramite SimInfoManager dell'intero salvataggio.
- **Preside**: massimo **1**, nominabile e sostituibile.
- **Professori**: **1 per classe/aula attiva**, 2 normalmente e 3 se Classe 3 abilitata. Assegnazione e sostituzione per classe indipendente.
- **Bidelli**: massimo **2**.
- **Addetti mensa**: massimo **3**.
- Lo stesso Sim non può ricoprire contemporaneamente due ruoli nel registro.
- Nessun CAS, generazione casuale o aggiunta di nuovi NPC, perché l'utente ha scelto esplicitamente Sim già presenti.
- Spunta ✓ di un picker = assegnazione, sostituzione o rimozione immediata; X = nessuna modifica; senza un secondo dialogo né console.
- Dati persistenti per save slot in un NUOVO JSON `Personale_slot_<slot>.json`, accanto agli attuali `Registro_slot_*.json` e `Impostazioni_slot_*.json`. Nessun cambio del registro iscrizioni né del salvataggio EA.
- Il numero di persone selezionabili nel picker dipende dai posti vacanti; i candidati sono adulti non già assegnati a un altro ruolo. I Sim rimossi restano nel gioco e possono essere riassegnati.
- Un eventuale Sim morto/scomparso richiederà in futuro segnalazione e sostituzione manuale o temporanea. Non creare automaticamente un NPC non richiesto.

## Menu progettato e implementato negli XML/SimData M53

```
MY HIGH SCHOOL
 ├─ Classe 1                         [M52 invariata]
 ├─ Classe 2                         [M52 invariata]
 ├─ Classe 3                         [solo se attiva]
 ├─ Personale scolastico             [NUOVO]
 │   ├─ Preside
 │   │   ├─ Scegli / sostituisci preside
 │   │   ├─ Rimuovi preside
 │   │   └─ Consulta preside
 │   ├─ Professori
 │   │   ├─ Assegna / sostituisci prof. Classe 1
 │   │   ├─ Rimuovi prof. Classe 1
 │   │   ├─ Assegna / sostituisci prof. Classe 2
 │   │   ├─ Rimuovi prof. Classe 2
 │   │   ├─ Assegna / sostituisci prof. Classe 3 [solo se Classe 3 attiva]
 │   │   ├─ Rimuovi prof. Classe 3 [solo se Classe 3 attiva]
 │   │   └─ Consulta professori
 │   ├─ Personale mensa
 │   │   ├─ Aggiungi addetti mensa (max 3)
 │   │   ├─ Rimuovi addetti mensa
 │   │   └─ Consulta mensa
 │   ├─ Bidelli
 │   │   ├─ Aggiungi bidelli (max 2)
 │   │   ├─ Rimuovi bidelli
 │   │   └─ Consulta bidelli
 │   └─ Riepilogo personale scolastico
 ├─ Impostazioni                     [M52 invariata]
 └─ Disattiva MY HIGH SCHOOL        [M52 invariata]
```

## Dettagli tecnici

- `src/m53_staff/mhs53_staff_store.py`: validazione rigorosa, registry per slot, atomic JSON write, fingerprint e limite per ruolo.
- `src/m53_staff/mhs53_staff_ui.py`: nativa `UiSimPicker` per adulti di tutto il salvataggio, 17 azioni, conferma via spunta, notifica di successo.
- `tooling/build_m53_staff_management.py`: M52 originale (35 TGI) invariata salvo STBL e iniettore XML, aggiunge **5 categorie+SimData Lot51** e 17 interaction tunings. Recuperata funzione FNV1-32(lowercase) per hash del nome SimData a 0x24 e _parent TableSetReference **nel blocco alto di 32 bit** a 0x5c, preservando l'annidamento che M44/M45 hanno sbloccato.
- `src/m39_visibility/mhs39_visibility_ui.py`: aggiunte classi M53 con il gate di visibilità M45 e della Classe 3 senza modificare le 19 SPECS originali.
- `tests/test_m53_staff_management.py` verifica capienza, unicità, sostituzione, rimozione multipla, persistenza, anti-stale/slot, 10 categorie/SimData e tutte le etichette IT/EN.
- `M53` compila 19 moduli Python 3.7 e un pacchetto DBPF con 62 risorse.

## Limiti non ancora implementati

Il nuovo personale **è assegnato soltanto nel registro esterno TEST**. I Sim scelti non sono ancora forzati ad apparire come professori, preside, mensa o bidelli sul lotto di **Vita da Liceali (EP12)**. Non sono implementate: l'integrazione del personale EA, le assegnazioni lavagna/aula, la presenza reale di 8 studenti per aula (24 massimo nel registro), il filtro tecnico che impedisce di usare la mod senza EP12, e la sostituzione per decesso / CAS / generazione NPC (queste due ultime non richieste). Informare chiaramente l'utente che M53 è il registro del personale, non ancora gestione degli NPC EA.

## Mac test consigliato (non eseguito)

Con backup della M52 e di `MY_HIGH_SCHOOL_M25_TEST_DATA`, installare esclusivamente i due file M53. Aprire `MY HIGH SCHOOL → Personale scolastico → Preside → Scegli / sostituisci preside`: deve comparire un selettore con Sim giovani adulti/adulti/anziani. Scelto un Sim, premere ✓; riprendere `Consulta preside` e verificare che appaia. Poi assegnare prof. Classe 1, due bidelli e tre addetti mensa sul save TEST, verificando che il selettore blocchi selezioni oltre capienza.
