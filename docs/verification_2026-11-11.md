# End-to-end feasibility check, 2026-11-11

Every stage of `make reproduce` has now been run on the real data on a clean 2-core, 8 GB Linux machine
(Python 3.9, torch 1.13.1, PyG 2.0.0). The data stages and baselines used the repo's code. For train and
evaluate, which are still stubs, a throwaway prototype was written to the spec in
`src/kairos_repro/model/paper_faithful.py` to prove the design works and to time it. That prototype is NOT in
the repo and its numbers are NOT the team's result: stories M3-01 to M3-04 must produce their own.

## The pipeline works end to end

| Stage | Result | Time (2 cores) |
|---|---|---|
| data, stats, graphs, baselines | as in verification_2026-11-09.md | ~15 min |
| train (paper-faithful settings, 5 graphs, 881,643 edges) | loss 1.71 -> 0.67 over 10 epochs | 16 s per epoch, ~3 min; peak RAM 0.5 GB |
| evaluate (595 graphs, ~88M edges) | per-graph scores for 120 validation + 475 test graphs | ~115,000 edges/s per process: ~13 min single, ~7 min with 2 processes |
| compare, check_headline | comparison table and metrics JSON written, exit 0 | seconds |

A full `make reproduce` is about 30-35 minutes on a small machine. That is too long for a live demo:
the talk needs `QUICK=1`, a single-graph `detect` demo, or the recording (risk R3).

## What the prototype scored (one seed, indicative only)

| Run | TP | TN | FP | FN | Accuracy | AUC (0/1) | AUC (scores) |
|---|---|---|---|---|---|---|---|
| Paper Table 4 | 100 | 375 | 0 | 0 | 1.000 | 1.000 | - |
| B0 do nothing | 0 | 375 | 0 | 100 | 0.789 | 0.500 | - |
| B1 histogram distance | 97 | 375 | 0 | 3 | 0.994 | 0.985 | - |
| Prototype, 10 epochs, paper scoring rule | 63 | 375 | 0 | 37 | 0.922 | 0.815 | 0.971 |
| Prototype, 40 epochs, paper scoring rule | 4 | 375 | 0 | 96 | 0.798 | 0.520 | 0.990 |

## Findings the team should plan around

1. **Expect a gap, and expect the simple baseline to beat the model on hard metrics.** The model ranks attack
   graphs above benign ones well (AUC from scores 0.97-0.99) but the 0/1 result is far from 100/375/0/0.
   A failed or partial reproduction with ranked causes is a valid result for this course.
2. **The threshold rule decides the outcome.** Threshold = maximum validation score means one unusual benign
   validation graph sets the bar. At 10 epochs the three highest validation scores were Gmail graphs (104,
   113, 102), just under many attacks. At 40 epochs a single Download graph (416) scored 5.19 and pushed the
   threshold above 96 of 100 attacks, even though ranking improved. The paper only says the threshold is set
   from benign validation data; "max" comes from the authors' code.
3. **Training length (unstated in the paper) moves the result a lot.** Fix epochs in the Evaluation Protocol
   before looking at test results, and never pick them using test labels.
4. **Gmail graphs look most like attacks** (small graphs, highest benign scores). Worth a sentence in the
   Data and Gap pages.
5. **Memory is not a problem** with one graph at a time and local node ids (ADR-0005): 0.5 GB peak in training.
6. **The authors' variant (M3-06) is the most likely explanation for the gap**, because the authors' code
   (per summaries; check) trains a link-prediction model, not the paper's edge-type decoder. Keep M3-06 if
   time allows; it is worth more than extra seeds.

## Changes made to the scaffold today

- `data/loading.py`: added `localize()` (ids local to a graph) with a test; `batches()` ignores scalar fields.
- Model stubs, CLAUDE.md, ADR-0005, deviations (D-04, D-13, new D-17), risks (R1, R2, new R12): updated to the
  one-graph-at-a-time design and the measured facts.
- `eval/compare.py`: the comparison file now also states AUC from continuous scores.
- `docs/schedule.md`: Dec 2 deadline and the four-iteration plan; `docs/backlog.csv` iterations match the board.

## Suggested additions to the Evaluation Protocol (story M2-10, decide before any model result)

- Headline = paper scoring rule + max-validation threshold, fixed epochs, seed 0. Report it whatever it is.
- Always report AUC from scores next to the 0/1 metrics.
- A labelled sensitivity table (not the headline): the same scores under one or two alternative validation-only
  threshold rules, to show how much of the gap is the threshold.
