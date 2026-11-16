# ADR-0005: One graph at a time, with node ids local to the graph

Status: decided 2026-11-11 (replaces the earlier "global compaction" proposal). Story M2-09 re-measures on team laptops.

Context. The authors' StreamSpot code allocates a node-memory table for 5,045,000 nodes (summary of the repo; check) and their
README asks for at least 64 GB. The paper's Table 2 counts 999,999 nodes. Measured on the real file (`make stats`): 5,044,482
distinct node ids, and the per-graph node counts sum to 5,046,878, so ids are almost never shared between graphs. The largest
graph has 9,284 nodes. Global renumbering (IdCompactor) therefore saves nothing: 5.04M rows either way.

Decision. Process one graph at a time. `data.loading.localize()` renumbers a graph's ids to 0..n-1; the model's node memory is
sized for the largest graph and reset, with the neighbour state, between graphs. With the cross-entropy decoder node ids are
only indices, so this is lossless within a graph. It drops any state carried across graphs through the rare shared ids
(about 2,400 of 5.04M), logged as deviation D-17. In the authors' variant, negative sampling draws over the id range, so
local ids change those draws: note it in that ablation.

Evidence. [x] distinct node count from `make stats` (5,044,482). [x] feasibility run 2026-11-11: full train + evaluate on a
2-core, 8 GB machine; training peaked at 0.5 GB of RAM. [ ] memcheck on each team laptop (M1-01). [x] M2-09: real model footprint and local ids against
stored ids, measured by `make footprint`; numbers in the block below and in results/id_check.md.

<!-- M2-09:start -->
Measured by `make footprint` on 2026-11-16 (user jonas, 8.1 GB RAM); source files results/env_report.txt and results/id_check.md.
- One full training epoch, one graph at a time: peak RSS 0.46GB.
- After also scoring the largest graph: peak RSS 0.54GB.
- After also building the stored-id table for graph(s) 101 (842,447 rows instead of 9284): peak RSS 1.37GB.
- Local ids against stored ids, graph(s) 101: largest per-edge difference 0.00e+00; scores the same.
<!-- M2-09:end -->
