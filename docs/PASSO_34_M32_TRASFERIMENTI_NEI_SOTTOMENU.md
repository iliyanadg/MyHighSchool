# M32 — altre operazioni direttamente nei sottomenu (31 ottobre 2026)

## Richiesta e struttura
L'utente ha chiesto di aggiungere altre funzioni all'interno delle tre classi prima di installare un nuovo aggiornamento. Il menu M30/M31 comprende tre sottocategorie native. M32 aggiunge **sei nuove voci**, due per classe:

- MY HIGH SCHOOL → Classe 1 → Trasferisci in Classe 2 / Trasferisci in Classe 3
- MY HIGH SCHOOL → Classe 2 → Trasferisci in Classe 1 / Trasferisci in Classe 3
- MY HIGH SCHOOL → Classe 3 → Trasferisci in Classe 1 / Trasferisci in Classe 2

Le vecchie operazioni **Iscrivi**, **Consulta iscritti**, **Rimuovi** rimangono nello stesso sottomenu, insieme alle due nuove. Non sono duplicate sotto MY HIGH SCHOOL.

## Come funziona il trasferimento
1. Il comando in Classe A → Classe B apre un picker fotografico con **soltanto gli iscritti a Classe A** presenti nel SimInfoManager.
2. Prima dell'apertura il sistema legge la capienza (massimo rigido otto iscritti nella Classe B), e blocca se non ci sono posti o se Classe A e vuota. Classi piene possono comunque **scambiare due studenti** tramite la funzionalita console di M28, che rimane disponibile.
3. Dopo la selezione di uno o piu Sim, viene creato **solo un piano in memoria**. La spunta non scrive dati.
4. Comando diagnostico `mhs32.transferpreview`: numero di studenti, nomi e classi prima/dopo.
5. Solo il comando `mhs32.transfercommit conferma` aggiorna il **registro JSON esterno TEST**. Ricontrolla lo slot di salvataggio, l'impronta del registro (nessuna modifica concorrente), l'appartenenza alla classe di origine, l'adolescenza dei Sim e la capienza della destinazione. Scrive una sola volta in modo atomico.
6. `mhs32.transfercancel` annulla la selezione; `mhs32.report` riporta eventuali motivi del blocco senza modificare i dati.

## Nessuna modifica reale alla scuola EA
- Questo e ancora un **registro iscritti** separato dai salvataggi `.save`. Non modifica le situazioni delle lezioni, le aule fisiche, gli insegnanti o la presenza al liceo.
- I Sim non vengono eliminati.
- Il programma di protezione e annullamento ultima modifica introdotto con M29 rimane disponibile (comando `mhs29.undo conferma`), ma si applica solo al JSON esterno.
- Non promettere che i nuovi picker si aprano nel gioco; la M31 non ha ancora concluso i test Mac.

## Compilazione
- Build cumulativa **M32**: file `MHS_M32_SOTTOMENU_TRASFERIMENTI_TEST.package` e `MHS_M32_SOTTOMENU_TRASFERIMENTI_TEST.ts4script`.
- GitHub Actions: https://github.com/iliyanadg/MyHighSchool/actions/runs/41146419685
- 29 risorse DBPF (contro le 23 di M31), 10 moduli bytecode Python 3.7. I test offline verificano categoria corretta, unica registrazione, protezione delle classi piene, commit esplicito e assenza di scritture alla sola selezione.

## Prima verifica in gioco, quando l'utente decide di provarla
1. Terminare la partita di prova senza eseguire commit e **chiudere il gioco**.
2. In Mods tenere una sola coppia sperimentale: spostare M29/M30/M31 all'esterno e sostituire con M32. Lasciare v1.6 e XML Injector. Conservare un backup del JSON di prova.
3. Aprire salvataggio TEST; verificare i 3 sottomenu con 5 operazioni ciascuno. Testare **Consulta iscritti Classe 1** e **Rimuovi studenti Classe 1** senza scritture, con diagnostiche `mhs29.report` / `mhs27.report` se falliscono ancora.
4. Nel menu Classe 1, provare **Trasferisci in Classe 3** (destinazione vuota nel registro TEST mostrato nell'ultimo screenshot). Il picker dovrebbe mostrare solo Baby Ariel e Amarachi Darong, non le due Sofie di Classe 2.
5. Se il picker apre, selezionare un solo studente, poi `mhs32.transferpreview`. **Non eseguire `mhs32.transfercommit conferma`** nel primo giro.
6. Se non apre, `mhs32.report`. I dati del registro dovrebbero rimanere Classe 1: 2/8, Classe 2: 2/8, Classe 3: 0/8 se non sono stati eseguiti altri commit.

La versione rimane sperimentale e non va usata nella partita principale.
