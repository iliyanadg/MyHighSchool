# Passo 24 — Sonda in-game PickedSim, con conferma invariata

**Stato: codice e test offline. Una build per il Mac viene compilata
esclusivamente se è disponibile CPython 3.7; non dichiarare il risultato
funzionante senza test nel gioco.**

Il M1 ha già superato prove reali della UI. Il problema rimasto è sapere
che cosa trasmette *effettivamente* la continuation di un picker quando
vengono scelti più Sim insieme.

## Nuovo esperimento M24
- Risorse del `MHS_M1_DIAGNOSTICA_HIGHBIT` conservate, salvo le due conferme.
- In `ConfirmClass1/2` cambiano solo `c` e `m` per puntare a
  `MHS24ProbeConfirmClass1/2` nel modulo originale `mhs24_diagnostic`.
- Una sottoclasse Vanilla `ImmediateSuperInteraction` legge
  `self.get_participants(ParticipantType.PickedSim)` quando viene
  eseguita la conferma e mantiene la notifica preesistente.
- Le letture sono conservate **solo nella memoria della sessione**,
  non su disco. `mhs24.report` stampa al massimo gli ultimi 16 eventi;
  `mhs24.clear` azzera i dati.
- Per gli eventuali problemi della lettura `PickedSim`, il report
  mostra il tipo d'errore e si prova a preservare la conferma standard.
- Gli ID vengono mostrati al giocatore per diagnostica: evitare di
  pubblicare schermate con ID di salvataggi personali.
- Nessuna chiamata al registro M2, nessuna modifica a Sims o .save.

## Test di accettazione in partita di prova
1. Confermare un solo adolescente in Classe 1; digitare
   `mhs24.report` nella console e rilevare 1 evento e 1 ID.
2. Usare `mhs24.clear`; selezionare 3 adolescenti contemporaneamente.
   Ripetere `mhs24.report` e contare **eventi** e **ID per evento**.
3. Ripetere con 8 e, separatamente, con Classe 2.
4. Non presumere che 3 conferme separate equivalgano a un batch unico:
   l'eventuale scrittura M2 è bloccata finché il risultato non sarà chiaro.

## Quali file servono
`MHS_M24_PICKEDSIM_SOLO_LETTURA.package` e
`MHS_M24_PICKEDSIM_SOLO_LETTURA.ts4script` vanno creati come coppia
dall'assemblatore in `tooling/build_m24_probe.py` usando **Python 3.7**.
Non usare `mhs24_diagnostic.py` da solo in Mods.

**Avvertenza:** questo script personalizzato non è ancora stato testato
nel gioco e potrebbe impedire le notifiche o addirittura bloccare l'avvio.
La v1.6 non deve essere modificata. Non installare contemporaneamente M1/M0
e M24. Fare la prova solo in nuova partita e non salvare.
