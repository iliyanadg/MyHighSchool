# Passo 30 — M28 pronta per UN test cumulativo, solo su salvataggio di prova

**Compilazione e test statici su Python 3.7:** GitHub Actions M28 #41143542150 completata con successo.
**Test reale in The Sims 4 su Mac:** ancora da eseguire. La riuscita dei test offline non prova la compatibilita dei nuovi picker.

## Cosa e implementato ora

1. Il registro M25 JSON esistente viene riletto senza migrazione di schema e puo contenere Classe 1, Classe 2 e Classe 3, ciascuna massimo 8 studenti. Non genera NPC casuali.
2. Menu cassetta postale M28: conserva i due picker di iscrizione e rimozione, aggiunge `Prepara iscrizione Classe 3` e `Rimuovi studenti - Classe 3`.
3. Lo script per la Classe 3 usa gli stessi comandi di iscrizione `mhs25.preview` e `mhs25.commit conferma` (solo registro test) e gli stessi comandi di rimozione `mhs27.removepreview` / `mhs27.removecommit conferma`.
4. La patch del bug M27 `'tuple' object has no attribute 'icon_resource'` e compresa. La risposta effettiva del picker e ancora da verificare nel gioco.
5. `mhs28.roster` elenca nella console fino a 3 classi, nome e cognome se il SimInfo e disponibile, ID e posti disponibili.
6. `mhs28.swappreview <sim_id_1> <sim_id_2>` prepara uno scambio fra due iscritti di classi diverse, anche se entrambe le aule sono piene. `mhs28.swapcommit conferma` lo applica atomico al JSON **solo** dopo nuovo controllo di slot e impronta del registro; `mhs28.swapcancel` annulla. Questa funzione ha **interfaccia console** nella M28, non ancora un picker grafico.
7. La rimozione nel registro non elimina il Sim. Non assegna presenze, aule fisiche, personale, situazioni EA.

## Installazione solo dopo chiusura del gioco

- Scaricare l'artifact dal workflow [M28 build](https://github.com/iliyanadg/MyHighSchool/actions/runs/41143542150).
- Rimuovere dalla Mods SOLTANTO la coppia M27 e conservarla fuori dalla cartella, poi inserire la coppia M28 scaricata.
- NON installare contemporaneamente M25, M27 e M28: solo **una** di queste coppie.
- Non toccare v1.6 o XML Injector, ne nessun altro file della Mods.
- Eseguire un solo giro di test su **salvataggio separato**, non sulla famiglia principale.

## Checklist in-game, in un solo ciclo

1. Aprire il salvataggio di prova; console `mhs28.roster` per leggere le 3 classi.
2. Aprire cassetta postale, verificare 3 iscrizioni e 3 rimozioni. Cercare la nuova voce Classe 3.
3. Testare il picker di rimozione Classe 1 **senza confermare scritture**. Se non apre, `mhs27.report` e screenshot.
4. Se la finestra si apre, scegliere un Sim e premere spunta; `mhs27.removepreview` e screenshot. Non usare ancora `removecommit`.
5. Testare il picker di iscrizione Classe 3 e visualizzare `mhs25.preview` ma senza `mhs25.commit conferma`.
6. Verificare `mhs28.roster` invariato. Reportare bug di input, crash o conflitti.
7. Solo con esplicita conferma su salvataggio test, provare commit/scambio/rimozione. **Attenzione: i commit modificano il JSON esterno anche se non si salva il gioco**.

## Limiti espliciti

- Un salvataggio ripristinato o duplicato NON ripristina automaticamente il registro JSON esterno. Prima di provare qualunque comando `commit`, fare copia di `MY_HIGH_SCHOOL_M25_TEST_DATA`.
- M28 non e una release definitiva e non va usata nella partita principale.
- La terza classe e facoltativa nel senso che si puo lasciare vuota, non ha ancora un interruttore di attivazione persistente.
- Nel menu manca ancora l'interfaccia grafica completa per scambio di classi piene e riepilogo con foto; nella M28 sono comandi diagnostici. Non descriverli come pulsanti presenti.
- La mod non controlla ancora che tutti e 24 i Sim siano presenti nello stesso lotto o in tre aule fisiche.
