# Evaluation protocol

Story M2-10. Owner: Aaliyah Moorefield. Committed before `model/evaluate.py` was run on any trained model
(the commit date is in the git history).
Nothing below may be changed after the first model result exists. If we ever have to change something, the change gets
a dated note at the bottom of this page and a row in `docs/deviations.md`, and both versions of the result are reported.

One disclosure. A throwaway feasibility prototype was run once on 2026-11-11 to see whether the pipeline fits on a
laptop (`docs/paper_crosscheck.md`). Its numbers are not results and are not reported. No setting on this page was
picked from it: every value comes from the paper or from the authors' code, with its source in `docs/deviations.md`.

## The claim we test
KAIROS, IEEE S&P 2024, Table 4, row "Manzoor et al." (StreamSpot): TP 100, TN 375, FP 0, FN 0; precision, recall,
accuracy and AUC all 1.000.

## Data split (fixed in `src/kairos_repro/common.py`; scripts import it and never retype it)
| Split | Graphs | Count |
|---|---|---|
| Train | 0, 100, 200, 400, 500 | 5 benign |
| Validation | x01 to x24 of each benign scenario | 120 benign |
| Test | x25 to x99 of each benign scenario, and 300 to 399 | 375 benign + 100 attack |

The test graphs are scored once per run. No setting is chosen by looking at test scores.

## What is fixed in advance
- Model: `configs/paper_faithful.json` as committed, including the exact recent-neighbour sampler (D-26),
  trained once per seed with `make train`.
- Training: 10 epochs, Adam, learning rate 0.0001, batches of 1,024 edges in file order (`configs/paper_faithful.json`).
  We do not pick the number of epochs from validation or test results.
- Per-edge error: cross-entropy of the true edge type (paper Sec. 4.2).
- Graph score: mean error of the edges whose error is above mean + 1.5 SD of that graph's errors (paper Sec. 4.3.1
  and 4.3.3, one time window per graph as in Sec. 5.1.1; population SD, D-06).
- Threshold: the largest graph score among the 120 validation graphs (D-05). A graph is called an attack when its
  score is strictly greater than the threshold.
- Scoring pass: one pass, evaluation mode (no dropout), node memory reset before every graph (D-17).
- Seeds: 0, 1, 2, 3, 4 and 12345. Seed 0 is the headline. We also report the mean and the spread over all six.

## Metrics
TP, TN, FP, FN, precision, recall, accuracy and F1 on the 475 test graphs.
AUC is reported two ways, and we always say which one a number is (D-24):
- AUC from the 0/1 predictions. This is how the authors' `test.py` computes it, so it is the one compared with the paper.
- AUC from the continuous graph scores. It does not depend on the threshold, so it shows how well the model ranks
  attack graphs above benign ones even when the threshold is badly placed.

## Baselines, on the same split and the same threshold rule
B0 do-nothing (always benign) and B1 edge-type histogram distance. Both were scored and committed before the model
(`results/baselines/`). The model's result is always shown next to them.

## Tracks
- P, paper-faithful: the headline. Everything above applies to it.
- V, authors' variant: an ablation with the authors' link-prediction decoder. Same split, same threshold rule; graph
  score = mean per-edge error, as in the authors' code. Never reported as the headline.
- X, authors' repo run as-is: an outside cross-check, labelled as not our code.

## How we will word the outcome
- "Reproduced exactly": the seed-0 confusion matrix equals the paper's (TP 100, TN 375, FP 0, FN 0).
- "Reproduced within tolerance": seed-0 precision, recall and accuracy are all at least 0.95.
- Anything else is a "documented divergence". We then report which graphs were misclassified, their scores against
  the threshold, and ranked reasons: first an error of ours, then a stated difference from the paper, then a choice
  the paper leaves open. We check our own work first.

A failed reproduction with honest evidence is a valid result. We report what the scripts produce.

## Where the numbers come from
`make evaluate` writes `results/<track>/graph_scores_seed{N}.csv` (one row per validation and test graph) and
`eval_meta_seed{N}.json` (threshold and the graph that set it). `make compare` turns the score file into
`metrics_seed{N}.json` and `comparison_seed{N}.md`. Every number in the report comes from these files.
