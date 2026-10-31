# Passo 63 — M55: prima convocazione controllata di UNO studente iscritto

## Baseline verificata (31 ottobre 2026)

La M54 (menu, iscrizioni/rimozioni/trasferimenti, personale solo umano) ha superato il test in gioco sul Mac. Le sue **62 risorse DBPF**, il menu e le 10 categorie con SimData Lot51 sono la baseline da conservare.

**Nuova azione di prova** in `MY HIGH SCHOOL → Classe 1 → M55 TEST - Convoca 1 studente Classe 1`. Non si usano console, generazione di NPC né nuove situazioni automatiche per tutti gli iscritti.

## Funzione del test

- UI nativa: mostra soltanto gli adolescenti umani **già iscritti** alla Classe 1 del registro esterno. Spunta ✓ = singolo tentativo; X = nessuna modifica.
- Dopo ✓ verifica **slot del salvataggio**, attivazione MY HIGH SCHOOL, iscrizione ancora valida, età e specie, e presenza di una situazione liceale EA `situation_HighSchool_Active_NPC_Base_Student` (GUID 277733).
- Se il Sim è già membro di una situazione Base Student osservabile, mostra «già presente» senza duplicare.
- Se EA espone il ruolo `job_HighSchool_Active_Base_NPC_Student` (GUID 277894), invia **una sola** richiesta `create_situation` con esattamente il Sim scelto. Blocca i tentativi ripetuti per Sim+slot nella stessa sessione; nessuna invocazione automatica o in background.
- **Non** scrive il registro, non tocca il personale, **non** modifica i tratti EA per cambiare classe, non programma il ritorno quotidiano e non forza la presenza fisica in aula.
- Se il salvataggio al liceo è identificato come slot 0 o lo school-day non risulta riconoscibile, **non** tenta di convocare nessuno. È un limite noto da studiare, NON un invito a bypassare la verifica.
- La prima prova è sulla Classe 1; lo scopo della M55 non è ancora portare 24 Sims insieme nello stesso lotto.

## Composizione

`tooling/build_m55_attendance_trial.py` parte dal package M54/M53, conserva 59 TGI byte-identici, aggiunge una sola interaction di Classe 1, modifica esclusivamente l'iniettore e i due STBL per esporre il comando. Package: 63 risorse, sempre 10 categorie e 10 SimData. La ts4script contiene i 19 moduli M54 + i 2 nuovi moduli M55 = 21; compilazione **Python 3.7**.

`tests/test_m55_attendance_trial.py` controlla la selezione singola, il controllo duplicati, il gate alle situazioni e ai GUID EA, il singolo invio, l'assenza di alterazioni del menu M54, e il roundtrip DBPF.

## Test Mac quando la CI sarà verde

1. **Salvataggio TEST**, con copia separata dei dati esterni `MY_HIGH_SCHOOL_M25_TEST_DATA`. Non provare per la prima volta sul salvataggio narrativo principale.
2. Chiudere il gioco; conservare la coppia M54. Sostituire esclusivamente i due file M54 con i due file M55 della **stessa compilazione GitHub Actions**. Non installare M54 e M55 insieme.
3. Avviare il salvataggio di prova con MY HIGH SCHOOL attiva e almeno 1 adolescente umano iscritto in Classe 1.
4. Visitare il lotto del liceo di Copperdale durante una giornata attiva in cui siano visibili studenti EA. Aprire MY HIGH SCHOOL → Classe 1 → M55 TEST e selezionare **un solo** studente non già presente.
5. Dopo ✓, riferire il testo esatto del messaggio e verificare **a vista** se lo studente arriva e se può seguire le lezioni. Non interpretare «richiesta inviata» come conferma dell'arrivo.
6. Se appare «slot non verificabile», «giornata liceo non rilevata», errori API o eccezioni, **fermarsi**; non ripetere rapidamente. Conservare M54 come rollback.

## Cosa resta dopo questo test

Presenza giornaliera persistente, sostituzione dei NPC casuali di EA, prof. e preside attivi, routing lavagne/aula 1/2, Classe 3 virtuale e controllo carico 24 adolescenti **non sono implementati**. La terza aula non ha un ruolo EA preesistente; non possiamo fingere che il test M55 la abiliti.

**Stato**: M55 codice e test offline; da validare in GitHub CI e poi nel gioco Mac, prima di qualunque merge in main.
