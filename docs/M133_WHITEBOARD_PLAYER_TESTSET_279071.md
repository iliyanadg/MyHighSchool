# M133 — Identificato il test EA reale dietro il rifiuto di Classe 2

## Dati reali, non supposizioni
- M132 alle 09:40: giocabili classe 2 `568605179484009778` e `568605179488204115` rifiutati da `Whiteboard_Class_Start` per `SituationJobTest: Sim does not have required situation job.`
- Giocabile classe 1 `568605179485058376` ha test superato alle 09:40.
- Alle 10:05, readback M122/M132 rileva entrambi i set originali EA lezione 8/8 con zero mis-registrations. **Questo non implica passare il test di interazione.**
- Buff ruolo giocabile assente alle 09:40 per tutti e tre, presente alle 10:05 per tutti e tre; questo dato non spiega la divergenza Classe 1 / Classe 2.

## Origine tuning originale: file recuperato da allegato precedente
`ESTRAZIONI AGGIUNTIVE.zip / Interaction Tuning / 0x00000035!0x0000000000043926.0xe882d22f`
`super_HighSchool_Active_Whiteboard_Class_Start` (276774) contiene:

```xml
<L n="test_globals">
  ...
  <V t="test_set_reference">
    <T n="test_set_reference">279071<!--testSet_HighSchool_Active_PickWhiteboard_Student--></T>
  </V>
</L>
```

**M133 conclusion:** Il test globale EA dell'interazione passa dal `testSet_HighSchool_Active_PickWhiteboard_Student` ID **279071**. Il `SituationJobTest` potrebbe essere una sotto-condizione di questo insieme, ma non possiamo conoscere quale job GUID richiede finché non leggiamo l'XML di quel test set o la sua struttura runtime. NON assumere che richieda 277919 o 280777; non sovrascrivere o rimuovere un test di sicurezza in modo indiscriminato.

## Prossimo passo
- Recuperare tuning EA: `testSet_HighSchool_Active_PickWhiteboard_Student` (279071) tramite Sims 4 Studio -> Extract Tuning.
- Verificare quali `SituationJobTest` contiene; confrontare con guid attuali `get_current_job_for_sim` per i due giocabili Classe 2.
- Solo dopo decidere modifica mirata a Classe 2, con controllo su tutte le iscrizioni e senza toccare il calendario EA.
- Non garantire 16/16 seduti alle 10:00 finché il fatto non è osservato.
