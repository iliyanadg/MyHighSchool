# Definition of Done — MY HIGH SCHOOL general-purpose class routing

**M138 is an experimental compatibility beta, not production-ready.** It adjusts a specific loaded Zerbu EA test hierarchy; it is armed manually per test save and relies on the existing Class1Student trait as a runtime discriminator. It does NOT provide universal save-independent, automatically installed MHS class routing.

## Product-wide requirements (apply for any player and eligible teen, not test character IDs)
- Dynamic MHS enrollment is the authoritative class assignment (1/2 initially; support all enabled classes according to the product plan). No hard-coded Sandro, Rosario or Sofia IDs.
- Enrolled teenage playable / NPC must have one correct class and one correct class board; clicking the other board must not offer school class participation. Class changes apply according to the existing next-school-day rule.
- First-time activation should configure and persist game behavior; no daily console commands. Automatic entry by 10:00 for eight registered students in each enabled class, with teacher, physical seating and no unregistered extras must be *measured in the actual game*. A correct EA situation membership or accepted interaction alone is insufficient.
- Preserve existing 13 NPC EA roles, staff, and EA school calendar. Never reassign standard NPC students to patch a playable-only issue.
- Compatibility when Zerbu GTS5 is absent or present: assess the original EA test hierarchy and apply a version-specific, safe compatibility adapter when supported. If unsupported, fail visibly without breaking vanilla. Do not override Zerbu Elementary situation tests globally.
- Enforce rules on actual MHS enrollment and save identity, including same Sim enrolling into a different class across saves. Trait sync alone is an implementation detail and not a substitute for authoritative saved registration.
- Test class and student transfers, multiple playables, NPC-only families, custom high schools/CC blackboards (where supported), reload, zoning, graduation, and temporary disable/restore.
- Mac and Windows platform paths and Python compatibility.
- Keep `main` stable until multiple game sessions prove intended behavior. No test-only beta is a final release.

## Current evidence
- M131 automatic Class1 trait sync succeeded live: 9 corrected, 16 enrolled, 0 wrong.
- M134 per-player native EA jobs confirmed Class1 304565/277919 and Class2 304567/280777.
- M136 original live testSet was replaced by Zerbu testSet 279071, `Zerbu_GTS5_WhiteboardStudentTestSnippet`: asymmetric NPC/player whiteboard rules and Elementary job alternative.
- M137's first `compat` at 09:40: `automatico=False stato=None`; its patch was not active; Sandro and Sofia saw both boards, Rosario only Class1.
- M138 changes the per-session experimental patch activation to happen at `arm` and tests a Class1/2 trait-based exclusive board predicate, but its real game effect remains unverified. It must not be presented as universal / automatic release.

## Next engineering actions
1. Prove scoped adapter against actual EA and Zerbu test semantics in-game; ensure it does not activate for unrelated school types or situations.
2. Replace test-save-only manual-arm logic with persistent, user-controlled activation and robust lifecycle install/restore.
3. Change class UI filter and action execution to authoritative enrollment and correct active school session (not just trait).
4. Handle selectable teenage Sims' original EA career/situation job and class participation automatically, without repeated push commands or double queueing.
5. Observe 8/8 physical seated at 10:00 with multiple class configurations across different saves and platforms.
