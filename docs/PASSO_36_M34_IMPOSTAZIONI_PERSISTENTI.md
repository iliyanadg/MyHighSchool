# Passo 36 — M34 impostazioni per singolo salvataggio, compilazione cumulativa

**Data:** 31 ottobre 2026. **Stato:** test automatici Python 3.7 e DBPF superati; da testare nel client reale su Mac.

## Perché questa versione
I test M33 hanno validato selettori, anteprime, ricerca e registro senza scritture. La giocatrice ha confermato un'altra volta che vuole:
- Attiva/disattiva MY HIGH SCHOOL senza perdere gli studenti
- Classe 3 opzionale: scelta 2 o 3 classi, 8 iscritti per classe
- Menu finale organizzato `MY HIGH SCHOOL → Classe 1/2/3 → azioni`
- Operazioni consentite anche con gioco in pausa e conferme direttamente nella UI

La M34 implementa **solo la gestione delle impostazioni del registro**; le ultime due richieste (menu annidato e operazioni in pausa) **NON sono ancora implementate** e devono essere affrontate evitando il crash invalid category ID della M32.

## Funzionalità già aggiunte
1. Un file separato per ogni slot nel solito folder registro M25 TEST: `Impostazioni_slot_<slot>.json`. Impostazioni non si mescolano tra salvataggi.
2. Per un salvataggio senza impostazioni precedenti, scelta iniziale **DISATTIVA**, **2 classi**: richiede un'azione esplicita di attivazione.
3. Aggiunte quattro opzioni nel menu piatto M33 della cassetta postale:
   - `Attiva MY HIGH SCHOOL (registro TEST)`
   - `Disattiva MY HIGH SCHOOL (registro TEST)`
   - `Impostazioni: usa 2 classi`
   - `Impostazioni: usa 3 classi`
4. Passaggio 3→2 classi **bloccato** se nel registro esistono iscritti alla Classe 3. Nessun Sim viene cancellato o trasferito automaticamente.
5. Modificare l'attivazione non cancella o modifica il registro. Le impostazioni restano dopo il riavvio, indipendenti per ogni slot.
6. La M34 porta un piccolo modulo di **protezione condivisa sulle scritture**: quando il sistema di gestione è disattivato, le operazioni che passano da `RosterStore.save` sono bloccate. In modalità due classi, una scrittura con assegnazioni in Classe 3 è bloccata. Le anteprime e gli elenchi rimangono disponibili. I vecchi pacchetti M25–M33 non contengono questo modulo e mantengono il comportamento storico.
7. Comandi diagnostici **sola lettura** `mhs34.settings` e `mhs34.report` per vedere stato configurazione e ultimi eventi. Le quattro opzioni funzionano solo quando la relativa interazione del Sim viene eseguita (nella M33 occorreva far partire il tempo).

## LIMITI SOSTANZIALI
- Disattivare il registro di prova **non cambia realmente** la frequenza scolastica EA, perché MY HIGH SCHOOL ancora non intercetta le situazioni/lezioni EA. Nessun affiancamento con la scuola EA è ancora implementato.
- Il menu rimane **piatto**, la struttura a tre sottomenu desiderata è in roadmap ma la vecchia soluzione ha causato una UI Exception.
- Le quattro nuove voci sono ancora `ImmediateSuperInteraction`; **non soddisfano la richiesta di agire durante la pausa**. L'UX finale richiede un'implementazione senza coda Sim, da progettare e verificare.
- Non esiste ancora la conferma finale delle modifiche del registro tramite una schermata di gioco: rimangono i comandi `commit conferma` per le scritture M33.
- I file JSON sono **esterni a `.save`** e non seguono rollback o Salva con nome; test solo su partita dedicata. Esci senza salvare non annulla le modifiche JSON già confermate.
- Le opzioni Classe 3 rimangono visibili anche quando la modalità è due classi, benché il guard impedisca scritture della Classe 3. Miglioramento UI futuro: nascondere o disabilitare i pulsanti.

