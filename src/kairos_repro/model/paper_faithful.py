"""The KAIROS model as the paper describes it, written by us. OWNER: Jonas (stories M3-01, M3-02).

Do not copy the authors' files. Build this from the paper (Sec. 4.2) and the PyG 2.0.0 APIs,
and record every decision the paper leaves open in docs/deviations.md.

Spec
----
Input   per edge: source/destination node ids (local to the graph: data.loading.localize), edge type, time t, 42-dim message
        [src node type one-hot | edge type one-hot | dst node type one-hot].
Memory  node state s(v), dimension 100, initialised to zeros, updated with a GRU after each edge
        (paper Sec. 4.2 "State Update"); PyG's TGNMemory is the building block. One graph at a
        time: size the memory for the largest graph (9,284 nodes) and reset memory and neighbour
        state between graphs (deviation D-17, ADR-0005). scripts/stack_check.py shows the PyG calls.
Encoder TransformerConv (the UniMP-style layer) over the 20 most recent neighbours, producing a
        200-dim edge embedding z (100 per endpoint, concatenated: D-18) from the node states, neighbour edge messages and time encodings.
        The edge being predicted must NOT leak into z (use states from just before t).
Decoder MLP(z) -> logits over 26 edge types; loss = cross-entropy against the true edge type.
Score   per-edge error = cross-entropy; graph score via model.scoring.graph_score().
Config  configs/paper_faithful.json; every UNSTATED value has a row in docs/deviations.md.
"""


class PaperFaithfulKairos:
    def __init__(self, config: dict, num_nodes: int):
        raise NotImplementedError("story M3-01: encoder and memory")

    def edge_errors(self, batch):
        raise NotImplementedError("story M3-02: decoder and per-edge cross-entropy")
