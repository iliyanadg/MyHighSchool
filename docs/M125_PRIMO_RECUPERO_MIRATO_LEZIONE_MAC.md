# M125 — Primo recupero mirato durante la lezione (Mac)

## Baseline reale
M123 e M124 hanno confermato nel gioco 8/8 studenti nei job
della Classe 1 e 8/8 della Classe 2, 13/13 Base/Core, 0 extra
nei job EA; la verifica visiva ha osservato solo 11 studenti
seduti in aula (5 Aula 1, 6 Aula 2), con 5 fuori.
Il file M124 mostrava un NPC Classe 1 con interazione reale
`sims4.tuning.instances.mirror_ResearchDebateSkill_Practice`
malgrado il suo job EA di lezione corretto; il resto
mostrava interazioni scolastiche, non prova della seduta.

## Intervento esatto
Il pacchetto conserva M124 completo (ammissione Base/Core,
inviti due lezioni, misure EA). In più contiene:

- `mhs125.candidati`: esamina i 16 iscritti, SENZA cambiare Sim,
  e restituisce ID dei soli NPC con attività allo specchio
  `mirror_ResearchDebateSkill_Practice` e job EA di lezione
  della classe giusta;
- `mhs125.rientro`: SOLO SU COMANDO MANUALE, annulla la
  singola interazione tramite l'API EA originale
  `interaction.cancel(FinishingType.SITUATIONS, reason)`.
  Un solo tentativo per Sim per sessione; nessun ciclo,
  nessun teletrasporto, nessuna iniezione di affordance;
- `mhs125.classi`, `mhs125.azioni`, `mhs125.status`:
  verificano di nuovo gli effetti senza affermare
  che il Sim sia seduto se non osservato.

NON tocca Sims giocabili, toilette, mensa, conversazioni,
o le attività legate alla lezione.
NON applica la modifica automaticamente; devi digitare
esplicitamente il comando. Se non c'è l'attività precisa,
`candidati=0` e `rientro` non interviene.

I limiti sono reali: annullare un'interazione concorrente non
garantisce che EA generi subito un'autonoma azione di lezione.

## Test (solo COPIA del save)

1. Chiudere il gioco e rimuovere M124 e tutte le beta EA
   precedenti da Mods. Conservare la mod stabile MHS e
   installare solo
   `MHS_M125_RECUPERO_AULA_MAC_BETA.ts4script`.
2. Da casa prima della scuola: `mhs125.arm`.
3. Durante la lezione al liceo, con il gioco in pausa,
   `mhs125.classi` e `mhs125.candidati`.
4. **Soltanto se candidati > 0**, digitare `mhs125.rientro`.
   Questo è un intervento reale sull'azione del Sim:
   eseguirlo solo sul salvataggio di prova.
5. Lasciare procedere 2-3 minuti del gioco; poi
   `mhs125.azioni` e verifica visiva in aula per
   gli studenti interessati.
6. Fine test: `mhs125.stop` e chiusura gioco.

## Compilazione e convalida
Python 3.7, **40 test offline superati**, controllo esplicito
degli undici moduli e stringhe dei comandi M125 in .pyc.
Workflow artefatto:
https://github.com/iliyanadg/MyHighSchool/actions/runs/41727265210

Questi test NON convalidano l'effetto nel gioco; solo la
sessione Mac potrà stabilire se si recupera davvero la lezione.
Non modificare `main`.
