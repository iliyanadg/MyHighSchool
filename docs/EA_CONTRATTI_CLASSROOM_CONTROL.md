# Correzione lavagna: contratti EA verificati

Questa revisione prosegue dalla build unificata `58db915` e usa i quattro file
EA forniti dalla creatrice. Tutti hanno magic CPython 3.7 `420d0d0a`.
Gli originali e il loro disassemblato restano privati: non fanno parte del
repository né del pacchetto della mod.

## API effettive osservate

- `event_testing/tests.pyc`: `TestSetInstance.__new__` passa il resolver a
  `test.run_tests(resolver, skip_safe_tests, search_for_tooltip)`.
  `CompoundTestList.run_tests` valuta le alternative originali e restituisce
  il risultato effettivo; il nostro filtro non converte mai un rifiuto in True.
- `event_testing/resolver.pyc`: `Resolver.get_participant` restituisce il
  partecipante unico. `InteractionResolver` espone `ParticipantType.Actor`
  e `ParticipantType.Object`; l'attore può essere SimInfo, il target rimane
  l'oggetto lavagna. Un resolver preliminare senza target mantiene il test
  originale: non si elimina un'interazione prima della ricerca dell'oggetto.
- `event_testing/test_base.pyc`: i test EA conservano proprietà di sicurezza,
  argomenti attesi e comportamento di early testing. Non è stato inventato
  un nuovo BaseTest con assunzioni sul caching: il dispatch avviene attraverso
  il contratto già verificato di `run_tests`.
- `interactions/interaction_queue.pyc`: `InteractionQueue.__iter__` legge
  l'interazione corrente e tutti i bucket, evitando il duplicato del corrente.
  `running` può essere l'interazione di transizione. La struttura `_queue`
  usata dal controllo precedente non è l'API effettiva. Non vengono chiamati
  `get_head`, `peek_head`, cancellazioni o rimozioni dalla coda.

È stata inoltre eseguita una prova privata dei metodi EA puri estratti,
con oggetti inerti: dispatch TestSetInstance/CompoundTestList, risoluzione
partecipanti, iteratore e getter `running`. La prova verifica rifiuto della
lavagna sbagliata, conservazione dell'identità dei risultati originali fuori
ambito e assenza di modifiche alla coda. Non equivale a una sessione nel gioco.

## Cosa cambia

`mhs_scoped_classroom` legge la classe dalla fotografia del registro della
giornata e controlla gli stati EA della lavagna. Un iscritto Classe 2 non può
superare il filtro su una lavagna Classe 1, anche se un ruolo o un tratto
transitorio lo indirizza lì. Non servono nomi o Sim ID fissi.

Il filtro viene applicato all'interazione NPC originale **297779**, al picker
EA/Zerbu e alle otto materie già gestite dalla M145. I test originali NPC,
giorno/materia e gli altri requisiti restano in esecuzione. La classe corretta
non basta a far superare un test EA fallito.

Per non iscritti, zone diverse dal liceo o gestione disattivata vengono
eseguite le liste originali, conservandone il risultato e i flag. Questo
mantiene il comportamento originale del ramo Elementary anziché modificarlo
globalmente. Il rollback controlla l'identità degli oggetti e non sovrascrive
modifiche successive di terze parti.

`mhs_queue_readback` legge tutti i bucket, con limite esplicito e rifiuto delle
letture incomplete. Riconosce anche il `super_interaction` di un mixer: usare
il telefono durante una lezione non significa che il Sim sia senza lezione.
Le richieste successive non interrompono quel genitore attivo.
Lo stesso controllo vale nell'invio iniziale di `Class_Start`, non soltanto
nei tentativi successivi: anche lì vengono rispettate code, lezioni e azioni
protette. Se la nuova API di lettura non è disponibile, non viene inviato
un tentativo alla cieca.

Il diario registra ora, per tutti i 16 iscritti, job EA, tratto Class1,
azioni realmente in coda e azione principale del mixer. Il campionamento
completo resta ogni 15 minuti simulati. I nuovi rapporti hanno prefisso
`MHS_CLASSROOM_CONTROL_`, preservando i vecchi rapporti M148.

È stato corretto anche il riconoscimento del conteggio nativo Base: il valore
tre apparteneva alla famiglia di prova. Gli XML verificati dei due schedule
partono da sei posti, ridotti dai partecipanti della famiglia; i risultati
nativi riconosciuti tra zero e sei sono ora distinti dalla quota Base ricavata
dal registro. Conteggi di forma diversa o sconosciuta restano inalterati.

## Limiti del primo collaudo

Il rapporto M148 precedente prova che tutti i 16 erano già sul lotto alle
08:16 e che un NPC Classe 2 puntava inizialmente alla lavagna Classe 1.
Non prova quale evento EA abbia causato quel target transitorio: ad esempio
un ruolo precedente, un tratto aggiornato o un'azione già preparata.
La correzione rende comunque vincolante il registro nel test del target.

Restano da misurare nel gioco: scelta e routing effettivi, otto seduti per
classe alle 10 e 14, completamento naturale, seconda giornata senza riarmo
manuale, pranzo, punizioni, esami ed eventi. Le prove di fallback con i
contratti EA/Zerbu non certificano l'intera compatibilità delle mod installate
né Windows. Non sono stati forzati posti, orari, obiettivi o teletrasporti.
