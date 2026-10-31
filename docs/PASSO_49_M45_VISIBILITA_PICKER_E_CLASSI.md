# Passo 49 — M45, rendere invisibili tutte le classi con scuola disattivata e Classe 3 opzionale

## Bug riprodotto dall'utente su Mac, 31 ottobre 2026 ore 13:57

Con M44 il menu era finalmente correttamente annidato, ma:
1. `Impostazioni -> Disabilita Classe 3` cambia l'azione in `Abilita Classe 3`, **ma il sottomenu Classe 3 resta visibile**.
2. `Disattiva MY HIGH SCHOOL` cambia la voce in `Attiva MY HIGH SCHOOL`, **ma le tre classi restano visibili**.
3. `Consulta iscritti - Classe 1` apre il picker in pausa, con i due nomi Amarachi Darong e Baby Ariel; NON costituisce ancora verifica di gestione del registro in pausa.

## Causa trovata nel package M44

Inventario tuning: 22 `SuperInteraction`/picker, di cui 3 sono `SimPickerInteraction` originali non coperti dal mixin M39 e 19 erano già protetti dal controllo `_test`.

I 3 unguarded picker erano:
- `Iliyana_MHS_M0_ChooseClass1` (id 10604127343160706865), categoria Classe 1;
- `Iliyana_MHS_M0_ChooseClass2` (id 10604124044625822232), categoria Classe 2;
- `Iliyana:MHS28_ChooseClass3` (id 16940364545210738611), categoria Classe 3.

Queste sono le **interazioni visibili «Prepara iscrizione Classe N»**. Quando tutte le altre interazioni sono nascoste, questi tre picker, rimasti attivi, mantengono la categoria visibile: le immagini M44 lo confermano in particolare per Classe 3 (resta solo `Prepara iscrizione Classe 3...`).

## Modifica fatta (M45)

- **Non cambiare** tuning categorie e SimData originali M44: il menu annidato è già funzionante su Mac.
- In `src/m39_visibility/mhs39_visibility_ui.py` sono stati aggiunti tre nuovi wrapper che ereditano `_MHS39VisibilityMixin` e `SimPickerInteraction`: `MHS45ChooseClass1/2/3`.
- I soli tre XML delle interazioni picker ora puntano a `mhs39_visibility_ui` e a questi wrapper. Le categorie sono le stesse, ID invariati.
- Gli altri 19 tuning delle interazioni e lo snippet XML Injector sono invariati.
- Le quattro SimData figlie Lot51 sono riprodotte esattamente dai valori originali `0x24..0x27` e `_parent` nella metà alta del riferimento 64-bit. I file risultanti M45 sono stati comparati **direttamente con il package M44 originale** nel container della chat: differiscono solo i 3 tuning XML dei picker. Le 5 categorie e 5 SimData corrispondono esattamente.
- 15 moduli Python 3.7, ZIP validato, aggiunte classi picker al `mhs39_visibility_ui.pyc`.
- Test unitari `tests/test_m45_visibility_complete.py`: `active=false` nasconde tutti e 3; `active=true,2 classes` nasconde la terza; `active=true,3 classes` li mostra tutti; verifica preservazione dei 35 record e di ogni dato non coinvolto.

### Build

Workflow GitHub Actions: https://github.com/iliyanadg/MyHighSchool/actions/runs/41204006607 — **success**.

Artifact: `MHS_M45_MENU_VISIBILITA_2_3_CLASSI_TEST` contiene:
- `MHS_M45_MENU_VISIBILITA_CORRETTA_TEST.package`
- `MHS_M45_MENU_VISIBILITA_CORRETTA_TEST.ts4script`

ZIP completo nella conversazione: `/mnt/data/MHS_M45_MENU_VISIBILITA_2_3_CLASSI_TEST.zip`.

SHA256 package `eb499de91718a35b27b1fd7dc97eb35e925fb14829a11a6a2ebc6440515f7b97`.

## Un'unica verifica sul Mac

1. Chiudere The Sims 4, salvare copia del file JSON esterno `MY_HIGH_SCHOOL_M25_TEST_DATA` (le impostazioni vengono scritte fuori dal salvataggio EA).
2. Togliere **soltanto i due file M44** dalla cartella Mods e inserire **soltanto la coppia M45**. Non toccare le altre mod. Conservare M44 fuori Mods come fallback.
3. Sul salvataggio di prova, se la scuola è disattivata: aprire MY HIGH SCHOOL, attendersi solo `Attiva`, senza sottomenu delle classi e senza Impostazioni.
4. Attivare; se due classi attive: Classe 1/2 e Impostazioni visibili, Classe 3 assente. In Impostazioni `Abilita Classe 3`; attivarla e verificare la comparsa Classe 3; quindi `Disabilita Classe 3` e verificarne la scomparsa immediata riaprendo il menu.
5. Se ci sono errori Better Exceptions o blocco della cassetta: non ripetere clic; uscire senza salvare e ripristinare M44.

**M45 NON è testata in game** al momento della creazione; test offline riusciti. Non è una prova di gestione effettiva della frequenza al liceo EA.

## Cose separate da implementare

- conferme di iscrizione/rimozione con UI nativa, senza console;
- scrittura effettiva dei dati in pausa (picker di sola consultazione si apre già in pausa);
- gestione reale della presenza e delle aule al liceo EA, studenti fissi per salvataggio, staff ed eventi.
