# M107 — Indagine decisiva, prima di ulteriori beta in gioco

Data: 2 novembre 2026. **Nessun codice EA modificato, nessuna nuova beta autorizzata.**

## Il punto debole scoperto dai test M105–M106

I test offline verdi non simulano la scelta reale dei Sim, l'occupazione
dei SituationJob né la classe EA. Nel salvataggio della giocatrice:

- 16 iscritti fissi, due gruppi di 8, tre teen giocabili.
- 13 NPC iscritti, 12/13 hanno superato il SimFilter Base EA.
- Nessuno dei 13 ha superato il SimFilter EA per MeanSim.
- M106 si è fermata: `no 5 Core + 8 EA-eligible Base partition for the fixed 16`.
- Non sostituire nessun iscritto, non cambiare le personalità, non assegnare
  arbitrariamente ruoli diversi.

## Fonti pubbliche che modificano l'ipotesi di sviluppo

1. SonozakiSisters, *High School Management 2.2 and Add-Ons*,
   post pubblicato 17 marzo 2026, aggiornato 10 aprile 2026:
   https://www.patreon.com/posts/153195289
   - il tratto nascosto `trait_HighSchool_Active_Class1Student` può alterare
     priorità e distribuzione (a prescindere dal nome, non garantisce l'aula);
   - esistono filtri di regione, particolarmente Moonwood Mill,
     Strangerville e Henford-on-Bagley, oltre a vincoli per household
     nascosti, relazioni nascoste e certi NPC di servizio;
   - MeanSim e membri delle squadre hanno condizioni diverse dagli altri;
   - la mod usa metodi di selezione speciali e segnala che nemmeno con
     More Students il risultato è sempre garantito.
2. SonozakiSisters, *Choose High School Classmates 2.0*:
   https://www.patreon.com/posts/121367985
   - usa regole di blacklist per i ruoli di liceo e i relativi SimFilter;
   - non prova 16 identità fisse senza modifiche al calendario originale.
3. Konanhurry, *Choose Your High School Classmates*:
   https://www.curseforge.com/sims4/mods/choose-your-high-school-classmates
   - l'idoneità a squadre/club e il salvataggio del nucleo scelto possono
     richiedere passaggi ulteriori rispetto alla semplice scelta del ruolo.
4. Motherlode, decompilatore Python 3.7 EA con verifica bytecode:
   https://github.com/BigBadBleuCheese/Motherlode
   - supporta macOS e può generare script leggibili e report di verifica
     direttamente dalla copia locale di The Sims 4.

L'articolo di Sonozaki non dimostra che un certo vincolo sia presente su
tutti i Sim del salvataggio; sono piste da verificare sul codice corrente.

## Artefatti di cui abbiamo già i dati

L'utente aveva fornito `weekly_schedule_zone_director.py`,
ritrovato nella propria Library ChatGPT in data 30 ottobre 2026.
Nel repository ci sono tunings originali dell'1 novembre:
`assets/ea_2026_11_01/277657.xml`, `279958.xml`,
`298052.xml`, `277733.xml` e altri.

**Non richiedere all'utente un'altra copia di
`weekly_schedule_zone_director.py`.**

## File sorgente mancanti, in ordine di valore

Da una decompilazione verificata *della sua installazione attuale*:
- `situations/bouncer/bouncer.py`
- `situations/bouncer/bouncer_request.py`
- `filters/sim_filter_service.py`
- `situations/base_situation.py`
- `situations/situation_guest_list.py`, se presente

Sono sufficienti pochi file mirati. Non è necessario condividere
salvataggi privati o l'intera installazione EA.

Se disponibili localmente, possiamo anche ispezionare soltanto i tunings
di Sonozaki High School Management 2.2.1 (nessuna installazione) per
capire quali filtri effettivamente sovrascrive e quali marker usa.

## Tre interrogativi che debbono avere una risposta tecnica PRIMA del prossimo test

1. **Ammissione:** esiste un punto sicuro in cui un gruppo esplicito di
   SimID iscritti viene invitato a un *vero* SituationJob EA, senza
   scegliere NPC diversi in fallback e senza cambiare tratti caratteriali?
   Verificare il Bouncer e i vincoli della situation guest list.
2. **Capienza:** come si realizzano esattamente 8 richieste Base quando
   il calendario originale ne prevede 6, senza crearne 16 o generare
   comparse aggiuntive?
3. **Lezioni:** quale parte di WeeklyScheduleSituationSet, lezione e
   RoleState assegna 8 al vero job dell'aula 1 e 8 all'aula 2? La sola
   convocazione sul lotto non equivale al ruolo di studente in lezione.

## Soglia di decisione e criterio di stop

Prima della prossima beta serve prova di codice e test **almeno** per
(1) original Bouncer acceptance, (2) exactly 13 NPC IDs and no
fallbacks, (3) schedule 8 Base, (4) mapping delle lezioni 8+8.

Se i quattro requisiti non sono realizzabili con gli hook nativi
verificati, dichiarare l'architettura EA-first inadeguata e valutare
un controller di situazioni alternativo, senza lanciare un'altra serie
di beta per singolo NPC.

Un test Python o GitHub Actions verde non soddisfa i criteri di
presenza nel gioco; servirebbe **un solo** test integrato su copia
del salvataggio, dopo il superamento di questi controlli.
