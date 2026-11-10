# CyberCardinals: KAIROS reproduction (CIS 3370)

Read this file and docs/deviations.md at the start of every session.

## The claim (one sentence)
KAIROS (Cheng et al., IEEE S&P 2024, DOI 10.1109/SP54263.2024.00005) reports in **Table 4, row
"Manzoor et al."**: TP=100 TN=375 FP=0 FN=0, precision = recall = accuracy = AUC = 1.000, on the
StreamSpot dataset, with 1 benign graph per scenario for training (5), 24 per scenario for validation
(120), 375 benign + 100 attack graphs for test, and one time window per graph. We try to get that again.
Secondary, only if time allows: Table 7 row "Manzoor et al." (Unicorn 0.98 / 0.93 / 0.96).

## What the course grades (capstone = 45% of the course grade; see docs/rubric_map.md)
Reproduction 15% (clean-checkout pipeline 35, fidelity to the paper 30, comparison 25, hygiene 10),
GitHub repo 9%, Project board 8%, Wiki report 5%, final presentation 7%, proposal 1%.
A failed reproduction is a valid result if the evidence is honest. No late work is accepted.

## The rule that shapes everything
**We rebuild the pipeline ourselves.** The authors' repo (github.com/ubc-provenance/kairos) is a
reference for details the paper omits, and an external cross-check. Do not paste or copy its files.
Every value taken from it is a row in docs/deviations.md with its source.

## Tracks
- **P, paper-faithful (headline):** follows the paper wherever it states a value (configs/paper_faithful.json).
- **V, authors' variant (ablation):** link prediction, neighbourhood 5, state 200 (configs/authors_variant.json).
- **X, authors' repo run as-is (cross-check only):** results/authors_repo/, labelled as not our code.
- **B0, do-nothing** and **B1, histogram distance** baselines on the same split, scored before the model.

## Data facts (from the team plan; Phase 2 confirms)
all.tar.gz from github.com/sbustreamspot/sbustreamspot-data, SHA-256 1551d7eb...5d23cf (full value in
src/kairos_repro/common.py). Columns: source-id, source-type, dest-id, dest-type, edge-type, graph-id.
Graph ids: 0-99 YouTube, 100-199 Gmail, 200-299 VGame, 300-399 drive-by-download (ATTACK),
400-499 Download, 500-599 CNN. Edge message = one-hot src type (8) + edge type (26) + dst type (8) = 42.
t = 1-based file line. Node ids are compacted (ADR-0005). Splits live in src/kairos_repro/common.py; import, never retype.

## Environment
Python 3.9, torch 1.13.1 CPU, torch-geometric 2.0.0, scikit-learn 1.2.0, networkx 2.8.7. Do not upgrade PyG.
Run with PYTHONHASHSEED=0 (the Makefile does). Seeds: 0-4 plus the authors' 12345.

## Rules
- Individual commits: each member commits their own work under their own account. Claude Code never
  runs git add / commit / push; it tells the user what to commit and suggests a message.
- Work comes from a user story on the board (docs/backlog.csv). Name the story id in the branch, commits and PR.
- Every number reported comes from a script in this repo and a file under results/.
- Every choice the paper does not state gets a row in docs/deviations.md before it is used.
- Never commit data/raw, data/processed, *.pt, or secrets.
- Ownership: Emiliano = src/kairos_repro/data, Jonas = src/kairos_repro/model (train, paper_faithful), environment,
  Aaliyah = model/evaluate.py, src/kairos_repro/eval, baselines. Ask before editing someone else's files.
