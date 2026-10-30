# SPECIFICA FUNZIONALE APPROVATA — MY HIGH SCHOOL — Classroom Control

**Aggiornamento:** 30 ottobre 2026. Questo documento descrive l'obiettivo, non funzioni già operative. Le decisioni recenti prevalgono sulle versioni precedenti.

## 1. Visione
Mod originale The Sims 4 per Mac, per controllare manualmente chi studia al liceo, in quale aula fisica e con quali docenti. Conservare, quando possibile, eventi EA di High School Years. Non serve compatibilità con Sonozaki High School Management, che la nuova mod deve sostituire.

## 2. Aule e routine
- **Tre aule** (Classe 1, Classe 2, Classe 3), con **massimo rigido di otto studenti per aula**, inclusi NPC e giocabili. Totale teorico: 24, da verificare nel gioco; non equivale alla capacità effettiva del lotto.
- Classe 3 facoltativa e disattivabile senza cancellare il registro.
- Una lavagna e un insegnante dedicati per aula; assegnazione tramite lavagna EA o CC compatibile, da riverificare se cambia il lotto.
- Uno studente deve essere fisicamente nell'aula prevista: presenza nel lotto, tratto nascosto EA e fase `Player_AttendClass` non bastano.
- Mantenere, se tecnicamente fattibile, orari EA e pranzo contemporaneo.
- Un liceo per salvataggio; sostituire il lotto non deve cancellare iscrizioni e personale.

## 3. Iscrizioni
- Registro inizialmente vuoto; nessun adolescente iscritto automaticamente.
- Scelta manuale fra tutti gli adolescenti del salvataggio, giocabili e NPC, di ogni nucleo/mondo, anche homeless.
- UI su PC o cassetta postale, su qualunque lotto, utilizzabile da adolescenti, giovani adulti, adulti e anziani.
- Selettore con ritratti, selezione multipla, ricerca/filtri per nome, mondo, nucleo e stato giocato; elenco dei non assegnati.
- Prima attivazione guidata; poi `Attiva MY HIGH SCHOOL` manuale. Disattivazione temporanea senza perdere dati.
- Cambi durante la giornata scolastica applicati dal giorno scolastico successivo. Gestire anche scambi fra classi già piene.
- `Riempi con NPC` solo su richiesta e per una quantità esatta: adolescenti esistenti o nuovi generati, con anteprima/accetta/escludi/rigenera.
- `Crea nuovo studente` via CAS e successiva assegnazione.
- Adolescente giocabile non iscritto: notifica per scegliere la classe, non iscrizione automatica.

## 4. Personale
- Un preside, un docente per aula attiva, numero personalizzabile di addetti mensa e custodi.
- Scelta da Sim esistenti, generazione NPC su richiesta oppure creazione CAS.
- Cambio docente dal giorno scolastico successivo.
- In caso di decesso del personale: sostituto casuale di emergenza con notifica e successiva selezione manuale.

## 5. Studenti: ciclo di vita
- Passaggio a giovane adulto o diploma anticipato: rimozione dal registro attivo e inserimento fra ex-studenti; posto libero, nessun rimpiazzo automatico.
- Decesso: rimozione e liberazione ruolo; nessun rimpiazzo automatico.
- Ritiro: cancellazione solo dall'elenco iscritti, Sim ancora esistente e reiscrivibile.
- Dati separati per ciascun salvataggio, senza trasferimenti automatici.

## 6. Ruoli ed eventi
- Rispettare i limiti EA per cheer, football, scacchi, informatica e altri ruoli; massimo un ruolo speciale per studente.
- Ruoli vacanti da assegnare manualmente a studenti iscritti.
- Mantenere ballo e diploma quando compatibili con EA. Invitati esterni ammessi al ballo senza diventare iscritti.

## 7. Compatibilità
- Mac, The Sims 4 con High School Years.
- Rilevare controller liceali incompatibili; notificare e bloccare l'attivazione, senza cancellare file.
- Valutare compatibilità con Sonozaki Elementary e Zerbu Go To School V5 senza presumere che funzioni.
- Non richiedere More Students 18, che causava bug nel gioco dell'utente.

## 8. Esclusioni e limiti
- **Escluso:** registro storico delle assenze e giustificazioni (malattia, marinare la scuola, ecc.).
- **Da definire:** flusso per scegliere quale adolescente giocabile seguire quando sono più di uno.
- **Da validare:** 3 lezioni contemporanee, 24 presenti, tre docenti, lavagne CC, eventi EA.
- **Da implementare:** interfaccia definitiva, wizard, gestione staff e attività avanzate.

## 9. Criteri di accettazione
1. Fino a otto adolescenti iscritti manualmente in ognuna delle tre classi, giocabili compresi; nessun iscritto casuale.
2. Durante la lezione, studenti fisicamente nell'aula assegnata.
3. Limite di capienza rispettato e limiti del motore comunicati, non nascosti.
4. Docenti distinti, pranzo insieme e orari EA conservati dove possibile.
5. Cambi durante scuola rinviati al giorno seguente; nessuna perdita dati.
6. Ogni funzionalità verificata con test offline **e prove nel gioco**: i test Python non provano la compatibilità con The Sims 4.
