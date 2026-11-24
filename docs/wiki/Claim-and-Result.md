# Claim and result

## The claim in one sentence

KAIROS (Cheng et al., IEEE S&P 2024, DOI 10.1109/SP54263.2024.00005) reports in **Table 4, row "Manzoor et al."**
TP = 100, TN = 375, FP = 0, FN = 0, and precision = recall = accuracy = AUC = 1.000 on the StreamSpot dataset,
training on 1 benign graph per scenario (5), validating on 24 per scenario (120), testing on 375 benign + 100 attack graphs,
with one time window per graph. **We try to get that result again with our own implementation.**

## The target, exactly as printed

Source: Cheng et al., *KAIROS: Practical Intrusion Detection and Investigation using Whole-system Provenance*,
2024 IEEE Symposium on Security and Privacy, pp. 3533-3551, DOI [10.1109/SP54263.2024.00005](https://doi.org/10.1109/SP54263.2024.00005).
Table 4 ("KAIROS' experimental results"), page 3540, row "Manzoor et al.":

| Datasets | TP | TN | FP | FN | Precision | Recall | Accuracy | AUC |
|---|---|---|---|---|---|---|---|---|
| Manzoor et al. | 100 | 375 | 0 | 0 | 1.000 | 1.000 | 1.000 | 1.000 |

The same row appears unchanged in Table 5 ("adjusted experimental results", page 3541): the adjustment only changes DARPA rows.

## The setup the paper states for this row (Sec. 5.1.1, page 3540)

| What | Paper | Where we follow it |
|---|---|---|
| Dataset | Manzoor et al. (StreamSpot): 6 scenarios x 100 graphs; the drive-by download scenario is the attack | [Data](Data) page |
| Labels | attack-scenario graphs = attack, all others benign | `common.label()`, graphs 300-399 |
| Time windows | "a single time window (§4.3) for each graph", so queue length 1 | one score per graph |
| Training | one benign graph per scenario (5 graphs) | graphs 0, 100, 200, 400, 500 (which one: D-11) |
| Validation | 24 benign graphs per scenario (120), used to set the detection threshold | x01-x24 per scenario (D-12) |
| Test | the remaining 75 benign graphs per scenario (375) and all 100 attack graphs | x25-x99 and 300-399 |
| Threshold | set from benign validation data after training (Sec. 4.3.3, page 3539) | maximum validation score (D-05) |
| Metrics | precision, recall, accuracy and AUC, counted per time window (= per graph here) | `eval/metrics.py`; AUC also from scores (D-24) |
| Model sizes | node state 100, neighbourhood 20, edge embedding 200 (Sec. 5) | `configs/paper_faithful.json` |

What the paper does **not** state (learning rate, epochs, batch size, seed, threshold rule, and more) is listed with our choice
for each in [Method and Deviations](Method-and-Deviations).

## Context: other systems on the same dataset (paper Tables 7 and 8, page 3542)

| System (paper table) | Precision | Recall | Accuracy |
|---|---|---|---|
| Unicorn (Table 7) | 0.98 | 0.93 | 0.96 |
| ThreaTrace (Table 8) | 0.98 | 0.99 | 0.99 |
| KAIROS (Tables 7 and 8) | 1.00 | 1.00 | 1.00 |

These are the paper's numbers, not ours. For Table 7 the paper says it needed no change for this dataset, because
each graph is already a single time window.

## Our result

**Outcome, in the [Evaluation Protocol](Evaluation-Protocol)'s wording: documented divergence** for the headline
paper-faithful model. The authors' variant (below) reproduces the row exactly, but it is an ablation and never the headline.

From `results/paper_faithful/comparison_seed0.md`:

| Metric | Paper (Table 4) | Ours (paper-faithful, seed 0) | Difference |
|---|---|---|---|
| TP / TN / FP / FN | 100 / 375 / 0 / 0 | 60 / 372 / 3 / 40 | -40 / -3 / +3 / +40 |
| Precision | 1.000 | 0.952 | -0.048 |
| Recall | 1.000 | 0.600 | -0.400 |
| Accuracy | 1.000 | 0.909 | -0.091 |
| AUC (0/1 predictions, as the paper's authors compute it) | 1.000 | 0.796 | -0.204 |
| AUC (from scores, threshold-free) | - | 0.961 | - |

**Why it misses** (from `results/paper_faithful/eval_meta_seed0.json`): the threshold, 4.04, is set by validation graph 119,
a Gmail graph. The lowest attack score (3.71) is below the highest benign test score (4.08), so attack and benign scores
overlap: 40 attacks fall under the threshold and 3 benign graphs go over it. The model still ranks attacks high (AUC from
scores 0.961); the threshold rule decides the hard numbers. Ranked reasons: [Gap Explanation](Gap-Explanation).

Seeds 0-4 and the authors' seed 12345: pending M3-05 (`results/seeds_summary.md`).

### The authors' variant (ablation, not the headline)

Same split and threshold rule, with what the authors' StreamSpot code does instead of what the paper describes: a
link-prediction decoder, memory 200, 5 neighbours from PyG's loader (D-26), and graph score = mean loss (track V; D-22, D-23). From `results/authors_variant/comparison_seed0.md`:

| Metric | Paper (Table 4) | Authors' variant (seed 0) | Difference |
|---|---|---|---|
| TP / TN / FP / FN | 100 / 375 / 0 / 0 | 100 / 375 / 0 / 0 | 0 |
| Precision / Recall / Accuracy | 1.000 / 1.000 / 1.000 | 1.000 / 1.000 / 1.000 | 0 |
| AUC (0/1 predictions) / AUC (from scores) | 1.000 / - | 1.000 / 1.000 | 0 |

Every attack graph scores at least 0.919 and every benign test graph at most 0.763, against a threshold of 0.767
(`results/authors_variant/eval_meta_seed0.json`). In short: **the authors' code reproduces Table 4; the model the paper
describes does not, on our run.**

### Baselines on the same split (already measured)

From `results/baselines/*/comparison_seed0.md`. Same split and the same threshold rule as the model. See [Baselines](Baselines).

| Metric | Paper (Table 4) | B0: do nothing | B1: histogram distance |
|---|---|---|---|
| TP / TN / FP / FN | 100 / 375 / 0 / 0 | 0 / 375 / 0 / 100 | 97 / 375 / 0 / 3 |
| Precision | 1.000 | 0.000 | 1.000 |
| Recall | 1.000 | 0.000 | 0.970 |
| Accuracy | 1.000 | 0.789 | 0.994 |
| AUC (0/1 predictions) | 1.000 | 0.500 | 0.985 |
| AUC (from scores) | - | 0.500 | 1.000 |

A simple edge-type histogram already separates the attack graphs almost perfectly, so the bar KAIROS has to clear on this
dataset is high, and a perfect score from any detector is less surprising than it looks.

## Numbers in the paper we could check against the data

| Paper | Says | We measured | Verdict |
|---|---|---|---|
| Table 2 | 89.8 M edges, 2,842,345 attack edges (3.165%) | 89,770,902 edges, 2,842,345 attack edges (3.166%) | match |
| Table 2 | 999,999 nodes | 5,044,482 distinct node ids | does not match (likely a capped count) |
| Table 3 | per-scenario average nodes and edges | four rows match exactly | match |
| Table 3 | Video Game: 8,831 nodes / 310,814 edges; Download: 8,637 / 112,958 | the other way round | rows swapped in the paper |

Details and the scripts behind each number: [Data](Data) page and `results/data_report.md`.
