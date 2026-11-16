# Local ids against stored (global) ids: story M2-09

Written by `python -m kairos_repro.tools.footprint` on 2026-11-16. Weights: trained model_seed0.pt.
The same weights score the same graph twice: once with ids renumbered to 0..n-1 and once with the
ids exactly as stored on disk. "Same" means every per-edge error agrees to within 0.00001.

| graph | edges | nodes | rows, local table | rows, global table | largest per-edge difference | score, local | score, global | same |
|---|---|---|---|---|---|---|---|---|
| 101 | 39280 | 6732 | 9284 | 842447 | 0.00e+00 | 3.761732 | 3.761732 | yes |

Result: local ids give the same scores as the stored ids.

## Memory, same run (peak RSS only goes up, so each line includes the ones above it)

```
2026-11-16 | jonas | x86_64 | ram=8.1GB | Linux-6.6.87.2-microsoft-standard-WSL2-x86_64-with-glibc2.35 | model_train_1_epoch_881643_edges | table=0.01GB | peak_rss=0.46GB
2026-11-16 | jonas | x86_64 | ram=8.1GB | Linux-6.6.87.2-microsoft-standard-WSL2-x86_64-with-glibc2.35 | model_score_largest_graph_574_716176_edges | table=0.01GB | peak_rss=0.54GB
2026-11-16 | jonas | x86_64 | ram=8.1GB | Linux-6.6.87.2-microsoft-standard-WSL2-x86_64-with-glibc2.35 | stored_id_table_graph_101 | table=0.61GB | peak_rss=1.37GB
```
