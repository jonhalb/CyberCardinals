# Final presentation outline (10 to 15 minutes plus Q&A; every member presents their user stories)

Lead with the comparison: the paper's number beside ours on slide 2. Everything after it is explanation.

| # | Slide | Time | Speaker |
|---|---|---|---|
| 1 | Title, team, the claim in one sentence (number, data, split, table) | 0:30 | |
| 2 | **Comparison table: paper vs ours vs difference** | 1:00 | |
| 3 | The data: which dataset and version, how we got it by script, rows, class balance, what we had to drop or repair | 1:00 | Emiliano |
| 4 | The pipeline we rebuilt, end to end, and the baselines scored before the method | 1:30 | Jonas |
| 5 | Live demo: clone into an empty folder, run `make reproduce`, print one number (recording ready) | 2:30 | Jonas |
| 6 | Every choice the paper did not state, and what we did about each (from docs/deviations.md) | 1:30 | Jonas |
| 7 | Loss/score histogram with the threshold line; seed spread and margin | 1:00 | Aaliyah |
| 8 | Where we differ and why, ranked: stated difference, unstated choice, error (checked ours first) | 1:30 | Aaliyah |
| 9 | What would settle the gap: the experiment we did not have time to run, and what we expect | 0:45 | Aaliyah |
| 10 | Who did what: the contribution table from the README | 0:30 | Emiliano |
| 11 | Q&A buffer | | all |

Hard rules: every member presents the stories they contributed to; missing the slot costs 15% of the capstone;
a recording of the clean-checkout run must be in the repo (`scripts/record_demo.sh`, saved under docs/demo/) and play with no network.
