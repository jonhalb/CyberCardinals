# Method and deviations

Enough detail for a reader to repeat the work. Pipeline: download and verify, stream into per-graph arrays, local node ids, TGN-style encoder with
memory, MLP edge-type decoder, per-edge cross-entropy, graph score, threshold, prediction. Link every stage to its script.
Then reproduce the table from docs/deviations.md with every row (D-01 onward) and what we did.
