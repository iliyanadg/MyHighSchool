# Passo 56 — M49: X e spunta ✓ con iscrizione verificata nel gioco (31 ottobre 2026, ore 15:30)

## Riscontro dell'utente
Dopo aver aperto il selettore nativo M49 «Iscrivi studenti - Classe 1» mentre The Sims 4 era in pausa, l'utente ha eseguito i due test previsti.

1. **X per annullare**: l'utente conferma «test 1 è così corretto»; il registro è rimasto invariato. Nessun comando console per l'iscrizione.
2. **Spunta ✓ per iscrivere**: una notifica originale della mod dice «Classe 1: 1 iscrizioni aggiornate. Totale 3/8. Il liceo EA non è ancora controllato.»
3. Il selettore «Rimuovi studenti - Classe 1» mostra ora **Amarachi Darong, Baby Ariel e Hugo Villareal**. La terza iscrizione effettiva è Hugo Villareal, benché il test proposto inizialmente suggerisse Rosario Lanzafame: non assumere che sia stato scelto Rosario.
4. Lo screenshot del selettore e della notifica mostra il gioco **IN PAUSA**, quindi il callback e l'aggiornamento del registro risultano operativi anche in pausa per questo caso.
5. Non è mostrata una nuova eccezione attribuibile a MY HIGH SCHOOL.

**Confermata in game la prima iscrizione completa tramite la spunta del picker, senza conferma secondaria né comando cheat.** Sono inoltre già state verificate la navigazione e visibilità dinamica della M45.

## Cosa NON prova ancora

- **Persistenza dopo il riavvio completo**: la scrittura JSON è supportata dalla notifica/consultazione, ma serve prova di chiusura e riapertura dello stesso salvataggio.
- Massimo otto studenti in una classe con selezione multipla e comportamento dell'interfaccia se si tenta il nono: il backend rifiuta il superamento degli otto, ma il limite UI è ancora basato su strategia Unlimited.
- Rimozione e trasferimento completi da GUI, conferma, idempotenza e mantenimento degli ID.
- Frequenza effettiva degli studenti alle lezioni, classi e personale del liceo EA: **non ancora implementati**. L'iscrizione corrente è nel registro JSON esterno di prova.

## Prossimo test senza nuova build
Con M49 e salvataggio TEST, dopo backup del registro esterno, **chiudere completamente il gioco e riaprire lo stesso salvataggio**. In MY HIGH SCHOOL -> Classe 1 -> Consulta iscritti devono restare Amarachi Darong, Baby Ariel e Hugo Villareal, e «Iscrivi studenti» deve indicare 3/8. Non fare altri cambiamenti prima di questa verifica. Non richiedere nuove prove del menu né ripetere test già superati.
