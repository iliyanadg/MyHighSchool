# Passo 73 — M57d: diagnosticare quali filtri EA scegliono davvero la popolazione

## Mac screenshot M57c del 31 ottobre 2026 (ore ~21:12)

La creatrice ha installato M57c e inviato tre schermate durante il primo mattino scolastico (alle ~8:25, ~8:28 e ~8:36). L'ultima finestra registra:

```
Automazione M55: installato
Controlli eseguiti: 20 | M57_PREFILTRO
Fonte slot: verified_zone_travel | slot verificato: 11
Selezione M57c: installata
Filtri limitati: 0 | non modificati: 10 | errori: 0
Ultimo: preserve filtro 303766: Ruolo speciale EA, nessuna restrizione
Ultimo errore: nessuno
M57 Sim visibili sul lotto: iscritti 4/16; altri adolescenti 7;
personale scelto 0/8 (presenza, NON ruolo EA)
Registro slot 11: C1 8/8, C2 8/8
Giocabili adolescenti della famiglia: 3
Non iscritti: 3 — Sofia Ogliari, Rosario Lanzafame, Sandro Paoletti
Ultimo evento: GIORNATA_INIZIATA: Iscritti idonei 16 / non idonei 0
Iscritti previsti: 16 / convocazioni richieste: 0
Da elaborare: 16
```

## Interpretazione corretta

- **Il difetto M57b che provocava 26 `ManifestError` è stato eliminato**. L'ID 303766 è `filter_HighSchool_Active_MeanSim` (Zerbu EP12). È normale preservarlo per ora: non è un filtro ordinario di iscrizione.
- **Non c'è evidenza di una vera selezione MHS riuscita**: `Filtri limitati=0`. Almeno 4 iscritti sono presenti, ma possono essere stati scelti da EA indipendentemente.
- Il personale configurato resta assente `0/8`. Questo numero riguarda i Sim istanziati, non prova di impiego/ruolo.
- I numeri `convocazioni=0` e `da elaborare=16` fanno riferimento al vecchio planner M56 che la M57 disabilita intenzionalmente: non sono 16 errori o assenze e non devono più essere mostrati come indicatore della M57.
- Attuale filtro candidato scolastico normale **280516**, staff specifico 296396, 300741, 300742, 300743, 300744; tra i preset EP12 pubblici esiste anche **`filter_HighSchool_Active_Faculty` 280457** generico, non ancora controllato dal sistema. Il servizio EA può chiamare altri filtri o altre API **prima** che il gioco mostri il liceo attivo.

## Modifica M57d

- `src/m57_selection/mhs57_filter_runtime.py`: aggiunge la sola telemetria del servizio `SimFilterService.submit_filter` e `submit_matching_filter`, memorizzando soltanto **GUID + conteggi** (max 64 identificativi recentemente osservati), senza SimID, nomi, XML del save o modifica EA.
- La diagnostica mostra le chiamate complessive, le chiamate riconosciute ai filtri scolastici, il contatore del filtro faculty generico **280457** e gli 8 ID richiesti più spesso. Nota: si osservano chiamate generali al servizio da parte del gioco, non tutte necessariamente appartenenti alla scuola; va sempre interpretato con il contesto di zona e giorno.
- **Non** limita ancora il filtro generico 280457: finché non sappiamo come assegnare un ruolo e rispettare i requisiti EA, forzarlo potrebbe selezionare personale errato.
- `src/m55_attendance/mhs55_attendance_auto.py`: mostra il dato `filter_observation_status()` nel pannello scolastico e sostituisce i vecchi contatori `pending` M56 con l'indicazione che non hanno significato nella M57.
- `tests/test_m57_ea_filter_policy.py`: test Python 3.7 delle chiamate GUID ripetute, cap a 64 filtri, distinzione fra core/staff/filtri generici, e protezione dal vecchio riepilogo fuorviante.
- Compilazione separata `MHS_M57D_TELEMETRIA_FILTRI_EA_MAC_TEST.package/.ts4script`, mantenendo M56 come rollback. Non alterare `main` e non affermare che i roster EA siano risolti.

## Test Mac dopo compilazione verde

1. Backup del salvataggio TEST e dei dati esterni di MY HIGH SCHOOL. Sostituire entrambi i file M57c con M57d compilati nella stessa run; non mescolare versioni.
2. Aprire casa poi nuovo giorno di liceo; se un vecchio salvataggio è già nel liceo, non dà la stessa sequenza di selezione prima dello spawn.
3. Verso le 8:20–9:00 aprire `M55 - Consulta presenze automatiche`. Rilevare `M57d API EA: chiamate... faculty generico 280457 ... ID frequenti...`, `Filtri limitati`, `errori` e `Sim visibili`.
4. Se compaiono solo 303766 o altri GUID non filtrati, la M58 dovrà intervenire nel punto in cui EA prepara la lista situazioni/guest e i filtri, e non aggiungere situazioni dopo la selezione.
5. Nessuna cancellazione di altri mod, nessuna iscrizione forzata dei giocabili, nessuna promessa di 16/24 presenze fisiche fino a test effettivi.

Fonte per mappatura preset: https://github.com/Zerbu/Mod-Constructor-5/blob/master/Constructor5/Presets/SimFilter/AllSimFiltersEP12.Presets.xml .
