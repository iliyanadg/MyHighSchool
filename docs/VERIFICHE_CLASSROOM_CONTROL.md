# Verifiche della revisione unificata

4 novembre 2026, ambiente cloud Linux. Nessuna prova The Sims 4 eseguita qui.

| Controllo | Esito osservato |
| --- | --- |
| Baseline M148 prima delle modifiche | 1.297 test passati con Python 3.12 |
| Suite complessiva dopo integrazione | 1.341 casi: 1.337 passati, 4 saltati (archivio richiede Python 3.7) |
| Sottogruppo build/sessioni/inventario/regressioni con CPython 3.7.17 | 65 casi: 64 passati, 1 saltato (rifiuto compilatore errato, non applicabile a 3.7) |
| Ultimi controlli inventario sorgenti/XML e lifecycle | 10 casi: 9 passati, 1 saltato per la stessa ragione |
| Verifica finale del compilatore, dopo correzione formato ZIP | 12 casi: 11 passati, 1 saltato; cinque controlli dell'archivio realmente eseguiti con Python 3.7 |
| Caricamento bytecode reale | Import di sessioni, policy e bootstrap dal `.ts4script` senza sorgenti `.py`; formato timestamp normalizzato accettato da zipimport 3.7 |
| Reset giornaliero e politiche di richiesta, verifica mirata | 27 test passati con Python 3.7 |
| Regressione impostazioni M52 dopo correzione avviso non necessario | 4 test passati |
| Build installabile corrente | 47 moduli unici, 75 risorse DBPF, 11 coppie categoria/SimData, CRC e magic `420d0d0a` validi |
| Provenienza della build | Tutti i 47 hash dei sorgenti corrispondono al checkout; entrambi gli hash artefatti corrispondono al manifest |
| Riproducibilità | Due compilazioni identiche nel test Python 3.7; timestamp ZIP e percorso bytecode fissati |
| Inventario su installazione sintetica della coppia reale | Due artefatti riconosciuti, nessuna collisione, dato persistente sentinella invariato |
| GitHub Actions | Workflow aggiunto; esito remoto non osservato, API `api.github.com` bloccata dalla rete corrente |
| Mac, Windows, 8/8 puntuali, lezioni concluse, compatibilità terze parti | Non verificati per questa revisione |

Comandi principali, dalla radice del repository:

```sh
python3 -m unittest discover -s tests -v
python3.7 -m unittest tests.test_school_session tests.test_classroom_attendance_policy tests.test_classroom_runtime tests.test_mod_inventory tests.test_classroom_control_build -v
python3.7 -m tooling.build_classroom_control /tmp/myhighschool-build
```

Nel cloud, il compilatore 3.7 verificato si usa tramite
`bash /workspace/.myhighschool-setup/python37.sh` al posto di `python3.7`.
Lo script di installazione e le istruzioni iniziali sono salvati nella bozza
dell'ambiente. Questo non equivale alla pubblicazione dell'ambiente.

I file ricevuti dal giocatore, i dati reali e i sorgenti EA originali non sono
stati aggiunti a Git o alla distribuzione. Le conclusioni sul rapporto M148
sono nell'audit; la build non certifica che il difetto della lavagna sia risolto.

La prima variante del nuovo compilatore usava header PEP 552 con hash:
il caricatore ZIP effettivo di CPython 3.7 li rifiuta. Tale variante non è stata
pubblicata. Il test finale di import ne ha determinato la sostituzione con
header timestamp normalizzati, confrontando anche il codice compilato con il
sorgente. Gli SHA-256 dei sorgenti rimangono nel manifest indipendentemente
dal formato dell'header.
