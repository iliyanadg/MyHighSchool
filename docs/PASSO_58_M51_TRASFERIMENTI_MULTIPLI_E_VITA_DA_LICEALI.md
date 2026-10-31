# Passo 58 — M51: trasferimenti multipli con la spunta; requisito Vita da Liceali

## Test di persistenza confermato dalla creatrice (31 ottobre 2026)
L'utente ha **riavviato completamente The Sims 4** e verificato che gli stessi studenti della Classe 1 e Classe 2 risultano ancora assegnati nelle rispettive classi. Quindi il registro JSON M49 persiste sullo stesso save slot oltre il riavvio. Il file di registro è esterno ai salvataggi EA e le scritture possono sopravvivere anche al «Non salvare» del gioco; fare backup del JSON di prova.

## Bug trasferimenti confermato
L'utente ha selezionato `Classe 1 -> Trasferisci in Classe 3`, ma il menu permetteva di selezionare **un solo Sim alla volta** e **nessun trasferimento veniva salvato**. Analisi del vecchio `src/m32_transfer/mhs32_transfer_ui.py`:
- costruiva l'elenco dal servizio `_dialog_factory` M27 senza configurare un massimo multi-select;
- alla spunta memorizzava soltanto un oggetto `_PENDING` in memoria, senza chiamare `_STORE.save`;
- il trasferimento veniva materialmente scritto solo tramite `mhs32.transfercommit conferma` nella console trucchi, in contrasto con la UX approvata dall'utente.

## Soluzione M51, mantenendo le funzioni M50
- Sostituita la sola funzione `open_transfer_picker` di M32 con un `UiSimPicker` nativo che offre gli studenti **solo della classe sorgente**, permette la selezione multipla fino ai **posti liberi** nella classe destinazione e conferma l'intero batch in un'unica operazione con la **spunta ✓**.
- La X non modifica il registro. La spunta rilegge il save slot, ricontrolla che entrambe le classi siano abilitate, che il registro non sia stato modificato dopo l'apertura e che gli ID appartengano alla classe sorgente; quindi richiama `plan_transfer`, che usa `SchoolRoster.assign_many`, e salva una sola volta con `RosterStore.save`.
- Quando si trasferiscono tutti gli studenti della classe di partenza, basta selezionarli tutti nel medesimo picker; non si trasferiscono persone non selezionate.
- Nuova notifica di riuscita con numero spostati e conteggio per classe; nessuna notifica «nessuna modifica» per X.
- Caso capienza: Classe 3 con 5 iscritti -> al massimo 3 Sim trasferibili da Classe 1.
- Se una classe è piena, mostra una notifica esplicativa e non apre un picker destinato a fallire.
- Le iscrizioni M50 filtrano tutte le persone già registrate (in qualsiasi classe) e limitano l'UI ai posti rimasti. I registrati restano disponibili in Consulta/Rimuovi/Trasferisci.
- **Il pacchetto DBPF M51 è identico a M49/M50** (35 risorse, categorie e SimData di Lot51 già provate). I cambiamenti risiedono nei moduli Python `.ts4script` per iscrizioni e trasferimenti.
- Test `tests/test_m51_bulk_transfer.py`: tre trasferiti in un solo click, X non salva, callback duplicato non salva due volte, classe target quasi piena, target piena, configurazione disattivata durante il picker, registro mutato mentre picker è aperto. In più suite M50 per filtro, limite otto e trasferimenti non impliciti.

## Requisito esplicito del prodotto
La creatrice ha precisato che **MY HIGH SCHOOL — Classroom Control richiede obbligatoriamente l'espansione Vita da Liceali (High School Years, EP12)**: nessuna versione solo gioco base è prevista. Il controllo tecnico di presenza del pack va implementato e testato prima del rilascio pubblico: non dichiarare già attiva una protezione runtime in M51 soltanto perché il requisito è scritto. Rif.: https://thesims4moddersreference.org/reference/pack_data/ (EP12).

La configurazione default del liceo EA è **2 aule e, secondo le analisi del 2026 di SonozakiSisters, 11 adolescenti complessivi**; la capacità proposta dalla nostra mod resta **8 per classe, massimo 3 classi = 24 iscritti nel registro**, NON promessa di 24 Sim fisicamente presenti nel lotto. Rif. https://www.patreon.com/SonozakiSistersSims4/posts/high-school-2-2-153195289

## Stato
La compilazione CI `M51` e il primo Mac game-test devono passare prima di dichiarare risolti i trasferimenti. Il menu M45 e le iscrizioni M49 sono già verificati; non chiedere altri test di quelle funzioni. I trasferimenti effettivi del liceo EA, con allievi presenti nel lotto, restano da progettare.

## Test M51 minimo consigliato
1. Conservare M49 e copia JSON registro TEST. Chiudere il gioco; sostituire solo package+ts4script M49 con M51 (nessun duplicato).
2. Aprire salvataggio di prova; `Classe 1 → Trasferisci in Classe 3`; spunta su due studenti disponibili (o tutti se non supera i posti disponibili). Una sola conferma.
3. `Consulta Classe 1` e `Consulta Classe 3`: i selezionati devono sparire da Classe 1 e comparire in Classe 3, senza cambiare gli altri.
4. `Iscrivi Classe 1`: non devono comparire gli studenti già iscritti in nessuna classe; il numero selezionabile è limitato ai posti liberi.
5. Se qualcosa fallisce: non continuare a cambiare classi, ripristinare M49 e inviare l'errore.
