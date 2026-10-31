# Passo 59 — M52: rimozione multipla, Classe 3 occupata e roadmap personale

## Conferme in-game fino alla M51 (31 ottobre 2026)

La creatrice conferma:
- Persistenza registro dopo riavvio: le scelte delle Classi 1 e 2 rimangono le stesse;
- Classe 1: otto studenti, quattro aggiunti da UI;
- Classe 2: otto studenti prima di test trasferimento;
- Classe 3: Amarachi e Hugo prima del test, poi Yuki e Sofia trasferite dalla Classe 2;
- **Trasferimenti multipli della M51 riusciti**, gli studenti selezionati vengono effettivamente spostati nel registro;
- **Rimuovi studenti non funziona**: la GUI originale permette solo un Sim alla volta e premendo spunta non modifica il registro né con gioco in pausa né con tempo in movimento;
- **Disabilita Classe 3 appare non funzionare**, poiché la Classe 3 è ancora popolata; la progettazione originale impedisce (correttamente) di disattivare una classe che contiene iscritti, ma non mostrava alcun messaggio.

## Diagnosi del codice

`src/m27_remove_ui/mhs27_remove_ui.py` (M27) apriva il picker e scriveva la selezione solo in `_PENDING` in memoria. Il file JSON veniva scritto esclusivamente con comando cheat `mhs27.removecommit conferma`. Il vecchio picker non specificava una strategia multi-select.

`SettingsStore.set_class_count(slot,2,roster)` blocca volontariamente la disattivazione se ci sono studenti in Classe 3, con messaggio `Classe 3 contiene N studenti: trasferiscili o ritirali prima di passare a 2 classi`; `mhs34_settings_ui._apply` catturava l'errore ma NON lo mostrava al giocatore.

## Modifiche M52

- Rimozione con selezione multipla nativa da 1 a 8 studenti iscritti della stessa classe, usando EA `UiDialogObjectPicker._MaxSelectableUnlimited` subclass con `get_max_selectable` che restituisce il numero di candidati della classe.
- Spunta ✓: convalida identità degli iscritti, salvataggio corrente, attivazione/classi, fingerprint JSON; chiama `RemovalService.preview` + `.commit` nello stesso evento. Una sola scrittura atomica per tutta la selezione. Nessun Sim cancellato dal gioco.
- X: chiude senza modifiche. Doppio callback bloccato.
- Notifica in gioco quando conferma rimozione e quando il registro blocca un tentativo.
- Notifica quando si tenta `Disabilita Classe 3` con iscritti presenti, spiegando la necessità di trasferirli o rimuoverli. La classe rimane visibile fino a quando è vuota.
- Il `.package` di M52 resta byte per byte identico a M51 con tutte le cinque categorie/SimData Lot51; la UI M45 e le iscrizioni/trasferimenti M51 non sono rigenerate.
- `mhs39_visibility_ui.py` importa le azioni di rimozione dal modulo esistente `mhs27_remove_ui`, evitando dipendenze a script sperimentali non inclusi nel bundle.
- Test dell'interfaccia legacy M27 aggiornati al comportamento M52, più test M52 di notifica/rimozione senza secondo dialogo, suite M50/M51.

## Requisito futuro e personale

Richiede **Vita da Liceali (EP12)** per la mod destinata alla pubblicazione; il controllo automatico della presenza del pack è ancora da implementare.
Non dimenticare il personale richiesto dalla creatrice:
- **Preside** scelto manualmente, con sostituzione possibile;
- **Un insegnante per aula attiva**, da scegliere manualmente o creare, e un'aula dedicata;
- **Mensa e bidelli**: gestione numero/dipendenti;
- Creazione/CAS, ruolo NPC e sostituzione automatica per morte o perdita del ruolo;
- Collegamento al campus EA e presenze vere degli studenti con posti massimo 8/classe, 3 classi.
Queste funzioni NON sono ancora implementate. Non promettere che siano già funzionanti.

## Verifica su Mac M52 (non ancora effettuata)

Salvare backup della cartella JSON esterna, conservare M51 fuori Mods, installare una sola coppia M52. Eseguire:
1. Classe 1 -> Rimuovi studenti -> selezionare due Sim del TEST -> ✓; riaprire Consulta Classe 1 e verificare che entrambi siano assenti. La X deve lasciare invariati gli iscritti.
2. Tenta Disabilita Classe 3 con iscritti presenti: deve comparire notifica con N studenti, la Classe 3 deve rimanere visibile.
3. Solo se Classe 3 diventa vuota attraverso trasferimento/rimozione, disabilitazione deve funzionare e il sottomenu scomparire.
4. Verificare che i trasferimenti M51 e iscrizioni M50 siano preservati senza ricominciare il test del menu principale.
