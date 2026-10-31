# Passo 46 — Esportazioni reali Lot51: scoperto il formato Parent SimData (31 ottobre 2026)

## File ricevuti dalla creatrice
Sono stati aperti e decodificati **tutti e cinque i .package**. Il loro contenuto non corrisponde a cinque categorie: tre esportazioni sono interazioni.

| File | Risorse esportate | Utilizzabile |
| --- | --- | --- |
| creator_name-tuning-export-1793449868.package | `Iliyana:MHS_MainMenu` PieMenuCategory + SimData | sì, 2/2 |
| creator_name-tuning-export-1793449956.package | `Iliyana_MHS_M0_ChooseClass1` SuperInteraction | no, non una categoria |
| creator_name-tuning-export-1793449985.package | `Iliyana_MHS_M0_ChooseClass2` SuperInteraction | no, non una categoria |
| creator_name-tuning-export-1793450000.package | `Iliyana:MHS28_ChooseClass3` SuperInteraction | no, non una categoria |
| creator_name-tuning-export-1793450021.package | `Iliyana:MHS_Settings` PieMenuCategory + SimData, e `Iliyana:MHS28_ChooseClass3` SuperInteraction | sì, Settings 2/2; ignora SuperInteraction |

## Scoperta concreta — diverso layout del parent rispetto a M43

Nel `MHS_M43_MENU_GERARCHIA_E_FIX_TEST.package`, la SimData figlia `Iliyana:MHS_Settings` ha Parent=1942018511 nell'**emissione manuale dei byte 0x5c..0x63**:

```
SimData M43, offsets 0x5C..0x63:
CF D9 C0 73 00 00 00 00    # little endian 0x0000000073C0D9CF
```

Invece Lot51 TDesc Builder, dopo aver riletto e rigenerato l'esatta categoria Settings XML con Parent=1942018511, produce:

```
SimData Lot51, offsets 0x5C..0x63:
00 00 00 00 CF D9 C0 73    # little endian 0x73C0D9CF00000000
```

Il campo a offset 0x24..0x27 cambia da `03 E2 27 80` (preservato dal modello copiato per tutte le categorie M43) a `9E 7B 59 1E` nel file Settings TDesc. Root MainMenu è invece **byte-per-byte identico** fra il pacchetto M43 e l'export Lot51, sia XML semanticamente che nella SimData binaria.

Queste prove mostrano una differenza deterministica nel formato del campo di riferimento e dell'header di SimData. L'ipotesi *molto forte* è che i quattro child siano orfani visivamente perché M43 ha immesso manualmente il numero del Parent nella metà sbagliata dell'8-byte TableSetReference. **Non ancora verificato in game**: non dichiarare già risolto il menu.

Fonte consultata: https://thesims4moddersreference.org/tutorials/creating-a-pie-menu/ documenta che Parent e tutti i campi richiedono risorse SimData aggiornate e consiglia la generazione automatica via Lot51.

## Prossima azione senza altri test in The Sims 4

La creatrice deve esportare solo le **tre categorie che mancano**, non le SuperInteraction `ChooseClass`, dal Workspace Lot51:

- `Iliyana:MHS_Class_1_` (nota il prefisso `Iliyana:` e underscore finale; **NON** `Iliyana_MHS_M0_ChooseClass1`)
- `Iliyana:MHS_Class_2_`
- `Iliyana:MHS_Class_3_`

Cliccare ciascuna voce di categoria, File > Download Package, includere **una risorsa PieMenuCategory e la relativa SimData** per ciascuna. Tre package separati vanno benissimo; eventualmente un unico export con tre schede selezionate.

Non installare i package esportati, perché sono risorse isolate di menu e non la mod completa.

Il tool `tooling/build_m44_tdesc_merge.py` è stato aggiornato per unire export multipli, controllare ciascuna categoria, scartare eventuali interazioni duplicate e verificare il formato Parent in bit ALTI (<< 32). M44 userà la SimData generata da Lot51 per tutte e 5 le categorie, preservando le interazioni, i testi, il registro e i 15 moduli Python della M43. Se mancano le cinque coppie, blocca la build. La prima prova Mac sarà quindi di tutto l'albero in una sola sessione.

**Non fare nuove versioni per una singola classe, né alterare il salvataggio principale.**
