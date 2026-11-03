# M123 — Prima correzione sperimentale delle liste di lezione, due classi da 8

## Risultato reale del test M122, 3 novembre 2026

Nel lotto scolastico, alle 10:33, l'utente ha osservato:
- **Classe 1** con prof. **Giuliano Papanice**: sei adolescenti
  (Lady Amaraki Darong, Rosario Lanzafame, Rohan Elder Barry,
  Sofia Ogliari, Delmira Gomez, Sandro Paoletti);
- **Classe 2** con prof. **Angelo Morlind**: otto adolescenti
  (Ollie Mark, Baby Ariel, Greta Lorent, Zafira Kahya Putri,
  Lady Sofia Brantes, Freya Loden, Nayon Specter, Kevin Puri);
- **Raul Chopra e Lutz Lopez** presenti al liceo ma impegnati
  al computer invece di partecipare alla lezione.
  Questi nomi sono osservazioni fisiche, NON la fonte per
  decidere l'iscrizione alle classi.

La M122 ha letto `giocabili_istanziati=3/3`,
`iscritti_istanziati=16/16`, `EA_classe1=3/8`,
`EA_classe2=8/8`, `mancanti_C1=8`, `mancanti_C2=5`,
`classe_sbagliata=8`, `extra_nelle_lezioni=0`.
Il disallineamento deriva dai ruoli delle situazioni EA
(che non rappresentano necessariamente l'aula fisica).

## Implementazione M123

La nuova beta utilizza tutto il controller della M122 e della
M121: **8 Base + 5 Core manuali**, senza sostituirli casualmente.

Nuovo `mhs123_lesson_guest_projection.py`: quando il metodo
originale `SituationManager.create_situation` riceve per la
prima volta una delle situazioni riconosciute di lezione:
- Classe 1 `304565` o `304703` (due percorsi alternativi),
  job studente `277919`;
- Classe 2 `304567`, job studente `280777`;

il controller prepara una nuova copia della guest list con
**esattamente gli otto ID già iscritti** alla classe corrispondente
nel salvataggio MHS, compresi eventuali Sim giocabili.
Conserva gli ospiti docenti e tutto il personale conosciuto
senza rimuoverli o cambiarne l'identità.

Se il job della lista non è riconosciuto, gli otto iscritti
non sono unici, il docente coincide con uno studente o
l'API originale è incompatibile, lascia la creazione EA invariata.
Non crea altri NPC o cambia i tratti caratteriali.

Viene preparata una sola lista per ogni classe MHS nel test.
Il filtro EA `BLANK_FILTER` è richiesto soltanto per
BouncerRequest con un SimID e job originali corrispondenti.

Il comando `mhs123.status` conserva i conteggi M121
(`EA_base_present=8/8`, `EA_core_present=5/5` come obiettivo)
e aggiunge:
- `lezioni_proiettate` (0, 1, 2);
- `lezione_job=C1:x/8|C2:y/8`, lettura dei job della situazione
  originale effettivamente creata;
- `lesson_filter`, `refused_lessons`.

`mhs123.classi` continua a confrontare tutti i 16 iscritti
con i job delle situazioni EA delle lezioni, rilevando anche
non iscritti. `mhs123.stop` ripristina i metodi originali.

## LIMITI IMPORTANTI — beta NON ancora provata nel gioco

L'originale EA `WeeklyScheduleSituationData.try_start`
seleziona i Sim attraverso test e limiti del job **prima**
di creare la situazione. La Classe 1 ha due route
`WithTrait/NoTrait` e un limite originale intorno a 6
per la relativa fase. Avere otto inviti nella guest list
NON prova che il Bouncer li ammetta tutti o li faccia
sedere. Inoltre, il secondo percorso Class1 originale
può ancora eseguire una situazione separata: va verificato
se crea duplicati, prima di incorporare questo schema
nel controller definitivo.

Non è stato modificato il codice EA delle capacità
di lezione, né l'associazione delle lavagne ai professori.
Per questo il test viene fatto esclusivamente su una
**copia** del salvataggio, e l'esito è valido soltanto
dopo aver letto le situazioni EA durante la lezione.

## Come verificare in gioco, una giornata

1. Chiudere The Sims 4, usare COPIA del salvataggio.
2. Rimuovere `MHS_M122_TREDICI_NPC_MAC_BETA.ts4script`,
   M121, M120 e altre beta EA. Conservare il menu MHS stabile.
3. Scaricare l'artefatto
   `MHS_M123_TWO_CLASSROOM_MAC_EXPERIMENTAL`:
   https://github.com/iliyanadg/MyHighSchool/actions/runs/41717570145
   Inserire in Mods **solo**
   `MHS_M123_DUE_AULE_MAC_BETA.ts4script`.
4. Da casa prima di scuola: `mhs123.arm`.
5. Dopo l'arrivo al liceo, alle 10:30 durante la prima lezione,
   prima `mhs123.status`, poi `mhs123.classi`.
   Inviare gli screenshot delle due risposte. Evitare
   ulteriori prove se il gioco genera errori.
6. Terminare `mhs123.stop`, uscire dal gioco.
   Se il ripristino segnala conflitto, riavviare il gioco.

Test automatici Python 3.7: **28 test superati**.
https://github.com/iliyanadg/MyHighSchool/actions/runs/41717570145

Il `main` stabile non è stato modificato.
