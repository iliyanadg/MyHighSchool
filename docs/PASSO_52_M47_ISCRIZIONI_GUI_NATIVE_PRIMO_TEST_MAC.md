# Passo 52 — M47: selettore studenti + conferma nativa GUI (31 ottobre 2026)

## Stato
La M45 è la baseline menu e visibilità **confermata nel gioco Mac**. La M46 ha aggiunto un motore di preview e conferma senza UI. La M47 è stata ora **compilata**, con tutti i test offline superati, ma non ancora provata in The Sims 4. Non sostituire la baseline in modo permanente senza un test Mac.

Build/artefatto: https://github.com/iliyanadg/MyHighSchool/actions/runs/41207267578
Nome artefatto: `MHS_M47_NATIVE_GUI_ISCRIZIONI_TEST`
ZIP nella conversazione: `MHS_M47_NATIVE_GUI_ISCRIZIONI_TEST.zip`
File:
- `MHS_M47_ISCRIZIONI_CONFERMA_GUI_TEST.package`
- `MHS_M47_ISCRIZIONI_CONFERMA_GUI_TEST.ts4script`

## Modifiche
- Il package conserva **tutte e cinque** le categorie e le SimData Lot51 originali M45, le 35 identità delle risorse, tutte le stringhe e gli altri 19 comandi visibili; sono cambiati solo i tre tuning XML «Prepara iscrizione Classe 1/2/3».
- I tre tuning ora eseguono un'interazione `ImmediateSuperInteraction` (struttura modellata sulla già esistente interazione M27) con il mixin di visibilità M45 e chiamano il nuovo codice `mhs47_enrollment_ui.py`. Non usa più il percorso `actor_continuation` di M25, sul quale non avevamo conferma che il batch multi-sim fosse completo.
- Il modulo `mhs47_enrollment_ui.py` apre un `UiSimPicker` con tutti i teen del save, incluso chi non è nella famiglia attiva, fa scegliere i Sim e avvia `preview_enrollment` senza scrivere. Quindi mostra una `UiDialogOkCancel` separata, con numero scelti, cambiamenti e posti occupati.
- Una callback su conferma positiva (una sola volta) invoca `confirm_enrollment` di M46 con doppio controllo di slot, classe attiva, roster hash, età e capienza 8. Annullamento o selezione errata non salva nulla. Esito comunicato da `UiDialogNotification`.
- Anche se scrive il registro esterno M25 TEST, la mod **non controlla ancora la presenza al liceo EA**. Lo stato del salvataggio EA e il JSON esterno possono divergere se il giocatore ricarica una partita precedente: usare solo il save test.
- Si compila su Python 3.7 e genera 17 moduli .pyc (15 M45 + M46 engine + M47 UI).

## Test automatici
- Tutta la suite repo su Python 3.7: PASS.
- 5 nuovi test M47 controllano che i tre tuning abbiano la classe nuova, che le altre 32 risorse rimangano invariate, che l'archivio includa 17 moduli e che una callback Cancel non possa scrivere nemmeno se viene invocata di nuovo.
- Nuovi 10 test M46 di transazione e protezione contro slot cambiato, classe disabilitata, registro obsoleto, capienza piena: PASS.

## Incertezza di compatibilità
La factory `UiSimPicker.TunableFactory().default` è modellata sulla M27 e gli esempi pubblici, ma **non è ancora stata verificata con la versione attuale del gioco** per un picker di tutti gli adolescenti. Lo stesso vale per `UiDialogOkCancel.TunableFactory().default` e per la possibilità di scegliere più studenti contemporaneamente con la policy di default della factory. Se la GUI non si apre, non dichiarare il lavoro completato.

## Prova Mac raccomandata
1. Chiudere il gioco e **fare backup del file/dir `MY_HIGH_SCHOOL_M25_TEST_DATA`** e del save test, perché il JSON esterno non segue la funzione Salva/Non salvare di The Sims 4.
2. Rimuovere solo i due file M45 e collocare al loro posto soltanto i due file M47; lasciare le altre mod installate. Tenere la M45 fuori Mods per ripristino.
3. NEL SAVE TEST: cassetta -> MY HIGH SCHOOL -> Classe 1 -> Prepara iscrizione Classe 1. Verificare se il picker mostra adolescenti e permette selezione.
4. Scegliere UN adolescente non già nella Classe 1, poi premere la spunta sul picker: deve aprirsi una **seconda** finestra con i dettagli e due scelte.
5. **Prima fare Annulla**, riaprire e verificare che nulla sia stato iscritto. Solo dopo eventuale backup confermare un singolo Sim TEST e verificare la consultazione, anche dopo chiusura/riavvio.
6. In caso di nuove eccezioni, chiudere subito senza salvare, rimuovere M47 e ripristinare M45. Se è stata fatta una conferma con scrittura su JSON, ripristinare anche il backup del registro esterno (uscire senza salvare non fa rollback del JSON).

**Non modificare categorie/sottocategorie/SimData Lot51 ormai funzionanti.** Prima provare la GUI nativa con due screenshot (picker e conferma); non richiedere altre versioni o prove sui menu.

Fasi dopo test GUI: conferme native per rimozioni e trasferimenti, compatibilità pausa completa, persistenza e controllo reale scuola EA.
