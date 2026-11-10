# Readiness checklist (15 items; mirrors the course checklist)

Tick an item only after doing its "How to verify". Update weekly. Count: 0 of 15.

## The paper
- [ ] The claim is one sentence. *Verify:* read it to someone outside the team; they can say the number and the data. (CLAUDE.md)
- [ ] The paper's own numbers are recorded in the repo with citations. *Verify:* every compared number is in `common.py` and cites a table.

## The data
- [ ] We have the data the paper used. *Verify:* a teammate runs `make data stats` on a clean machine and gets the same counts.
- [ ] The data is described the course's way. *Verify:* `results/data_report.md` answers the four questions and states class balance, with code.

## The reproduction
- [ ] A baseline is scored before the paper's method. *Verify:* `results/baselines/` shows B0 and B1 on the same split.
- [ ] The paper's method runs end to end. *Verify:* `make reproduce` reproduces the headline from raw data on a machine that is not ours.
- [ ] Our numbers sit beside the paper's in one table with three columns (paper, ours, difference), no empty cell.
- [ ] Every gap has a stated reason, or we say plainly that we could not determine one.

## Documentation and governance
- [ ] The Wiki runbook is complete. *Verify:* a teammate who did not write it follows it start to finish.
- [ ] The README is the front door. *Verify:* a newcomer can state our result within a minute.
- [ ] The Individual Contribution Summary Table is accurate. *Verify:* every row is backed by commits, issues or documents with that name.
- [ ] The Project board is clean. *Verify:* every card is closed, in progress with a reason, or dropped with a note.

## Presentation
- [ ] A dry run finished inside the limit without cutting the results section.
- [ ] A demo fallback is recorded and plays from the presentation machine with no network.
- [ ] Every member knows their part and the one number they explain.
