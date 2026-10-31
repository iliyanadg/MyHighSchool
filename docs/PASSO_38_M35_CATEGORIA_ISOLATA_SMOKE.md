# Passo 38 — M35: prova isolata per capire la UI Exception delle categorie

**Motivo:** dopo la validazione in gioco della persistenza M34, l'utente vuole il menu
`MY HIGH SCHOOL → (Attiva/Disattiva) → Classe 1 / Classe 2 / Classe 3 opzionale → azioni`,
con conferme grafiche, operazioni in pausa e massimo otto studenti per classe.

### Perché una sola categoria

La M30/M32, che tentava di aggiungere tre PieMenuCategory nuove figlie della principale,
provocava in The Sims 4 su Mac un report Better Exceptions `invalid category ID`,
bloccando perfino l'uso della cassetta postale. Eliminando la coppia M32 dalla Mods,
il menu riprendeva a funzionare. Non esiste prova in gioco che la soluzione basata sulle
tre categorie con `_parent` fosse corretta.

Questa M35 **non è il menu finale**. È una compilazione diagnostica con una sola variabile:

1. Partire dalla coppia M34 la cui categoria unica è stata verificata in gioco.
2. Creare una nuova categoria con **XML e SimData**, ID a 31 bit, la stessa struttura
   della categoria M34, ma con `_parent=0` per testare la registrazione della categoria
   indipendentemente dal collegamento padre-figlio.
3. Spostare **soltanto** l'interazione `Consulta iscritti - Classe 1` sotto quella categoria
   `Classe 1 - M35 PROVA`, a sé stante.
4. Le altre operazioni, comandi, impostazioni, 4 studenti già iscritti e script Python
   rimangono identici a M34. Nessun commit automatico.
5. Se il gioco riconosce la categoria, il passo **successivo**, ancora da sviluppare,
   sarà testare il collegamento `_parent` verso MY HIGH SCHOOL senza introdurre
   subito le altre due classi.

### Build e test

Workflow: https://github.com/iliyanadg/MyHighSchool/actions/workflows/m35-smoke-python37.yml

La compilazione produce:
- `MHS_M35_SMOKE_CATEGORIA1_TEST.package`
- `MHS_M35_SMOKE_CATEGORIA1_TEST.ts4script`

Le prove statiche controllano che ci siano esattamente 2 coppie XML/SimData
(rispetto a una nella M34), che il clone usi `_parent=0`, che soltanto
la voce di consultazione Classe 1 faccia riferimento al nuovo ID, e che
tutte le altre interazioni restino byte-per-byte uguali.

**ATTENZIONE: test automatici superati NON equivalgono alla registrazione nella UI.**
È possibile che il problema precedente si ripresenti.

### Procedura sul Mac (soltanto partita di prova)

1. Chiudere completamente The Sims 4. Conservare fuori Mods i due file
   M34 (backup di recupero), e una copia della directory
   `MY_HIGH_SCHOOL_M25_TEST_DATA` con registro/impostazioni slot 11.
2. Spostare fuori Mods la coppia M34; inserire **solo la coppia M35** sperimentale.
   Lasciare XML Injector e altre dipendenze già esistenti, non modificare il save.
3. Riavviare, entrare nella solita partita TEST. Con il gioco in pausa, **cliccare
   sulla cassetta postale senza scegliere alcuna operazione**.
4. Se la cassetta non è cliccabile o Better Exceptions genera una nuova
   `UI Exception`, chiudere subito senza salvare, togliere M35 e ripristinare M34.
   Mandare uno screenshot del rapporto: questo isolerà il problema alla registrazione
   della nuova categoria, senza coinvolgere l'ereditarietà del menu.
5. Se la cassetta funziona, cercare `Classe 1 - M35 PROVA` (menu separato) e
   la consueta voce `MY HIGH SCHOOL (M35 SMOKE TEST)`.
   Controllare che le altre operazioni compaiano nel menu MY HIGH SCHOOL.
6. Provare **solo lettura** `Consulta iscritti - Classe 1` dal nuovo ramo,
   selezionando nessuno e senza nessun `*commit conferma`.
   Questa interazione M34/M35 necessita ancora che il tempo non sia in pausa
   per partire. Nessuna scrittura al JSON.
7. Per verificare la modalità salvata leggere `mhs34.settings`: lo slot 11
   deve essere ancora DISATTIVA / 2 classi. M35 è un test della categoria
   e non filtra ancora le voci in base a questo stato.

### Stato delle richieste ancora aperte

- L'UX annidata vera è definita e testata come **modello dati M35**, ma
  **non è ancora integrata** nel menu reale.
- La presenza/assenza di classi in base a 2/3 e Attiva/Disattiva, la gestione
  in pausa e le conferme con finestre native NON sono ancora funzionanti.
- Il sistema di frequenza del liceo EA non è implementato.

### Esito compilazione M35
- Workflow passato: https://github.com/iliyanadg/MyHighSchool/actions/runs/41157983178
- Archive: `MHS_M35_SOLO_TEST_REGISTRAZIONE_CLASSE1` (contiene la coppia .package + .ts4script)
- Tutti i test offline e bytecode Python 3.7 superati; **NON ANCORA VERIFICATA NEL GIOCO**.
