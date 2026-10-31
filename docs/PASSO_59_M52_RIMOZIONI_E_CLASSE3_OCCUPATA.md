# Passo 59 — M52 rimozioni multiple e disattivazione Classe 3 occupata (31 ottobre 2026)

## Verifiche reali M51 segnalate dall'utente
- Classe 1 e Classe 2: iscrizioni multiple riuscite, 8 iscritti per classe nel registro.
- Classe 3: Amarachi e Hugo, poi Yuki e Sofia trasferite dalla Classe 2 in una sola selezione. Trasferimento multiplo confermato funzionante.
- Rimozione di Baby Ariel in Classe 1: la finestra vecchia permette una persona per volta, ma non aggiorna il registro né in pausa né col tempo attivo.
- «Disabilita Classe 3»: la classe rimane visibile. È **previsto** quando ci sono studenti: SettingsStore.set_class_count rifiuta il passaggio da 3 a 2 classi se il registro contiene iscritti alla Classe 3. Il vecchio comando falliva in silenzio; serve un avviso esplicito.

## Diagnosi
Il vecchio `mhs27_remove_ui.py` imposta soltanto `_PENDING` alla spunta e richiede `mhs27.removecommit conferma` nella console. Non salva tramite GUI. Inoltre non configura un limite multi-select EA: usa il picker con il default.

## Correzione M52
- Nuovo `src/m52_removal/picker.py` (compilato nel .ts4script come `mhs52_picker.pyc` per evitare collisioni con altre mod) costruisce un UiSimPicker con massimo 8 selezioni, limitato agli iscritti della classe selezionata.
- `✓`: verifica ID/slot, classe attiva, snapshot invariato, calcola `plan_removal`, scrive una volta con RosterStore.save, mostra notifica con conteggio. `X`: chiude senza modifica. Nessun Sim viene cancellato dal gioco.
- `mhs39_visibility_ui.py` conserva l'elenco SPECS originale richiesto dai vecchi builder XML, ma per le sole tre rimozioni carica la nuova classe Python M52. Nessuna modifica al DBPF menu M51.
- `mhs34_settings_ui.py`: se una classe 3 occupata non può essere disattivata, notifica il motivo. Non nasconde la classe mentre contiene iscritti.
- `tooling/build_m52_removal.py`: produce 2 file M52 compatibili con Python 3.7, 18 moduli compilati, DBPF identico a M51 con 5 categorie e SimData originali.
- Test: `tests/test_m52_multi_removal.py` copre multi-removal con un clic, cancel, blocco con gestione disattivata e avviso Classe3. Le regressioni M45/M51 e M34 sono superate.

**CI build:** https://github.com/iliyanadg/MyHighSchool/actions/runs/41215443170 — SUCCESS (compilazione e regressioni selezionate).

**Stato:** compilato, **non ancora testato in game**. Non dichiarare già risolta la rimozione sul Mac.

## Test Mac consigliato
1. Conservare M51 e backup del registro esterno `MY_HIGH_SCHOOL_M25_TEST_DATA` con gioco chiuso. Sostituire unicamente i due file M51 con i due M52. Lasciare le altre mod.
2. Nella partita di prova: Classe 1 -> Rimuovi studenti -> selezionare Baby Ariel e un altro studente che si desidera ritirare; premere ✓. Verificare notifica ed elenchi di Classe 1 (devono sparire) e nessun Sim eliminato.
3. Nella Classe 3 **ancora occupata** premere Disabilita Classe 3: deve mostrare un avviso esplicativo, senza nascondere i 4 iscritti. Solo dopo avere spostato o ritirato tutti dalla Classe 3 si può disabilitarla.
4. Se Better Exceptions, non ripetere il click; uscire e ripristinare M51.

Il progetto richiede *Vita da Liceali* (High School Years/EP12). Controllo pack runtime e frequenza fisica al liceo sono ancora da implementare.
