# MY HIGH SCHOOL — Classroom Control

Mod per The Sims 4 con Vita da Liceali: due classi da otto iscritti,
registro e personale persistenti, integrazione con le situazioni originali EA.

Questo branch unifica M54 e M148 e corregge il test della lavagna degli NPC
usando le API EA ricevute. Il primo collaudo ha osservato 8/8 in entrambe le
aule, con ritardi ancora da diagnosticare. **La mod non è dichiarata stabile**.
La revisione corrente aggiunge letture per la seconda giornata; il personale
salvato nel menu non è ancora collegato al reclutamento dei ruoli EA.

- [Audit, correzioni ed evidenze ancora necessarie](docs/AUDIT_CLASSROOM_CONTROL.md)
- [Installazione e inventario sicuro delle Mods su Mac](docs/INSTALLAZIONE_PULITA_MAC.md)
- [Primo collaudo: una sola versione, due giornate EA](docs/PRIMO_COLLAUDO_CLASSROOM_CONTROL.md)
- [Analisi dei quattro contratti EA originali](docs/EA_CONTRATTI_CLASSROOM_CONTROL.md)
- [Esito del primo collaudo e diagnostica della seconda giornata](docs/SECONDA_GIORNATA_DIAGNOSTICA.md)

Compilazione dai sorgenti con CPython 3.7:

```sh
python3.7 -m tooling.build_classroom_control /tmp/myhighschool-build
python3 -m unittest discover -s tests -v
```

La build produce una sola coppia `MHS_CLASSROOM_CONTROL.package` e
`MHS_CLASSROOM_CONTROL.ts4script`, con manifest e hash. I controlli offline
non provano puntualità, completamento delle lezioni o compatibilità con altre mod.

Non cancellare `saves/` o `MY_HIGH_SCHOOL_M25_TEST_DATA/`. Le versioni precedenti
restano nella cronologia e nei rispettivi branch.
