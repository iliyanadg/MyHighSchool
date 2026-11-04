# M131 — First practical native player interaction pilot (Mac)

## What was implemented
- On the *first* original EA school preparation situation create call (observed at 09:30 in M127), run a strict 16-Sim **MHS roster -> EA Class1 trait** alignment. The routine runs only once per activated school session; saves the result in controller and can be read by `mhs131.sync`. On failure, the original EA situation is not blocked and a failure reason is recorded.
- `mhs131.giocabili` is an **explicit** test of the EA player-specific school interaction `super_HighSchool_Active_Whiteboard_Class_Start`, tuning 276774. This is **not** the NPC `AttendClass_NPC` affordance.
- Classroom target is selected solely from the registered MHS class and from two live whiteboards whose EA true states are unambiguous (Class1 true state 276075 / Class2 true state 276077). If an EA tuning/object manager method is unavailable, classes are not distinguishable, or multiple boards are classified the same way, command refuses and does not queue any interaction.
- Original 13 NPC admissions, 16 lesson guest-list enrollment, EA lesson schedule and 8x2 MHS registry remain unchanged.
- No teleport, no interaction cancellation. Existing player school workbooks, player class start or toilet actions are not interrupted.

## Important limitations
- The in-game native `InteractionContext` constructor and `state_value_active` are validated only structurally offline, **not verified on user's Mac/EA build**. The first live test may be rejected, and the command will print the actual reason; do not claim finished behavior.
- No automatic daily playable entry yet: `mhs131.giocabili` is opt-in to safely verify the EA route. If successful and role buffs permit early use, a later revision may trigger this in the native school preparation before 10:00.
- Native EA may reject `Whiteboard_Class_Start` before its player role/buff becomes active. No bypasses or arbitrary force.
- A successful queue only proves EA accepted the action, not 8/8 students physically seated at the right desks by 10:00.

## Live test
1. Use only a backup/test save, install M131 instead of M130, `mhs131.arm` while home.
2. Enter original EA school, around 09:35 execute `mhs131.sync` then `mhs131.verifica`. Ideally sync succeeded and `tratti_errati=0` without manual `allinea`; if not, capture exact output, no guess.
3. At 09:40 (or once EA player school role active), run `mhs131.giocabili` **once** and capture per-Sim command statuses; do not repeat rapidly or spam queues.
4. Visually count 8+8 and log the time; at 10:05 `mhs131.posti` provides positions. Report statuses plus actual visual results. Stop on repeated exceptions.
5. This is a pilot, not a production MHS release. main branch untouched.

## Grounded failure addressed
M130: original EA 09:30 prep, 09:55 near registered boards 4, other board 1, 11 standing; 10:05 correct proximity 7, wrong zone 2, 7 standing. Visually 8 Class1, 6 Class2 and Rosario Lanzafame / Sandro Paoletti missing. The prior assistant must not assume both played Sim IDs are registered in Class2 without a roster lookup.
