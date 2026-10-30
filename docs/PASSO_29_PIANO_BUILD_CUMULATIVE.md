# Passo 29 — Piano a pacchetti, niente piu micro-installazioni

**Data:** 31 ottobre 2026. Piano di lavoro, non dichiarazione di funzionalita funzionanti nel gioco.

## Perche
L'utente ha confermato che desidera piu correzioni e funzionalita per ogni versione di prova. Evitare una build per ogni bug o pulsante, salvo problema che blocca l'avvio del gioco o rischia il salvataggio.

## Stato osservato
- M25: iscrizione/trasferimento manuale per Classe 1 e 2 con picker e comando separato di commit, in registro JSON esterno.
- M27: voci Rimuovi studenti per Classe 1 e Classe 2 compaiono nella cassetta postale.
- Prova in-game M27 del 31/10: il picker rimozione non si apre. Diagnostica: `AttributeError: 'tuple' object has no attribute 'icon_resource'`.
- Fix del `icon_override=(None, info)` gia implementato su GitHub in `mhs27_remove_ui.py`; la correzione NON e ancora verificata in-game.
- Le prove statiche di build non certificano il funzionamento dentro The Sims 4.

## Prossima build cumulativa: M28 — gestione registro studenti (solo partita test)

Consegna in una sola coppia `.package` + `.ts4script`, **sostituendo** la coppia M27 (mai installarle insieme):

1. Stabilizzare il picker fotografico e intercettare i fallimenti senza perdita dati.
2. Completare **3 classi** (la terza facoltativa, capienza rigida 8 ciascuna). Conservare compatibilita dei dati esistenti per Classe 1 e Classe 2.
3. Menu coerente per Classe 1/2/3, con iscrizione selettiva, rimozione iscritti (non eliminazione Sim), trasferimento e riepilogo studenti con nomi e capienza.
4. Sempre e solo adolescenti selezionati volontariamente, sia giocabili sia NPC; no generazione di NPC o inserimenti automatici.
5. Gestire selezione multipla, duplicati, classe piena, passaggi fra classi, cancellazione e conferma esplicita, con esito facilmente leggibile. Lo scambio simultaneo fra classi piene va gestito come transazione, non come due spostamenti unilaterali.
6. Diagnostica direttamente accessibile e controlli preflight di slot, classe, eligibility e stato del registro.
7. Non creare file di dati senza conferma esplicita e preservare rollback e caricamento della M25; usare esclusivamente partita di prova.

## Criteri di prova e blocchi
- Test automatici Python/DBPF, XML, SIMDATA, localizzazione, compatibilita Python 3.7; CI verde.
- Verifica sul Mac in-game del menu, di foto/nomi e dei 3 elenchi; se il picker non compare, raccogliere errori senza test di scrittura.
- Verifica salvataggio in JSON, riavvio e nuovo caricamento, trasferimento e rimozione.
- Una singola installazione per il pacchetto M28, con checklist breve.
- **Non considerare pronta per la partita principale**: registro JSON esterno non sincronizzato con Save/Load e ancora nessuna prova che i ragazzi vadano fisicamente a scuola / nelle classi.

## Dopo M28
- M29: aula fisica, lavagne EA/CC, insegnanti e scheduling, con veri test della frequenza.
- M30: staff completo, evento ballo e diploma, integrazioni compatibilita e ciclo di vita.

I numeri versione sono provvisori. Implementazioni complesse possono essere suddivise nel codice, ma non richiedono una nuova installazione a ogni singolo commit.
