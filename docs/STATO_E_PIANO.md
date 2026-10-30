# MY HIGH SCHOOL — Stato e piano di lavoro

## Obiettivo
Mod originale per The Sims 4 su Mac, versione di gioco osservata **1.129.39.1230**, con gestione manuale e persistente degli studenti al liceo.

## Requisiti confermati
- Due classi obbligatorie e una terza facoltativa, fino a **8 adolescenti per aula** (24 iscritti teorici: la presenza simultanea va testata).
- Scelta manuale degli adolescenti, inclusi Sim giocabili e NPC; niente inserimenti casuali non richiesti.
- Registro indipendente per salvataggio; la disattivazione della terza aula non cancella gli iscritti.
- Accesso da cassetta postale e PC, con menu originale a cerchio e selettore dei Sim nativo.
- In seguito: assegnazione stabile di aula/insegnante, personale, lezioni, pausa pranzo, eventi EA e gestione delle uscite dalla scuola.
- Nessun registro dettagliato delle assenze.

## Base funzionante
- Sul Mac dell'utente, **MY_HIGH_SCHOOL_v1_6_Scelta_Aula_Giocabili.ts4script** consente al gioco di avviarsi.
- NON sovrascrivere la v1.6, i registri, i salvataggi o le mod già installate.

## Esperimenti non funzionanti
- Due primi prototipi d'interfaccia (uno con hook Python, uno con XML Injector) impedivano l'avvio del gioco.
- Il successivo **M0_MENU_NATIVO_SOLO_TEST.package** impediva anch'esso l'avvio; il gioco torna a funzionare rimuovendo solo quel package.
- La causa precisa del blocco all'avvio **non è ancora dimostrata**. Le verifiche precedenti sulla leggibilità delle risorse non erano sufficienti.

## Riferimenti tecnici già recuperati
- File EA dalla versione installata: `simulation.zip`, `core.zip` e cinque moduli .pyc dell'interfaccia.
- Sonozaki High School Management 2.2.1: package principale, ts4script e addon Force To Attend Class, analizzati come riferimento.
- Sonozaki impiega selettori nativi tramite tuning XML; confrontarne anche le risorse associate, non soltanto la sintassi XML.
- Prima di scegliere un framework, verificare le dipendenze e la compatibilità esatta con la versione di gioco.

## Regole di sviluppo
1. Lavorare sui **sorgenti**, non installare package come metodo di debugging.
2. Inserire test automatici per DBPF, risorse collegate, identificativi, XML e dipendenze. Distinguere test statici da verifiche in gioco.
3. Correggere e revisionare il primo menu su un ramo separato; non pubblicare build come funzionanti finché non sono effettivamente provate.
4. Non caricare nel repository sorgenti EA, salvataggi, dati personali né mod di terzi.
5. **Primo traguardo:** voce MY HIGH SCHOOL sul menu originale a cerchio della cassetta postale, senza bloccare l'avvio. Solo dopo il picker e la persistenza.

Questo documento è un registro di lavoro, **non** una dichiarazione che la mod sia già funzionante.
