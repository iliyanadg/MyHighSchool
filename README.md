# MY HIGH SCHOOL — Classroom Control

Mod per **The Sims 4: Vita da Liceali**. La versione unificata usa due
classi da otto studenti (16 in totale), registri e personale persistenti,
un solo controller per le situazioni EA e lavagne separate.

## Stato reale della beta

**Collaudo in gioco del 5 novembre 2026:** osservati 8 studenti in ogni
aula, Geoffrey Landgraab e Akira Kibo come docenti, Kai Aether preside
e Bjorn Bjergsen e Gianluca Ferraro come bidelli contemporanei nei veri
job EA. Non e una certificazione di funzionamento universale.

**Problema ancora aperto:** l'addetto mensa non e arrivato e molti
studenti non hanno pranzato. La correzione successiva invita un
**unico addetto principale fisso** quando il registro contiene 2–3
addetti e segnala gli altri come in sospeso. Il servizio e il pranzo
**devono ancora essere verificati in gioco**.

**Correzioni di ciclo giornaliero:** un cambio di giorno a scuola non
deve disinstallare il controller gia attivo. Il monitor dell'arrivo
viene riarmato dopo la fine della giornata. Durante l'intervallo
12:00–13:24 i test modificati delle lavagne lasciano quelli EA
originali, senza forzare l'uscita degli studenti o ordini di cibo.
Sono salvaguardie; non dimostrano ancora che gli studenti mangino.

**Estensione personale in prova:** se il gioco assegna soltanto uno dei due\nbidelli, la mod tenta una seconda situazione EA riservata esclusivamente\nal bidello mancante. Per ogni addetto alla mensa oltre Agnes richiede un\nbancone scolastico aggiuntivo riconosciuto nel lotto; non convoca altri\naddetti quando il bancone non e verificabile. I nuovi incarichi restano\n**in beta** finche il report non conferma i job EA e il lavoro effettivo.\n\nLa mod rimane una **beta da collaudare in gioco**, non una release\ncertificata stabile.

## Scaricare una build corretta

Per questa revisione **non usare** il vecchio
`downloads/MHS_CLASSROOM_CONTROL.zip` presente nel repository:
e un archivio precedente alle correzioni per il personale.

Usa l'**Artifact** `MHS_CLASSROOM_CONTROL_OFFLINE_VERIFIED` del
workflow GitHub Actions **Classroom Control unified package**
associato al commit/PR da collaudare, soltanto se i test passano.

L'Artifact genera una coppia:
- `MHS_CLASSROOM_CONTROL.package`
- `MHS_CLASSROOM_CONTROL.ts4script`

Installa soltanto questa coppia, dopo aver fatto backup di
`saves/`, `MY_HIGH_SCHOOL_M25_TEST_DATA/` e della build
precedentemente funzionante. Non usare vecchi script MHS in parallelo.

## Documentazione

- [Collaudo integrato personale e mensa](docs/COLLAUDO_PERSONALE_BETA.md)
- [Audit e limiti](docs/AUDIT_CLASSROOM_CONTROL.md)
- [Installazione su Mac](docs/INSTALLAZIONE_PULITA_MAC.md)
- [Contratti EA](docs/EA_CONTRATTI_CLASSROOM_CONTROL.md)

## Build locale

La compilazione degli script installabili richiede **CPython 3.7**:

```sh
python3.7 -m unittest tests.test_classroom_bootstrap_day_rollover tests.test_scoped_classroom -v
python3.7 -m tooling.build_classroom_control /tmp/myhighschool-build
```

Il solo successo del CI non dimostra presenza dei Sim, compimento
delle lezioni, servizio della mensa, compatibilita Windows o
compatibilita con mod di terze parti.
