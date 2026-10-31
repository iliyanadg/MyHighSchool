# Passo 69 — M57: prima di invocare, scegliere la scuola EA (riscontro Mac 31/10/2026)

## Nuova osservazione sul Mac (M56 confermata)
Dopo la rilevazione dello slot 11 e le convocazioni automatiche, la giocatrice vede **alcuni** dei 16 iscritti selezionati, per esempio Ollie Mark, Yuki Behr, Jeb Harris, Wolfgang Munch, Kiyoshi Ito, Nyon Specter, Savannah Prezzo. Ma EA lascia i compagni propri, per esempio Duane Talle, Morgan Fyres e Molly Prescott, e il personale originale:

- **EA docente Aula 1**: Giuliano Papanice; invece registro MHS: Geoffrey Landgraab.
- **EA docente Aula 2**: Angelo/Anjelo Morlind; invece registro MHS: Akira Kibo.
- **EA preside**: Mei Flex; invece registro MHS: Kai Aether.
- **EA custode**: Tai Lum; invece registro MHS: Bjorn Bjergsen e Gianluca Ferraro.
- **EA mensa**: Ava Harjo; invece registro MHS: Agnes Crumplebottom, Alex Moyer e Alessia Sanna.
- Tre teen giocabili al liceo, **Sofia Ogliari, Rosario Lanzafame, Sandro Paoletti**, non sono nel registro MHS. Il loro arrivo è gestito da EA. Per farli parte delle classi MHS devono essere iscritti manualmente, entro un totale di 8 compresi gli NPC.

**Conclusione:** M56 ha risolto slot e letto 16 nomi, ma `create_situation(277733)` invia persone *in aggiunta* alla coorte già scelta da EA. Questo non garantisce 16 presenti né la corretta aula; non è un controller scolastico. La piccola notifica blu vuota dopo il tempo di gioco non conferma il successo: il resoconto MHS lungo può essere troncato nella UI.

## Ricerche pubbliche da tradurre in un adapter EA originale

L'autrice Sonozaki (fonte https://www.patreon.com/posts/high-school-2-2-153195289) elenca i filtri che il suo management deve intervenire: NON solo `filter_HighSchool_Active_Student` 280516, ma:

Studenti/eventi:
- filter_HighSchool_Active_Student
- filter_HSStudent_CheerTeam
- filter_HSStudent_FootballTeam
- filter_HSStudent_ChessTeam
- filter_HSStudent_ComputerTeam
- filter_HighSchool_Active_MeanSim
- filter_HSStudent_TeamRival
- filter_HSStudent_GraduatingNPC
- filter_HSProm_Teen, filter_HSProm_Teen_PreProm, filter_HSProm_Teen_PostProm

Staff:
- filter_HighSchool_Active_Faculty_Principal
- filter_HighSchool_Active_Faculty_Teacher
- filter_HighSchool_Active_Faculty_Teacher2
- filter_HighSchool_Active_Faculty_Janitor
- filter_HighSchool_Active_Faculty_CafeteriaWorker

Simvasion conferma una riscrittura del filtro che convoca studenti nel liceo attivo, con possibili conflitti: https://simvasion.com/high-school-years-tweaks/. **Nessun tuning originale o codice proprietario è stato copiato.** Il vero tuning aggiornato della patch EA va ancora verificato prima di scrivere un override.

## Cosa è implementato ora nel ramo M57

`src/m57_selection/mhs57_school_manifest.py` introduce il **piano di selezione puro** e deterministico, con:
- SimID esatti dal `SchoolRoster` e `StaffRoster` dello stesso slot, classi 1–3 fino a 8 studenti ciascuna, inclusi gli adolescenti della famiglia attiva soltanto se iscritti.
- Separazione fra `all_student_ids`, `to_invite` (non giocabili), `playable_in_classes` e `playable_unenrolled`.
- Corrispondenza staff ai ruoli `principal`, `teacher1/2/3`, `cafeteria`, `custodians`; blocca doppi incarichi e uno stesso Sim indicato come studente e personale.
- `compare_live_ids`: distingue iscritti nel registro, iscritti fisicamente presenti, iscritti mancanti, NPC non iscritti osservati e personale corretto/errato, **senza** creare né eliminare situazioni EA.
- Test in `tests/test_m57_school_manifest.py`, GitHub Actions `.github/workflows/m57-school-manifest.yml` con Python 3.7.

**Il manifest è codice originale scritto e pushato, NON un override EA già funzionante.** Non viene incluso nella coppia M56 installata, e non presenta nuove interazioni nel menu. Non installare files M57 del manifest: non ci sono ancora binaries.

## Condizioni per il prossimo controller installabile

1. Confrontare filtri/tuning attuali di EA e metodi di servizio filter/situation, poi scegliere il punto d'iniezione meno conflittuale e reversibile **prima che EA generi gli NPC**.
2. Collegare il `SchoolManifest` alla lista vera di candidati per studenti normali, cinque ruoli core e faculty. I ruoli core non sono ancora nel registro MHS: richiederanno interfaccia/assegnazione o un policy engine che rispetta i requisiti EA, senza NPC casuali.
3. Gestire la capacità *reale* delle situazioni: il limite 8/classi in JSON non cambia la capacità di due aule native EA; la terza aula richiede un controller aula autonomo e lavagna.
4. Evitare installazione insieme a Sonozaki, More Students, altri filtri scolastici in conflitto. Salvataggi test, monitor freeze/duplicati/prom.
5. Test in-game su due classi con alunni giocabili, uno staff scelto e tutti i 5 ruoli speciali. Solo il confronto dei SimID **fisicamente presenti** può confermare il successo; non basta un numero di richieste create.

## Adesso nel gioco
Non richiedere ulteriori prove di minuti Sim: gli screenshot hanno già dimostrato il problema. Non cambiare il registro e non correggere manualmente gli NPC EA con trucchi. Per questo salvataggio di prova M56 resta una versione diagnostica/di convocazione parziale; eventuali test con i filtri EA dovranno iniziare da un backup, senza salvare sopra la partita principale.
