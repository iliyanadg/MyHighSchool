# Passo 67 — M57: controllare la selezione EA PRIMA dello spawn, non dopo

## Evidenza concreta sul tuning, dal materiale già analizzato dell'utente

L'analisi storica `ANALISI_SONOZAKI_PER_MY_HIGH_SCHOOL.md` (archivio privato dell'utente, verificato 30/10/2026) documenta **un identificativo reale, non una supposizione**:

- Filtro EA originale: **`filter_HighSchool_Active_Student`, tuning 280516**.
- La mod Sonozaki 2.2.1 include **18 tuning filter XML**, oltre a picker, trait nascosti e loot. Non è dimostrato che si possano controllare tutti gli NPC con un solo filtro.
- Tra le interazioni già studiate: SimPicker Classe 1 18144138582290629883, Classe 2 14341772145049865184, Loot Class1 10693709237371872932, whitelist hidden trait 17792305569937722552. **Non ricopiare le risorse proprietarie Sonozaki**: questi identificativi descrivono comportamento osservato, non vengono inseriti nelle nostre risorse.
- Il tratto EA `trait_HighSchool_Active_Class1Student` ha tuning **293779** ma da solo non determina la classe giocabile reale. Nell'esperimento v1.11 un Sim giocabile assegnato a Classe 2 ha comunque seguito la lezione fisica in Classe 1: occorre un adapter specifico per playable.

Questa evidenza è più solida del nostro M55 che crea situazioni aggiuntive con GUID 277733: quando EA ha già selezionato i propri NPC, creare altre situazioni non sostituisce gli NPC esistenti.

## Conferme indipendenti da mod pubbliche

- `Choose Your High School Classmates` di konanhurry, sul sito ufficiale CurseForge, indica cinque Core NPC obbligatori: **Mean, Chess, Cheer, Football, Computer**. La versione «Strict» modifica filtri EA e può confliggere con altri tuning override. https://www.curseforge.com/sims4/mods/choose-your-high-school-classmates
- Simvasion `High School Years Tweaks` dice esplicitamente di modificare un **filtro originale di selezione degli studenti** e di poter entrare in conflitto con altri override: https://simvasion.com/high-school-years-tweaks/
- SonozakiSisters `Choose High School Classmates 2.1`: liceo EA di default **10 studenti complessivi (5 per ciascuna delle 2 classi)**; alcuni ruoli speciali vengono assegnati alla Classe 2; gli adolescenti giocabili accompagnati riducono il totale di NPC da iscrivere. Per due classi con più alunni serve un cambiamento delle situazioni/capienza reale, NON basta cambiare i numeri del nostro registro. https://www.patreon.com/posts/choose-high-2-1-132672857
- La stessa guida Sonozaki esclude o segnala personaggi con ruoli EA incompatibili (per esempio **Baby Ariel** e fantasmi) dalle nomine ordinarie di compagno. In Classe 1 MHS TEST risulta Baby Ariel: verificare idoneità e ruolo prima di presumere che debba arrivare fisicamente.
- Aramiteus `High School More Classmates` documenta assegnazione di più aule mediante lavagne e controlli faculty; l'utente **non** vuole reinstallare More Students 18, che precedentemente ha causato freeze e NPC invisibili. https://www.nexusmods.com/thesims4/mods/1463

## Architettura da implementare nella M57

1. **Inventario dei tuning EA realmente estratti dal gioco aggiornato**, partendo dal filtro 280516 e dai filtri dei ruoli Core NPC (principal/teacher/janitor/cafeteria e membri delle cinque squadre). Documentare TGI, reference e capienza effettivi per la patch attuale. Non inventare gli ID mancanti.
2. **Registro autorevole per slot** `Registro_slot_*.json` più `Personale_slot_*.json` già funzionanti. Filtrare il `SimInfoManager` e i ruoli con lista esatta di SimID, includendo i teen giocabili che occupano 1/8 posti; saltare NPC non idonei e non generarne altri.
3. **Selezione EA preventiva**: al momento in cui EA sceglie il personale e gli allievi, fornire un filtro o punteggio deterministico che ammette i soli ID selezionati, per ciascuna categoria, senza modificare tratti in modo permanente o sovrascrivere altri filtri non analizzati.
4. **Capienza EA separata dai posti del registro**: partire da una situazione con limite documentato, modificare solo quanto serve, mantenere i requisiti dei 5 Core NPC e gli slot per giocabili. Il nostro obiettivo 8×2 e poi 8×3 richiede prove prestazionali e un sistema scolastico esteso; non promettere 16/24 fisici automaticamente.
5. **Classe reale**: integrare 2 classi, 2 docenti e lavagne, con routing verificato e senza tradire l'ordine di EA (pranzo, esami, prom, graduation). Una vera terza classe necessita situazione/lezione aggiuntiva e lavagna assegnata; non basta registrarla nel JSON.
6. **Conflitti**: rilevare altri mod controller del liceo e bloccare l'attivazione (non cancellare file dell'utente); non sovrascrivere lo stesso filtro 280516 mentre Sonozaki o Rex Strict sono installati. Versione Mac/Python 3.7 e compatibilità patch da testare.
7. **Diagnostica fisica**: rapportare tre quantità distinte: iscritti JSON, SimID selezionati dalla situazione EA, Sims effettivamente instanziati sul lotto e in aula. L'ID di `create_situation` non è una presenza confermata.

**Il Passo 67 è ricerca e architettura:** nessun override EA o controllo dei 16–24 Sims è stato ancora compilato e validato. La M56 attuale riguarda lo slot stabile a scuola; mantenere `main` M54 e il ramo di prova separati.
