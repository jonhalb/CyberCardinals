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
2-core, 8 GB machine; training peaked at 0.5 GB of RAM. [ ] memcheck on each team laptop (M1-01). [ ] M2-09: scores for one graph identical with local and
global ids.
