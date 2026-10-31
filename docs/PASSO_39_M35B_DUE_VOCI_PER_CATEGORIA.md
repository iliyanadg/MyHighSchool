# Passo 39 — risultati reali M35 + M35B doppia voce

31 ottobre 2026, 03:17 (Mac, The Sims 4, save test slot 11).

## M35 smoke verificata
La giocatrice ha fornito cinque screenshot. Sono risultati importanti:
1. La **cassetta postale si apre** senza l'eccezione `invalid category ID` della M32.
2. `MY HIGH SCHOOL (M35 SMOKE TEST)` è visibile e le restanti operazioni del menu si aprono su più pagine.
3. La voce `Consulta iscritti - Classe 1` è stata **spostata fuori da MY HIGH SCHOOL**, come previsto dal tuning M35, ma compare direttamente nel menu radice anziché sotto `Classe 1 - M35 PROVA`.
4. Cliccandola, la finestra fotografica **Consulta iscritti - Classe 1** si apre e mostra soltanto Amarachi Darong e Baby Ariel; il registro test 11 risulta leggibile.
5. Non abbiamo verificato alcun commit in questo test; la mod viene testata come sola lettura.

Questo dimostra che **un'unica nuova categoria con una sola interazione non ha creato un sottomenu grafico**. Non è ancora chiaro se l'Olympus UI appiattisca categorie con una sola azione oppure se non venga caricata/riconosciuta la nuova PieMenuCategory. Non affermare di aver già risolto il problema.

## Ipotesi e nuova build minima M35B
- La SimData originale clonata da M34 ha `_collapsible=1`, quindi l'ipotesi “manca _collapsible” NON spiega da sola questo comportamento.
- La M35 conteneva **una sola voce** associata alla categoria aggiuntiva. Una spiegazione possibile è che il gioco mostri direttamente una categoria con un unico comando.
- La M35B è identica alla M35 ma associa alla stessa unica categoria indipendente `Classe 1 - M35 PROVA` **due** operazioni preesistenti, inalterate nella loro logica:
  - `Consulta iscritti - Classe 1` (sola lettura)
  - `Rimuovi studenti - Classe 1` (apre il picker, non scrive fino al `mhs27.removecommit conferma`).
- Solo il riferimento di categoria del tuning di `Rimuovi studenti - Classe 1` cambia. Non cambia Python, stato degli studenti, altri tuning, impostazioni o `_parent`.
- È una prova di diagnosi della UI e **NON** il menu finale annidato.

## Sicurezza e risultato atteso
La M34 è la versione di recupero testata.
- Chiudere The Sims 4 e rimuovere sia M35 sia M34 dalla cartella Mods; usare SOLO la coppia M35B e conservarle entrambe fuori da Mods. Fare backup della directory JSON `MY_HIGH_SCHOOL_M25_TEST_DATA`.
- Riaprire il save di prova. Cliccare sulla cassetta postale **senza confermare azioni né iscrizioni**.
- Se la categoria compare `Classe 1 - M35 PROVA`, aprirla e confermare che contiene Consulta iscritti + Rimuovi studenti. Non confermare rimozioni.
- Se la voce non compare ma le due azioni restano separate, **non** concludere che due o tre categorie annidate funzioneranno: è ancora irrisolta la registrazione.
- Se la cassetta si blocca/UI Exception, chiudere senza salvare, rimuovere M35B, ripristinare M34 e inviare lo screenshot del report.

## Stato richieste finali (non ancora implementate)
- Menu `MY HIGH SCHOOL → Attiva/Disattiva → Classe 1 / Classe 2 / Classe 3 (opzionale) → azioni`
- Attivazione e scelta 2/3 classi devono nascondere/mostrare dinamicamente i comandi, non solo impedire scritture.
- Ogni azione deve funzionare in pausa, senza dover far partire il tempo del Sim.
- Confermare direttamente nella UI del gioco e registrare i dati senza usare la console.
- Le aule e presenze liceo EA ancora da integrare.

La M35B non può essere chiamata completa o compatibile finché non testata **nel client reale Mac**.
