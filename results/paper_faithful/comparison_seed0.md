| Metric | Paper (KAIROS (IEEE S&P 2024), Table 4, row 'Manzoor et al.') | Paper-faithful (ours) | Difference |
|---|---|---|---|
| TP | 100 | 60 | -40 |
| TN | 375 | 372 | -3 |
| FP | 0 | 3 | +3 |
| FN | 0 | 40 | +40 |
| precision | 1.000 | 0.952 | -0.048 |
| recall | 1.000 | 0.600 | -0.400 |
| accuracy | 1.000 | 0.909 | -0.091 |
| auc | 1.000 | 0.796 | -0.204 |

AUC above is from the 0/1 predictions, so it depends on the threshold. AUC from the continuous graph scores (threshold-free): 0.961.
