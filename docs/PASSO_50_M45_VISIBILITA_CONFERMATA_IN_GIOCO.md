# Passo 50 — M45: gerarchia e visibilità confermate in gioco Mac (31 ottobre 2026, 14:14–14:15)

## Esito degli screenshot

Cinque screenshot forniti dall'utente confermano il funzionamento in gioco dei menu M45:
- MY HIGH SCHOOL disattivata: la categoria contiene soltanto «Attiva MY HIGH SCHOOL»; Classe 1, 2, 3 e Impostazioni sono nascoste.
- MY HIGH SCHOOL attiva, due classi: sono visibili Classe 1, Classe 2 e Impostazioni; Classe 3 non compare.
- Impostazioni con Classe 3 disabilitata mostra «Abilita Classe 3».
- Classe 3 riabilitata: torna visibile il suo sottomenu, con Prepara iscrizione, Consulta iscritti, Rimuovi studenti, Trasferisci in Classe 1/2.
- Classe 1 con due classi attive: il menu mostra Trasferisci in Classe 2, non Trasferisci in Classe 3.
- Non appaiono avvisi di nuove LastException negli screenshot; il pop-up verde di Better Exceptions è soltanto il messaggio di benvenuto e non prova assenza totale di errori nel log.

## Diagnosi confermata

La M44 aveva tutti i menu annidati ma lasciava tre SimPickerInteraction di preparazione iscrizione senza il filtro di visibilità usato per le altre interazioni; questi mantenevano visibile la categoria in modalità disattivata. La M45 ha corretto i tre picker mantenendo le SimData provenienti da Lot51 e il menu principale funzionante.

**Baseline UI verificata su Mac: M45.** Evitare di rigenerare o modificare le cinque categorie XML/SimData o di ripetere test del menu senza motivi precisi. L'utente conserva le altre mod installate.

## Da sviluppare e validare in fasi successive

1. Iscrizioni e conferme realmente completabili dall'interfaccia di gioco, senza console; notifica successo/errore e massimo otto studenti per classe.
2. Esecuzione di modifiche mentre il tempo di gioco è in pausa. Finora è stato verificato solo che la finestra di consultazione si apre in pausa.
3. Persistenza JSON per salvataggio, con prova di riavvio e backup perché le modifiche esterne non seguono il Salva/Non salvare di EA.
4. Frequenza effettiva al liceo, classi fisiche, personale, eventi High School Years: non ancora implementati né verificati.

Non affermare che la mod sia già una gestione scolastica completa; **si è verificato il menu e la sua visibilità**.