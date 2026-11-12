# Paper cross-check, 2026-11-12

The whole paper (IDS_PROJECT.pdf, Sections 1-8 and Appendices A-F) read against the plan. "In plan" means the
scaffold or backlog covers it; "Out" means it is outside the approved scope (one dimension: attack agnosticity,
StreamSpot only).

## Section by section

| Paper | What it says | Status | Where |
|---|---|---|---|
| Abstract, Sec. 1 | Four dimensions: scope, attack agnosticity, timeliness, attack reconstruction | One in scope (attack agnosticity) | docs/schedule.md, ADR-0001 |
| Sec. 3 Threat model | Anomaly-based; trained on attack-free benign data | In plan | train on 5 benign graphs only |
| Sec. 4.1 Graph construction | Time-stamped directed edges; 3 node types, 9 edge types; hierarchical feature hashing of paths/IPs, 16 dims | Adapted: StreamSpot has 8 node and 26 edge type codes, no paths, IPs or timestamps | D-03, D-04, D-07 |
| Sec. 4.2 Encoder | TGN; UniMP GNN; node state starts at zero; neighbours' states, edge features and timestamps | In plan | paper_faithful.py spec, M3-01 |
| Sec. 4.2 State update | GRU on source and destination after each edge; the edge must not leak into its own prediction | In plan | M3-01, M3-04 leakage test; D-19 batching |
| Sec. 4.2 Decoder | MLP predicts edge type; cross-entropy = reconstruction error; encoder and decoder trained together | In plan | M3-02; D-07, D-18 |
| Sec. 4.3.1 | Cut = mean + 1.5 SD of the window's errors; rareness (IDF) picks suspicious nodes | Cut in plan; IDF unused with one window | model/scoring.py; D-06, D-09 |
| Sec. 4.3.2 | Queues of time windows linked by suspicious nodes | Out: queue length is 1 for this dataset | D-10 |
| Sec. 4.3.3 | Window score = mean error above the cut; queue score = product; threshold from benign validation data | In plan (product of one window = that window) | scoring.py; D-05 |
| Sec. 4.4 Investigation | Graph reduction, Louvain communities, summary graphs | Out: reconstruction dimension | D-10 |
| Sec. 5 Setup | PyG, scikit-learn, NetworkX; state 100, neighbourhood 20, edge embedding 200, feature dim 16, window 15 min; 64 GB server | Sizes in plan; feature dim and window length do not apply | configs/paper_faithful.json; D-16 |
| Sec. 5.1.1 Dataset | 6 scenarios x 100 graphs; attack = drive-by download; 1 train, 24 validation, 75 test per benign scenario, 100 attack test; one window per graph | In plan, verified on the real file | common.py; D-11, D-12 |
| Table 2 | 999,999 nodes; 89.8M edges; 2,842,345 attack edges (3.165%) | Edges and attack edges match exactly; nodes do not (we count 5,044,482) | results/data_report.md |
| Table 3 | Average nodes and edges per scenario | All match, except Video Game and Download are swapped in the paper | results/data_report.md |
| Table 4 (and 5) | TP 100, TN 375, FP 0, FN 0; precision, recall, accuracy, AUC 1.000 | The target; all eight metrics computed | eval/compare.py |
| Sec. 5.2 Metrics | Counted per time window (= per graph here); precision, recall, accuracy, AUC | In plan | eval/metrics.py |
| Sec. 5.2 Retraining | Retrain on false positives | Out (DARPA only) | - |
| Sec. 5.3, Tables 7-8 | Unicorn 0.98/0.93/0.96 and ThreaTrace 0.98/0.99/0.99 on this dataset | Recorded as context | common.py, Claim wiki page |
| Sec. 5.4 Hyperparameters | Sensitivity study | Out (DARPA only) | - |
| Sec. 5.5 Reconstruction | Summary graph sizes | Out | - |
| Sec. 5.6 Performance | About 11K edges/s, time per window | Out (timeliness dimension); our timings logged anyway | verification_2026-11-11.md |
| Sec. 6 Limitations | Public datasets are poorly documented; reproduction is hard | Supports our Table 2 and Table 3 findings | Gap-Explanation |
| Appendices A-D | DARPA details and summary graphs | Out | - |

Nothing the paper states for the Manzoor et al. experiment is missing from the plan.

## What the paper does NOT state (each is a logged choice)
Learning rate, optimiser, epochs, batch size, seed (D-01, D-02, D-19); which graph trains and which 24 validate (D-11, D-12);
how the validation data sets the threshold (D-05); how the 200-dim edge embedding is formed from two endpoints (D-18);
attention heads, dropout, time encoding (D-08); node features and the edge-type count for this dataset (D-03, D-07);
whether AUC uses 0/1 predictions or scores (we report both).

## Will the numbers match? Evidence so far says no
Three trial runs of a throwaway prototype built to the paper's description (one seed each; not the team's result):

| Trial | TP of 100 | FP of 375 | AUC from scores | Highest validation graph |
|---|---|---|---|---|
| 10 epochs, 200-dim per endpoint | 63 | 0 | 0.971 | Gmail 104 (3.91) |
| 40 epochs, 200-dim per endpoint | 4 | 0 | 0.990 | Download 416 (5.19) |
| 10 epochs, 100-dim per endpoint (D-18 reading) | 0 | 0 | 0.987 | Download 416 (5.32) |

In every trial the model ranks attacks high (AUC 0.97-0.99) but attack and benign scores overlap (24 to 60 benign test graphs
score above the lowest attack), and one benign validation graph sets the threshold above most attacks. The paper's perfect
score is therefore unlikely to be matched by the paper-faithful track. The histogram baseline scores 97 / 375 / 0 / 3.

Ranked candidate causes for the Gap-Explanation page:
1. Unstated choice: the threshold rule (maximum validation score is fragile to one outlier).
2. Stated difference: the authors' released code reportedly trains link prediction with memory 200 and 5 neighbours, not the
   paper's edge-type decoder (to confirm against the source; story M3-06 measures it).
3. Unstated choices: epochs, learning rate, seed, embedding layout.
4. Possible error on our side: to be ruled out by the M3-04 leakage test and the M3-07 cross-check.
