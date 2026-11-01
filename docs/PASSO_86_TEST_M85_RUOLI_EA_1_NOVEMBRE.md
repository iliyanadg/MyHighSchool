# Passo 86 — Test reale M85 alle 10:09, 1 novembre 2026

La build M85 compilata su Mac produce correttamente la notifica
`MY HIGH SCHOOL - PRESENZE AUTOMATICHE`. Screenshot fornito dall'utente
alle 03:11 ora locale, ora di gioco **mercoledì 10:09**.

Trascrizione puntuale:
- M58 attiva: **SI**
- Conteggi CREAZIONE situazioni: Studenti **3**, Core **1**,
  Personale **1**, Mensa **1**, Errore **none**.
- M85 iscritti fisicamente sul lotto: **3/16**
- M85 iscritti in situazioni scolastiche EA: **3/16**
- Classe 1 iscritti in situazioni EA **1**
- Classe 2 iscritti in situazioni EA **2**
- La notifica precisa: **NON significa seduti**.

**Nota fondamentale**: C1=1 + C2=2 = 3, quindi i dati sono
internamente coerenti. Non confondere la cifra di C1 con 2.
Il menu sta facendo conteggi veri della presenza per Sim ID, non
la selezione o l'assegnazione di un banco.

Il pannello del gioco mostra attività di lezione alle 10:09;
la screenshot è all'esterno del liceo, perciò non prova che tutti
gli NPC casuali siano seduti in quel preciso momento. La precedente
prova M58 aveva confermato il regolare avvio delle lezioni.

## Risultato pratico
La priorità è il collegamento **pre-spawn** degli esatti Sim del registro
ai lavori/guest list delle situazioni EA, preservando la situazione
scolastica esistente, non più fare altre diagnostichette generiche.
Da verificare anche il limite di posti e i job nelle due fasi di lezione.
La modifica deve coinvolgere esattamente gli iscritti e mai introdurre
nuove situazioni additive per ogni Sim.

## Vincolo
Mantieni i file M85 attuali come baseline diagnostica.
Non riattivare i constraints M57/M60 e non installare More Students/
Sonozaki High School in parallelo.
Non dichiarare le presenze 16/16 finché il test Mac non le conferma.
