# Passo 64 — M55b: errore hook Mac e confronto roster / presenze

## Verifica reale nel gioco — 31 ottobre 2026

La giocatrice ha installato M55 (compilazione Python 3.7 superata) e ha aperto il salvataggio di prova. Il nuovo sottomenu **M55 - Consulta presenze automatiche** compare e si apre; conferma che il package e l'interazione UI della M55 sono caricati correttamente. Tuttavia, nello screenshot la finestra mostra esattamente:

```
Automazione M55: installato
HOOK_ERRORE: TypeError
Giornata liceale: non ancora rilevata
```

**Causa individuata nei sorgenti:** `src/m55_attendance/mhs55_attendance_auto.py` chiamava `alarms.add_alarm(zone, interval, _tick, repeating=True, repeat_interval=interval)`. L'API `alarms.add_alarm` di EA non accetta il keyword `repeat_interval`. La callback dell'hook veniva invocata, ma `_start_zone` terminava con TypeError e l'allarme non partiva; non era un errore nelle iscrizioni, nei Sims scelti o negli oggetti sul lotto.

**Correzione M55b**: `alarms.add_alarm(zone, interval, _tick, repeating=True)`. Gestisce `None` come allarme non creato, espone nel messaggio di stato sia il tipo sia il testo di eventuali futuri errori. Inserito un test AST che esegue il vero `_start_zone` contro uno stub con signature EA (priva di `repeat_interval`), impedendo regressioni. La correzione mantiene la convocazione automatica **di tutto il registro**, non reintroduce selezione singola o convocazione manuale. Restano invariati capacità 8 × 2/3 classi, filtro persone, staff e menu.

## Dati rilevati da utente sul lotto (utile per confronti successivi)

### Iscritti nel registro Classi 1 e 2
- **Classe 1 (8):** Baby Ariel, Jeb Harris, Kiyoshi Ito, Luna Villareal, Nyon Specter, Ollie Mark, Rahul Chopra, Yuki Behr.
- **Classe 2 (8):** Amarachi Darong, Ash Harjo, Rohan Elderberry, Savannah Prezzo, Sofia Abrantes, Wolfgang Munch, Zelmira Gomes, Zhafira Cahyaputri.
- I Sims giocabili Sandro, Giorgio, Sofia **non sono stati iscritti manualmente al registro**, per scelta della creatrice: intende accompagnarli attivamente a scuola. Questi Sims restano gestiti da EA come studenti giocabili.

### NPC e staff reali rilevati al liceo, prima della correzione
- **Aula EA 1 docente:** Giuliano Papanice; **alunni:** Duane Talle, Sofia Bjergsen, Sofia Ogliari, Rosario Lanzafame, Giorgio Paoletti, Wolfgang Munch.
- **Aula EA 2 docente:** Anjelo Morlind; **alunni:** Noah Kane, Morgan Fyres, Nyon Specter, Molly Prescott, Savannah Prezzo.
- **Preside EA:** Mei Flex.
- **Custode EA:** Tai Lum.
- **Mensa EA:** Ava Harjo.

Nota: molti dei partecipanti sono NPC spontanei di EA e non membri del registro MHS. La loro presenza non è ancora impedita dal controller M55. Solo Nyon Specter, Savannah Prezzo e Wolfgang Munch corrispondono ai 16 iscritti MHS visti sui due roster, **ma questo non dimostra che M55 li abbia convocati**: l'automa non era avviato a causa del TypeError.

### Staff configurato nel nostro registro
- **Preside:** Kai Aether, diverso dalla preside reale Mei Flex.
- **Prof Classe 1:** Geoffrey Landgraab, diverso da Giuliano Papanice.
- **Prof Classe 2:** Akira Kibo, diverso da Anjelo Morlind.
- **Prof Classe 3:** non assegnato.
- **Mensa (3/3):** Agnes Crumplebottom, Alex Moyer, Alessia Sanna, diversi da Ava Harjo.
- **Bidelli (2/2):** Bjorn Bjergsen, Gianluca Ferraro, diversi da Tai Lum.

La M55b sistema solo **l'avvio automatico**; l'assegnazione del personale scelto ai ruoli EA, la soppressione dei personaggi casuali, la posizione di ciascuna classe e la terza aula reale restano funzionalità successive.

## Prossimo test Mac della M55b

1. **Non sovrascrivere il salvataggio principale.** Chiudere il gioco, mettere da parte la coppia M55 precedente, installare entrambi i file della M55b provenienti da una stessa GitHub Actions run riuscita.
2. Tornare al salvataggio di prova, seguire i propri Sims al liceo durante la normale giornata e lasciare avanzare il tempo (la UI mostra `IN PAUSA` nello screenshot). Il nuovo hook dovrebbe mostrare `CONTROLLO_AVVIATO` se l'allarme EA parte.
3. A liceo EA in funzione: aprire `MY HIGH SCHOOL → Classe 1 → M55 - Consulta presenze automatiche`. Copiare tutto il testo. Se compare un altro errore ora includerà dettagli utili, non solo `TypeError`.
4. Contare gli alunni realmente **visibili**, distinguendo alunni registrati da NPC EA. Richieste inviate ≠ arrivi confermati, e una terza aula EA non è ancora implementata.
5. Se crash o freeze, uscire senza salvare il test e ripristinare M54.

**Invariante:** non toccare le iscrizioni o l'assegnazione staff funzionanti nei JSON. Le modifiche devono essere solo runtime e build M55b.
