# Claim and result

## The claim, quoted
KAIROS, Table 4, row "Manzoor et al.": TP = 100, TN = 375, FP = 0, FN = 0; precision, recall, accuracy and AUC all 1.000.
Dataset: StreamSpot (Manzoor et al.), 600 graphs. Split: 1 benign graph per scenario for training, 24 for validation, the remaining 75 per scenario
plus all 100 attack graphs for test; one time window per graph (paper Sec. 5.1.1).

## What the paper reports for other systems on the same dataset (context, not our target)
| System (paper table) | Precision | Recall | Accuracy |
|---|---|---|---|
| Unicorn (Table 7) | 0.98 | 0.93 | 0.96 |
| ThreaTrace (Table 8) | 0.98 | 0.99 | 0.99 |
| KAIROS (Tables 4, 7, 8) | 1.00 | 1.00 | 1.00 |

## One sentence
(copy from CLAUDE.md)

## Result
(paste `results/paper_faithful/comparison_seed0.md`; three columns: paper, ours, difference; no empty cell)
Seeds 0-4 and 12345: (paste `results/seeds_summary.md`).
Baselines on the same split: (link Baselines page).
