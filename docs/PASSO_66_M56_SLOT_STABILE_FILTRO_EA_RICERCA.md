# Passo 66 — M56: identità del salvataggio a Copperdale e meccanismi di EA

## Verifica Mac del 31 ottobre 2026 (M55c)

L'interazione M55c mostra **Controlli eseguiti: 16–20**, ma l'ultimo gate è:

```
ERRORE: AttendanceError: Identita del salvataggio non disponibile
Registro: diagnosi non disponibile (AttendanceError)
Giornata liceale: non ancora rilevata
```

Nella stessa zona compare normalmente il giorno scolastico EA (inizia alle 8, finisce alle 15). Il menu cassetta postale mostra soltanto «Classe 1», perché il mixin `mhs39_visibility_ui.py` blocca le altre azioni quando `mhs_m2_game_bridge.current_slot()` riceve lo scratch slot 0.

## Ricerca tecnica verificata

1. **Fonte pubblica MIT: Lot51 Core Library**, `utils/context.py`:
   `Context.save_slot_id` restituisce `str(services.get_persistence_service().get_save_slot_proto_guid())`. La documentazione ufficiale Lot51 afferma che tale identificativo **non cambia quando il gioco passa a uno scratch save** durante il viaggio. Link: https://github.com/lot51/core-library/blob/main/utils/context.py , https://github.com/lot51/core-library .
2. **Modder riv_rel** documenta lo slot `00000000` in seguito a cambio zona o modalità, e problemi di MCCC autosave che può variare lo slot. https://rivforthesesh.itch.io/riv-rel/devlog/209749/squashing-some-more-bugs .
3. **Choose Your High School Classmates / konanhurry** usa una selezione preventiva dei Sim e cinque ruoli richiesti per Core NPC: mean teen, chess, cheer, football e computer. La versione «Strict» sovrascrive filtri EA ed espone incompatibilità. https://www.curseforge.com/sims4/mods/choose-your-high-school-classmates
4. **Simvasion High School Tweaks** dichiara di modificare il filtro NPC che convoca studenti al liceo e avverte dei conflitti con altri override dello stesso tuning: https://simvasion.com/high-school-years-tweaks/
5. **High School More Classmates / Aramiteus** documenta iscrizione attraverso la cassetta postale, classi multiple con lavagne, e gestione del personale: https://www.nexusmods.com/thesims4/mods/1463 .
6. **Sims4CommunityLibrary** espone funzioni per interrogare situazioni EA e crearle con guest list; il fatto che venga creato un ID situazione NON garantisce che il Sim arrivi, si sieda o sostituisca NPC spontanei: https://github.com/DeviantGameMods/Sims4CommunityLibrary/blob/main/Scripts/sims4communitylib/utils/sims/common_sim_situation_utils.py .

Nessun sorgente di mod di terzi è stato copiato: solo interfacce EA pubblicamente documentate e analisi delle descrizioni.

## M56: correzioni implementate nel branch

### Identità per salvataggio
- `src/m2_registry/mhs56_slot_identity.py`: classe pure Python `TravelSlotGuard`, associa il **guid stabile** al **vero numero di slot** osservato con `get_save_slot_proto_buff().slot_id` quando non è zero, insieme all'ID della famiglia attiva. I due valori **non sono assunti uguali** (il guid potrebbe avere un formato differente).
- Dopo il viaggio, se EA restituisce slot 0, permette il recupero in memoria solo se **guid stabile + nucleo attivo** combaciano con l'ancoraggio verificato nella medesima sessione. Se cambiano il salvataggio, la famiglia o il guid non è leggibile, non usa un slot a caso e si blocca.
- `current_slot(allow_travel=False)` rimane **strict** per tutte le scritture di iscrizioni, rimozioni, trasferimenti, configurazione e assegnazioni del personale.
- Solo le operazioni di consultazione del registro e la convocazione EA **transiente** usano `current_slot(allow_travel=True)`. Non scrivono dati nel JSON durante lo scratch slot.
- Il progetto non dipende dal pacchetto Lot51 installato, perché richiama direttamente l'API EA individuata nella documentazione open source. In presenza di un aggiornamento EA che rimuove il metodo il sistema non inventa uno slot.
- I test `tests/test_m56_stable_school_slot.py` coprono anchor casa→scuola, assenza anchor, divergenza guid, cambio famiglia, e rifiuto delle modifiche allo scratch slot.

### Visibilità del menu al liceo
- `mhs39_visibility_ui.py` usa il solo accesso di lettura verificato per calcolare Classi 1/2/3 e mostrare le sezioni originali senza errore dello slot.
- La consultazione iscritti Classe 1 e il riepilogo del personale possono leggere il registro durante lo scratch slot; rimozioni/iscrizioni/assegnazioni restano bloccate in quel contesto per salvaguardare i JSON.
- `mhs55_attendance_auto.py` non si ferma più soltanto perché il proto EA del liceo riporta 0, se esiste la validazione precedente nella sessione.

### Limitazioni deliberate
- L'ID stabile non garantisce da solo una corrispondenza con il numero del registro: per questo serve una validazione positiva prima del viaggio.
- Se il giocatore avvia il gioco **direttamente da una partita salvata nel lotto del liceo**, può non esserci alcun ancoraggio e il menu verrà bloccato. Non inferire la partita da un nome di Sim o da file arbitrari.
- Il controller **non sostituisce ancora i filtri di scelta dei compagni** e non assegna ai Sim del personale i rispettivi situation jobs EA. La M56 risolve una precondizione fondamentale prima di implementare questi sistemi.
- Massimo 8 studenti TOTALI per aula, inclusi i giocabili, senza duplicare gli adolescenti già accompagnati a scuola. Classe 3 senza aula EA autonoma finché non sarà testata.

## Test Mac

Solo in **salvataggio di prova**, con la coppia M56 compilata da un'unica GitHub Actions run verificata. Chiudere The Sims 4, rimuovere la precedente coppia M55c, installare i due file M56, e **aprire inizialmente la partita dalla casa**, così lo slot e il guid stabile sono legati insieme. Poi accompagnare gli adolescenti al liceo *senza chiudere il gioco fra casa e scuola*, far scorrere 15–30 minuti Sim e consultare il menu sulla cassetta postale.

Esiti da verificare, nell'ordine:
1. Tornano visibili Classe 1 e Classe 2 e il personale, non solo Classe 1.
2. Il diagnostico mostra `Fonte slot: verified_zone_travel` e i conteggi iscritti (se non lo mostra, aggiornare UI diagnostica).
3. Il gate supera «Identita del salvataggio non disponibile» e arriva a situazione liceo non rilevata / giornata avviata.
4. Solo allora contare i Sim presenti fisicamente, distinguendo ID situazione creata, NPC spontanei, giocabili e iscritti.

**Nessun test in-game M56 è stato completato. Non fare merge in main né dichiarare che 16–24 studenti o il personale scelto siano in aula.**
