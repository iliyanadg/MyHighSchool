# Passo 25 — Iscrizione M25 con commit esplicito, test isolato

**Questa build è ancora non verificata nel gioco e va provata
ESCLUSIVAMENTE in una nuova partita di test salvata.**

## Risultati del precedente M24 (verificati nel gioco)
Lo screenshot `mhs24.report` prova che `PickedSim` della continuation
di Classe 2 ha passato **8 ID distinti in un unico evento**. Classe 1
ha passato un solo ID in altri eventi. M24 non mostrava la notifica,
perché la sottoclasse restituiva la coroutine/generator super senza
consumarlo: in M25 `yield from` esegue il generator originale se esiste.

## Differenza rispetto a M24
- Il selettore resta quello M1 (gia verificato).
- Il tasto ✓ invoca `MHS25StageConfirmClass1/2`, che legge solo
  `PickedSim` e PREPARA il gruppo (da 1 a 8 studenti). **Non scrive**.
- `mhs25.preview` verifica slot, adolescenti, capienza e spostamenti.
- Solo `mhs25.commit conferma` salva nel registro JSON **M25 SEPARATO**,
  con scrittura atomica, slot verificato e limiti 8/classe.
- `mhs25.roster` legge i due elenchi; `mhs25.discard` annulla,
  `mhs25.slot` verifica lo slot senza scrivere.
- Nessun NPC generato, niente iscritti automatici, nessun evento EA,
  nessuna lezione, nessuna modifica ai Sim o al file .save.
- Tutte le stringhe del picker/notifica sono state corrette per
  evitare che dicano "nessuna iscrizione salvata" dopo un eventuale
  commit. Il toast conferma **solo la selezione pronta**, non il
  risultato del salvataggio.

## Perche richiediamo un commit separato?
M25 è un test potenzialmente scrivente. Vogliamo vedere il conteggio
dei Sim e l'ID del salvataggio **prima** di creare un JSON.
Una volta verificati i successi e i blocchi, potremo integrare la
conferma diretta dal selettore.

## Limite critico dei registri esterni
I dati sono salvati in un JSON nella cartella
`MY_HIGH_SCHOOL_M25_TEST_DATA`, separata da M2 e dalla v1.6.
Non sono parte del file .save e non vengono automaticamente
ripristinati se il giocatore torna a una versione precedente
della stessa partita, duplica il salvataggio o usa 'Salva con nome'.
**Non adatto alla partita principale** finché non risolviamo
l'integrazione al ciclo Save/Load.

## Piano di prova Mac, un passo alla volta
1. Chiudere il gioco. Lasciare la v1.6 invariata e M0/M1/M24 fuori
   dalla Mods. Installare soltanto la coppia M25 .package e .ts4script.
2. Avviare la partita di prova e SALVARLA prima della scelta di studenti.
   Non usare il salvataggio principale.
3. Console `mhs25.slot`: richiede un ID di slot positivo.
4. Cassetta postale → M25 TEST → Classe 1 → seleziona 2 adolescenti → ✓.
5. Console `mhs25.preview`: controllo soltanto, nessuna scrittura.
6. Console `mhs25.commit conferma`: primo JSON del test.
7. Console `mhs25.roster`: verifica 2 iscritti in Classe 1.
8. Chiudere e ricaricare prova, usare `mhs25.roster` e verificare
   che risultino ancora presenti. NON caricare partita principale.

Se il gioco non parte, se salta la notifica o il preflight fallisce:
NON salvare/committare; chiudere e togliere SOLO M25, lasciando v1.6.
