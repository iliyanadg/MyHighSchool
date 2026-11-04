# Six uploaded EA school jobs: SimData, not SituationJob tuning

The six files supplied on 2026-11-01 are valid XML **SimData** exports,
resource type `0x545AC67A`, group `0x000785C3`.
Each root element is `<SimData>`, with only an empty
`recommended_objects` list and its schema. They are not damaged
and the six job IDs and names are correct; they simply do **not** expose
EA `sim_filter` or `sim_auto_invite`.

| EA job ID | Role | Received file type |
| --- | --- | --- |
| 277894 | ordinary Base Student | SimData |
| 278965 | CheerTeam | SimData |
| 278966 | ChessTeam | SimData |
| 278967 | FootballTeam | SimData |
| 278968 | ComputerTeam | SimData |
| 303765 | MeanSim | SimData |

**Needed next:** the same six resource instances but original
`SituationJob` **Tuning** XML, resource type `0x9C07855F`
(group normally `0x00000035`), with a root `<I ... s="..." ...>`.
Export from Sims 4 Studio > Tools > Extract Tuning by job name or ID.
Sims 4 Studio may export both Tuning and associated SimData; send only
the six `9C07855F!` XMLs, or send the original export folder/ZIP
containing both and let us separate them.

Run `python -m tooling.verify_ea_school_jobs FOLDER` to ensure the
correct set is present. This checker rejects SimData and does not
claim that valid tuning alone guarantees 16/16 attendance.

**Compatibility:** leave M85 installed, do not install More Students
or either partially integrated capacity beta into the main save.
No additional EA job override, random-core interception, or claim of
complete attendance is authorized by these SimData exports.
