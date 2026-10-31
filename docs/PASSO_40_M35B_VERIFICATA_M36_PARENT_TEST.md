# Passo 40 — conferma M35B e build M36 parent-only (31/10/2026 ore 03:27)

## Verifica M35B su The Sims 4, Mac, save TEST slot 11

La giocatrice ha inviato sette screenshot:
- La cassetta postale apre normalmente i menu, senza nuovo blocco UI.
- La nuova categoria separata `Classe 1 - M35 PROVA` è comparsa davvero come **voce comprimibile**.
- Il click apre due azioni, `Consulta iscritti - Classe 1` e `Rimuovi studenti - Classe 1`.
- Entrambi i selettori fotografici si aprono e mostrano soltanto Amarachi Darong e Baby Ariel (2 iscritti della Classe 1).
- Tutte le altre azioni M35B restano sparse nel menu `MY HIGH SCHOOL (M35 SMOKE TEST)`; **non è la struttura finale**.
- Non sono stati eseguiti `commit conferma`; la prova non modifica il registro.

**Conclusione tecnica:** non manca la registrazione di questa singola nuova categoria. Il problema M35 con una sola azione deriva dal comportamento pie-menu che la visualizzava direttamente invece che come sottomenu. **Per comparire come categoria nell'esperimento, con _collapsible=1, sono servite due azioni.**

## Esatta UX finale richiesta e riconfermata (non negoziabile)

```text
Cassetta postale / PC
  └─ MY HIGH SCHOOL
       ├─ Attiva / Disattiva MY HIGH SCHOOL
       ├─ Classe 1  (solo se mod attiva)
       │   ├─ Iscrivi studenti
       │   ├─ Consulta iscritti
       │   ├─ Rimuovi studenti
       │   └─ Trasferisci in Classe 2 / Classe 3 se abilitata
       ├─ Classe 2  (solo se mod attiva)
       │   ├─ Iscrivi / Consulta / Rimuovi
       │   └─ Trasferisci in Classe 1 / Classe 3 se abilitata
       ├─ Classe 3  (solo se mod attiva E classe 3 abilitata)
       │   ├─ Iscrivi / Consulta / Rimuovi
       │   └─ Trasferisci in Classe 1 / Classe 2
       └─ Impostazioni (solo se mod attiva)
           └─ Abilita Classe 3 / Disabilita Classe 3
```

**La scelta di iniziare con 2 classi non è definitiva:** si deve SEMPRE poter abilitare successivamente Classe 3, anche dopo aver già registrato studenti in Classe 1 e 2. Una volta abilitata, la Classe 3 compare nel menu con capienza 8 e nessun NPC auto-assegnato. Se Classe 3 contiene studenti, la disabilitazione deve essere bloccata fino a trasferimento/rimozione dal registro (mai cancellare i Sim).

Rimangono richieste: gestione e conferma anche mentre l'orologio è in pausa, operazioni senza console; attivazione/disattivazione senza perdere registri e impostazioni; liceo EA non ancora controllato dal prototipo.

## Nuova build M36 di prova

La M36 NON è il menu finale. Usa come base la M35B verificata; introduce **una sola modifica funzionale**: all'unica categoria Classe 1 già funzionante aggiunge `_parent` con riferimento alla categoria `MY HIGH SCHOOL`, sia nel tuning XML, sia nella SimData binaria. Nessuna altra interazione o script cambia.

Compilazione: https://github.com/iliyanadg/MyHighSchool/actions/runs/41160463498

Artefatto: `MHS_M36_SOLO_PARENT_CLASSE1_TEST`, contiene:
- `MHS_M36_PARENT_SOTTOMENU_CLASSE1_TEST.package`
- `MHS_M36_PARENT_SOTTOMENU_CLASSE1_TEST.ts4script`

Test offline passati con Python 3.7, 29 risorse, 2 categorie + 2 SimData.
Questo **NON dimostra** che il collegamento padre/figlia funzionerà nel gioco: M30/M32 bloccavano la cassetta e il link del menu è la sola variabile ora testata.

## Test nel client reale, su salvataggio test

1. Con gioco chiuso, copia di sicurezza della directory `MY_HIGH_SCHOOL_M25_TEST_DATA`, se non già disponibile; togli dalla Mods i due file M35B, mettili in un posto sicuro assieme a M34.
2. Inserisci esclusivamente la coppia M36 (mai più versioni della mod insieme), quindi riapri The Sims 4 in save test.
3. Clicca sulla cassetta postale. Se è bloccata o c'è UI Exception/invalid category ID, chiudi **senza salvare**, rimuovi M36 e ripristina M35B o M34; invia screenshot del report.
4. Se si apre, entra in MY HIGH SCHOOL e verifica che lì compaia `Classe 1 - M35 PROVA`; aprila e verifica che contenga le due voci di sola prova.
5. Non selezionare alcun Sim da rimuovere e **non eseguire commit**.
6. Se M36 funziona, nella build cumulativa successiva aggiungere Classe 2/3, stato della mod e visibilità dinamica in base a config; testare la verifica visiva in gioco, non affidarsi soltanto ai test Python.

## Sviluppo del modello menu

`src/m35_menu/mhs35_menu_model.py` contiene ora anche `settings_options`: in modalità 2 classi la voce `abilita_classe3` resta abilitata; in modalità 3 diventa `disabilita_classe3`, bloccata quando il registro classe 3 contiene studenti. `tests/test_m35_menu_model.py` controlla esplicitamente la possibilità di aggiungere Classe 3 DOPO aver attivato le due classi. È un modello logico, NON è ancora interfaccia live.
