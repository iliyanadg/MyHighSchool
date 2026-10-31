# Passo 62 — M54: non mostrare animali nel selettore del personale

## Test Mac M53 positivo, con un problema segnalato dall'utente (31/10/2026)

L'utente ha confermato che **tutto il nuovo menu «Personale scolastico» M53 funziona** sul suo Mac. Ha però notato che quando apre il picker per scegliere preside/professori/mensa/bidelli **compaiono anche cani** (e quindi il filtro permetteva potenzialmente anche gatti e altri animali).

### Causa confermata nella M53

Il codice originale `src/m53_staff/mhs53_staff_ui.py` controllava solo:
`sim.age in (Age.YOUNGADULT, Age.ADULT, Age.ELDER)`.
Nel gioco gli animali possiedono valori di età simili a quelli dei Sim umani e possono risultare `Age.ADULT`. Il SimInfoManager contiene anche i Sim animali (cani/gatti/cavalli etc.).

### Correzione M54

Nel selettore `_adult_infos()` ora è obbligatorio **sia `sim.species == Species.HUMAN` sia l'età adulta ammessa**. Il campo `species` mancante non viene interpretato come umano: nessuna assegnazione finché la specie non è verificata.

La funzione `_still_adult(sim_id)` (usata dal validatore prima della scrittura) applica lo stesso filtro. La callback di conferma del picker rifiuta la selezione se il Sim è divenuto animale/non idoneo anche dopo aver aperto la finestra. Questo protegge **tutti** i ruoli: preside, prof. delle classi 1/2/3, mensa massimo 3, bidelli massimo 2. Non cambia nessuna capienza.

**Caso di recupero:** se per errore la M53 avesse già assegnato un cane a un ruolo, l'azione «Rimuovi» può ancora mostrarlo per consentire di liberare il posto; il cane non riappare nel menu «Assegna», e la rimozione non elimina l'animale dal gioco.

Il `.package` M54 è **byte-identico alla M53**: le 10 categorie e SimData Lot51, le 17 azioni aggiunte, tutte le vecchie 35 risorse M52 e le traduzioni restano identiche. Si ricompilano solo i 19 moduli Python della `.ts4script`.

### Validazioni e limiti

`tests/test_m54_human_staff_species.py` include cani, gatti, cavalli, volpi, specie assente, adolescenti umani e umani giovani adulti/adulti/anziani; controlla il filtro al momento dell'apertura e della spunta e controlla compatibilità binaria della M53.

La M54 corregge **solo il registro e l'interfaccia del personale**, non fa ancora comparire questi Sim come personale attivo del liceo EA. Rimane obbligatoria l'espansione Vita da Liceali (EP12) per il prodotto finale, con controllo pack/ruoli EA da implementare.

### Test Mac

Salvare una copia della M53 funzionante e del registro JSON personale, rimuovere SOLO la coppia M53 dalla cartella Mods e inserire la coppia M54. Aprire `MY HIGH SCHOOL -> Personale scolastico -> Preside -> Scegli / sostituisci`, controllare che non siano visibili cani/gatti, ma che rimangano gli umani giovani adulti/adulti/anziani. Verificare se necessario il menu dei professori e mensa. Se un animale risultasse precedentemente assegnato, usare Rimuovi, non Assegna.
