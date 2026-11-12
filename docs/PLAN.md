# Plan

Built from the paper (IDS_PROJECT.pdf), the course rubric files, and a read of the authors' public repo
(summaries only; confirm against source before relying on anything marked "check").

## What we are reproducing
See the one-sentence claim in CLAUDE.md. Table 4, row "Manzoor et al.", StreamSpot, one window per graph.

## Tracks
| Track | What | Why | Owner |
|---|---|---|---|
| B0 | Do-nothing baseline | Course requires a baseline scored before the method | Aaliyah |
| B1 | Histogram-distance baseline | One simple model on the same split and threshold rule | Aaliyah |
| **P** | **Our paper-faithful model (headline)** | Rubric: fidelity to the paper where it states values | Jonas, Aaliyah |
| V | Authors' variant as an ablation | Measures the paper-versus-code gap | Jonas |
| X | Authors' repo run once as an external cross-check | Shows where our numbers differ from theirs | Emiliano |

## Facts that decide the design
Verified against the paper: Table 4 row; Table 7 Unicorn row; split of 1 / 24 / remaining per scenario; one time window
per graph (Sec. 5.1.1); |s|=100, |N|=20, |z|=200 (Sec. 5); edge-type decoder with cross-entropy (Sec. 4.2); anomaly
cut at mean + 1.5 SD (Sec. 4.3.1); window score = mean of errors above the cut (Sec. 4.3.3); lr, epochs, seed not stated.
From summaries of the authors' StreamSpot code (check): link-prediction loss with random negatives, neighbourhood 5,
memory 200, Adam 1e-4, batch 1024, 10 epochs, `torch.manual_seed(12345)`, threshold = max validation loss,
one-hot node types, fixed node table of 5,045,000 rows, PostgreSQL loading, test.py run twice.
Verified 2026-11-09 on the real file: checksum, 89,770,902 edges, 600 graphs, per-scenario averages, and the Table 3
Video Game / Download swap (docs/verification_2026-11-09.md).

## Milestones (docs/backlog.csv holds the stories and points)
| Milestone | Contents | Rubric lines it feeds |
|---|---|---|
| M1 Environment setup | pinned environment that installs from one script; memcheck on each laptop | Repo |
| M2 Data and baselines | download, stats, graphs, tests, B0, B1, metrics, evaluation protocol | Pipeline completeness, comparison |
| M3 Paper-faithful pipeline | encoder, decoder, training, evaluation, seeds, variant, cross-check | Fidelity, comparison, hygiene |
| M4 Comparison, report, presentation | tables, Wiki, README, clean-checkout test, deck, dry run | Wiki, repo, presentation |

The deck's suggested pacing: weeks 1-4 shortlist, data loading, proposal; 5-8 preprocessing and a baseline; 9-11 the
paper's method and comparison; 12-15 close gaps, report, rehearse. Real dates go in docs/schedule.md.

## Evaluation protocol (commit to the Wiki before any model number exists, story M2-10)
- Metrics: TP, TN, FP, FN, precision, recall, accuracy, AUC (hard labels, as the authors compute it), plus F1 and AUC from scores.
- Split: exactly as in src/kairos_repro/common.py. Seeds 0-4 and 12345; seed 0 is the headline, mean and spread reported.
- The rubric sets no pass bar. For our own wording: "reproduced exactly" = seed-0 confusion matrix equals the paper's;
  "reproduced within tolerance" = precision, recall and accuracy all at least 0.95; anything else is a documented divergence
  with ranked reasons (a stated difference, an unstated choice, or an error, in that order; check our own work first).
- Every divergence gets: which graphs were misclassified, their score against the threshold, and the cause we can support.

## Open questions for Dr. Parra (team checklist in the README)
1. Is StreamSpot-only scope acceptable (the DARPA data is terabytes)?
2. Is using the authors' code as a reference and cross-check fine, given we write our own pipeline?
3. Proposal weight: the kickoff deck says both 1% and 2%; the rubric says 1%.
