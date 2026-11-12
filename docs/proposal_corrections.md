# Corrections to apply to the proposal (team checklist in the README)

Checked against the paper and a read of the authors' repo.
1. Repository: the code is at github.com/ubc-provenance/kairos (the paper still lists ProvenanceAnalytics/kairos).
2. Environment: the authors pin Python 3.9, torch 1.13.1, PyG 2.0.0, scikit-learn 1.2.0, networkx 2.8.7.
3. StreamSpot has no file paths or IPs, so hierarchical feature hashing does not apply; the authors use one-hot node types.
4. The authors' StreamSpot code does link prediction; the paper describes edge-type classification. We follow the paper and run the code's version as an ablation.
5. Paper hyperparameters: |s|=100, |N|=20, |z|=200; the authors' StreamSpot code uses memory 200 and neighbourhood 5. Learning rate, epochs and seed are not in the paper.
6. Time windows, IDF rareness, queues and Louvain are not needed for this row: one window per graph (Sec. 5.1.1), and the score formula does not use rareness.
7. Hardware: the paper's server had 64 GB; the authors' README asks for at least 64 GB for their fixed 5,045,000-node table. We compact node ids and measure.
8. No GPU is needed; the authors' code runs on CPU.
9. Loading: the authors use PostgreSQL; we stream the file instead.
10. The paper's Table 3 appears to have the Video Game and Download rows swapped: confirm with `make stats` before stating it.
11. Add what the rubric asks of a proposal: venue and year (S&P 2024), the claim as a table row, evidence the data loads, the blocker and fallback, roster and hours, the recorded commit vote.
12. Proposal weight: the rubric says 1% (the kickoff deck's "2%" is a typo).
