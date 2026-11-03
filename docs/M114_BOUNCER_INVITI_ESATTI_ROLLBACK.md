# M114 — Bouncer scuola per invito originale, 3 novembre 2026

## Problema reale individuato

Alle 10:33 nel report M111 sono presenti 4/16 studenti iscritti,
7 adolescenti non iscritti e zero iscritti nel job della propria
Classe MHS. L'intervento deve controllare sia gli inviti Base/Core
EA sia il Bouncer che sceglie e sostituisce i Sim.

La prima versione M108 di SchoolFilterScope riconosceva uno degli
otto Base iscritti ma NON controllava se proprio quell'ID fosse
stato invitato nell'effettiva creazione EA. Questo poteva ammettere
uno studente iscritto ma non ancora convocato.

## Modifica implementata, senza alterare main o il gioco

- SchoolNativeGuestSession.has_native_student_invitation:
  conferma l'identita esatta di un NPC per situazione, job EA e ID,
  solo durante una chiamata EA con biglietto pending o dopo un
  acknowledge_created con ID situazione positivo. Un invito
  cancel() non autorizza alcun bypass.
- SchoolFilterScope.eligible e is_tracked:
  non basta piu che l'ID figuri in una delle due classi; e
  obbligatorio il ticket originale della stessa situazione e job.
  Le richieste esterne, professionisti, duplicati, animali,
  giocabili, wrong-role o senza invito restano al filtro EA.
- M114SchoolBouncerPair:
  integra due stage M109NativeStage coordinati:
    1. school_filter_scope: patch soltanto __init__ e
       get_additional_filter_terms della BouncerRequest originale;
    2. no_show_guard: patch soltanto clone_for_replace, impedendo
       richieste casuali quando la request della scuola e sotto
       il controllo verificato dello scope.
  Il ripristino dei filtri per request avviene anche in caso di
  installazione parziale.
- compose_m113_late_graph:
  accetta solo le due componenti Bouncer e gli altri tre stage
  esatti richiesti dal controller M113; non crea stage vuoti
  per simulare una prova di capienza o presenze.
- mhs114_native_bouncer_owner.inspect_original_ea_bouncer_owner:
  importa soltanto a runtime la classe EA
  situations.bouncer.bouncer_request.BouncerRequest, con i metodi
  richiesti, Age.TEEN, Species.HUMAN e il SimInfoManager;
  non installa hook. La classe e il percorso SONO fondati nel
  rapporto MAC reale M109: tre proprietari identici.

## Sicurezze e limiti

Tutto quanto sopra e un contratto Python 3.7 **offline**:
l'invocazione vera deve acquisire una provenienza indipendente
di richiesta Bouncer, contesto save/giorno/lotto e i verificati
EA SimInfo e capienza NPC. Non basta chiamare install() con
un dizionario sintetico di flag True.

Non abbiamo identificato in modo affidabile il filtro EA
**vuoto** da usare per il solo ambito scolastico. Quindi M114
non inventa un filter tuning o un GUID: l'applicazione al
gioco resta disabilitata finche questo dato e gli altri gate
non siano stati verificati.

Il no-show guard impedisce clone_for_replace SOLO per le
request originali MHS verificate. Se il ticket e annullato,
lo scope del filtro decade: non va affermato che la sostituzione
casuale sia gia interamente bloccata nel gioco. Il comportamento
di callback EA resta da validare.

## Test automatici

- tests/test_m108_school_filter_scope.py: aggiunti test
  per NPC iscritto ma mai invitato, ticket annullato,
  job sbagliato e ticket di altro NPC;
- tests/test_m114_school_bouncer_pair.py: verifica i due
  stage su una BouncerRequest emulata, eccezioni,
  esclusione delle richieste non scolastiche e rollback;
- tests/test_m114_native_bouncer_owner.py: verifica la forma
  degli import EA e che owner alterati o service mancanti
  risultino bloccati;
- regressioni M108 no_show + M109 descriptor restore.
- CI dedicata:
  https://github.com/iliyanadg/MyHighSchool/actions/workflows/m114-bouncer-exact-invite-safety.yml

Non produce .ts4script installabile e non prova
13 NPC + 3 giocabili a scuola.

## Prossimo passo necessario per gioco reale

Verificare nel codice EA la fonte nativa di un SimFilter
scolastico a termini vuoti, la struttura dei BouncerRequest
per un guest esatto e il comportamento clone_for_replace.
Poi alimentare il M113 stage_graph_factory con sorgenti reali
di prove, unendo native_precreate, Bouncer scope, no_show,
lezioni e post-assegnazione; nessun flag simulato.

Per prima prova attiva usare una COPIA del salvataggio,
un unico controller e rollback di tutti gli originali.