## Build M34
- GitHub Actions: https://github.com/iliyanadg/MyHighSchool/actions/runs/41152216847
- Artifacts `MHS_M34_IMPOSTAZIONI_SOLO_PARTITA_TEST`
- Contiene `MHS_M34_IMPOSTAZIONI_REGISTRO_TEST.package` e `MHS_M34_IMPOSTAZIONI_REGISTRO_TEST.ts4script`.
- 27 risorse, 13 moduli compilati con CPython 3.7, una sola PieMenuCategory + SimData derivata dalla M33 testata.

## Un solo giro di test quando necessario
1. Copiare prima la cartella `MY_HIGH_SCHOOL_M25_TEST_DATA`. Chiudere il gioco e rimuovere la coppia M33 dalla Mods, conservandola fuori. Mettere solo coppia M34; v1.6 e XML Injector restano.
2. Aprire la partita test slot 11. Comando `mhs34.settings`: deve mostrare `DISATTIVA` / `2 classi` se non c'è ancora file impostazioni.
3. Cassetta postale, con il tempo in esecuzione: `Attiva MY HIGH SCHOOL` e `Impostazioni: usa 3 classi`. Dopo ogni comando aprire `mhs34.settings`: dovrebbe mostrare `ATTIVA` / `3 classi`.
4. Il registro deve ancora mostrare Classe 1 2/8 (Baby Ariel, Amarachi), Classe 2 2/8 (due Sofie), Classe 3 0/8; non effettuare commit.
5. Tornare a `2 classi`: successo perché Classe 3 è vuota.
6. Disattivare e vedere che `mhs34.settings` mostra DISATTIVA. Non eseguire operazioni di scrittura al registro in questo giro.
7. Non verificare il blocco Classe 3 occupata modificando il registro principale; è già coperto da test unitari, e per prova nel gioco servirà un file JSON test separato.

## Test automatici
- Default off/2, persistenza attiva/disattiva, isolamento slot, classe 3 facoltativa, rifiuto classe 3 non vuota, fallimento in sicurezza su JSON corrotto, guard su scritture disattivate, presenza tuning e traduzioni, conservazione singola categoria.

## 31 ottobre 2026, ore 02:09 — prova M34 Mac e menu desiderato chiarito
- Foto del gioco M34: `mhs34.settings` prima della modifica = Slot 11, Gestione iscrizioni DISATTIVA, Classi disponibili 2, Classe 3 iscritti 0.
- Dopo clic sulla voce `Attiva MY HIGH SCHOOL (registro TEST)`, `mhs34.settings` restituisce **ATTIVA**, Classi disponibili **2**, Classe 3 iscritti **0**, con `SAVED slot 11 | Attiva | 2 classi`. Il test dell'attivazione del registro per lo slot 11 è confermato.
- Seconda foto: la cassetta postale continua a mostrare il **menu piatto M34**, con tutte le opzioni di consultazione, trasferimento e attivazione distribuite su diverse pagine. L'utente ha richiamato espressamente la struttura finale: **clic sulla voce MY HIGH SCHOOL → Attiva/Disattiva → (se attivo) Classe 1 e Classe 2, eventualmente Classe 3 → sotto-ogni-classe tutte le operazioni della sua classe**.
- Quando DISATTIVA, le voci delle classi NON dovrebbero essere visibili/attive, lasciando visibile l'opzione ATTIVA. Quando ATTIVA, il menu deve mostrare DISATTIVA, Classe 1 e Classe 2, più Classe 3 **solo quando abilitata** tramite la scelta 2/3 classi. Per scelta 2/3, prevedere sezione Impostazioni persistente (per singolo salvataggio). Le opzioni devono poter funzionare in pausa e confermare nel gioco, senza necessità di console. **Questa UX non è implementata nella M34.**
- La precedente soluzione per sottocategorie M30/M32 ha causato `invalid category ID` e menu cassetta bloccato, quindi la prossima soluzione non va data per pronta senza prova live su Mac; mantenere un percorso di recupero con menu valido.
- Prossima verifica funzionale M34 da eseguire: scegliere `Impostazioni: usa 3 classi` nella cassetta con tempo attivo e leggere `mhs34.settings`. Attesi ATTIVA e 3 classi, registro studenti invariato.
