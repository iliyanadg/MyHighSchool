# Passo 71 — M57b: falso conflitto Sonozaki risolto (Mac 31/10/2026)

## Screenshot del primo test M57 al liceo

La diagnostica M57 mostra:
- `Fonte slot: verified_zone_travel`, **slot 11**; classi 1/2 **8/8 ciascuna**.
- `Selezione M57: bloccata (altre mod liceo: ...)`, `Filtri limitati: 0`, `non modificati: 26`, `errori: 0`.
- Il blocco indica **due file che NON sono controller del liceo**:
  - `!_SonozakiSisters_KatieMods_MegaInteractions_ALLMERGED_Traduzione_ITA_[bySha_Tsita].package`
  - `SonozakiSisters_Elementary_School_Management_IT.package`
- `M57 Sim visibili sul lotto: iscritti 3/16; altri adolescenti 8 (inclusi 3 giocabili non iscritti); personale scelto 0/8`.
- `M57_PREFILTRO` (nessuna convocazione aggiuntiva della M56). Il motore scolastico di EA è stato riconosciuto correttamente, ma la selezione M57 non è stata applicata.
- `Giornata iniziata: 16 idonei`, zero richieste, `da elaborare: 16`. Quest'ultimo contatore riguarda il vecchio planner disattivato dalla M57: non equivale a 16 tentativi non riusciti del nuovo filtro.

## Diagnosi

Il detector precedente `mhs57_filter_runtime._find_conflicting_school_mods` conteneva un controllo **troppo generico sul nome `sonozaki`**. Qualunque pacchetto dell'autrice faceva bloccare tutti i filtri EA per liceo, anche una traduzione MegaInteractions o Elementary School Management.

**Non chiedere all'utente di eliminare Elementary School o Mega Interactions**, non sono una prova di conflitto sul liceo.

## Correzione M57b

- `mhs57_filter_policy.is_competing_high_school_mod`: whitelist di pattern per **controller EP12 del liceo** (high school management, choose high school classmates, more students, high school more classmates, ecc.). Un nome di autrice non è una condizione sufficiente.
- `mhs57_filter_runtime` usa il predicato precedente quando scansiona la cartella Mods all'avvio. Niente cancellazioni o alterazioni di mod utente.
- `tests/test_m57_ea_filter_policy.py`: usa i **due nomi esatti visti nello screenshot** per controllare l'assenza del falso positivo, e verifica che rilevi autentici High School Management, Choose High School Classmates e More Students.
- Coppia nuova `MHS_M57B_FILTRO_SCUOLA_FIX_CONFLITTI_MAC_TEST.package/.ts4script` compilata con **Python 3.7** tramite GitHub Actions. Conservare M56 come rollback.

## Test Mac M57b (dopo CI verde)

1. Chiudi The Sims 4, copia il salvataggio test e il registro esterno `MY_HIGH_SCHOOL_M25_TEST_DATA`. Rimuovi **entrambi** i file M57 precedenti e installa **entrambi** i file M57b della stessa CI.
2. Lascia installati i file MegaInteractions e Elementary School dell'utente: sono esattamente i falsi conflitti corretti. Rimuovere solo eventuali veri controller liceali incompatibili, senza toccare le altre mod.
3. Apri la partita dalla casa, segui i giocabili a Copperdale in una **nuova giornata scolastica**, perché EA sceglie i partecipanti all'inizio della giornata.
4. Apri la diagnostica M55: deve essere **`Selezione M57: installata`** (non `bloccata`), e verificare **`Filtri limitati: N`**. Se N=0, il controllo non ha ancora intercettato la selezione EA: non dichiarare che funziona.
5. Controlla il numero dei 16 iscritti **fisicamente presenti**, e le presenze/ruoli del personale. `M57 Sim visibili` conta solo Sim instanziati, non certifica i loro role EA; far avanzare tempo Sim per dare a EA occasione di completare la zona.
6. In caso di liceo vuoto, sim assenti, freeze, classi bloccate, tornare alla M56 senza sovrascrivere il salvataggio.

## Funzionalità non ancora risolte

- Nessuna garanzia che il motore EA accetti tutti i 16 studenti o 8 lavoratori: la capienza reale non è stata ancora aumentata.
- I cinque ruoli core (cheer, football, chess, computer, mean) non sono ancora gestiti da MHS.
- La terza aula, le lavagne e l'assegnazione effettiva dei docenti in classe non sono ancora collegate.
- I 3 adolescenti giocabili **non iscritti** Sofia Ogliari, Rosario Lanzafame e Sandro Paoletti vengono accompagnati da EA, senza posti riservati alle nostre classi. Per controllarli nel registro occorre liberarli e iscriverli manualmente negli otto posti per aula; farlo dopo l'esperimento M57b di confronto.
