# Verifica preliminare dei package DBPF

Strumento: `tooling/package_audit.py`. Si tratta di una **lettura statica** del package: non avvia The Sims 4 e non verifica la validità dei tuning del gioco.

## Cosa controlla
- Intestazione DBPF, dimensioni e posizione dell'indice.
- Duplicati di identificativi Tipo/Gruppo/Instance.
- Intervalli dati delle risorse non validi o tronchi.
- Presenza di una risorsa SimData con lo stesso instance ID di ciascuna `PieMenuCategory`: **solo avviso**, perché la mancanza non è stata dimostrata essere l'unica causa del mancato avvio.

Lettura manuale, se necessario: `python tooling/package_audit.py /percorso/al/file.package`. Non altera il file.

## Confronto effettuato con i file originali forniti
| File | Risorse | Categorie menu | SimData abbinata | Risultato del controllo |
|---|---:|---:|---:|---|
| M0 (non avvia il gioco) | 8 | 1 | 0 | Avviso: 1 categoria priva di SimData |
| Sonozaki 2.2.1 (riferimento) | 165 | 14 | 14 | Nessun avviso per quel problema |

Le risorse proprietarie EA e i package di terzi **non** vengono caricati nel repository. Questi dati sono risultati del confronto offline.

I 6 test su package sintetici controllano il funzionamento dell'auditor. Non dimostrano che un nuovo package sia installabile.

**Prossima attività:** completare l'importazione dei moduli v1.6 e verificare il tuning XML/SimData prima di compilare una nuova build. Nessuna nuova build va definita stabile senza una prova separata di avvio nel gioco.
