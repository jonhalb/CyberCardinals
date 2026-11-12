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


import numpy as np
import torch
import torch.nn.functional as F
from torch_geometric.nn import TransformerConv
from torch_geometric.nn.models.tgn import IdentityMessage, LastAggregator, LastNeighborLoader, TGNMemory

from kairos_repro.common import MSG_DIM
from kairos_repro.data.graph_encoding import one_hot_msg

MAX_NODES = 9_284  # largest StreamSpot graph (results/data_report.md); the memory table has one row per node


class PaperFaithfulKairos(torch.nn.Module):
    """KAIROS encoder (story M3-01) and decoder (story M3-02).

    Use, one graph at a time and one batch at a time, always in time order:
        model.start_graph(graph)          # graph from data.loading.localize(); wipes memory (D-17)
        err = model.edge_errors(batch)    # one error per edge, from an embedding built ONLY from the past
        model.advance(batch)              # now the batch's edges become part of the past
    """

    def __init__(self, config: dict, num_nodes: int = MAX_NODES):
        super().__init__()
        state = config["node_state_dim"]                          # 100: size of each node's state
        heads = config["attention_heads"]
        per_node = config["edge_embedding_dim"] // 2              # 100 per endpoint, 200 per edge (D-18)
        self.num_nodes = num_nodes
        # 1. Node memory: one state vector per node, all zeros at the start, updated by a GRU
        #    each time the node takes part in an edge (paper Sec. 4.2, "State Update").
        self.memory = TGNMemory(num_nodes, MSG_DIM, state, state,
                                message_module=IdentityMessage(MSG_DIM, state, state),
                                aggregator_module=LastAggregator())
        # 2. Neighbour list: remembers each node's 20 most recent edges (paper Sec. 5, |N| = 20).
        self.neighbors = LastNeighborLoader(num_nodes, size=config["neighbors"])
        # 3. Attention layer: mixes a node's state with its recent neighbours' states. Each
        #    neighbour edge carries its 42-dim message and an encoding of how long ago it happened.
        self.conv = TransformerConv(state, per_node // heads, heads=heads,
                                    dropout=config["attention_dropout"], edge_dim=MSG_DIM + state)
        # 4. Decoder (story M3-02): a small MLP that reads the 200-dim edge embedding and scores
        #    each of the 26 edge types (paper Sec. 4.2; 26 not 9: D-07). The paper says "MLP" but
        #    not its size: one hidden layer of 100 with tanh is our choice (deviation D-20).
        emb = config["edge_embedding_dim"]
        self.decoder = torch.nn.Sequential(
            torch.nn.Linear(emb, emb // 2), torch.nn.Tanh(),
            torch.nn.Linear(emb // 2, config["num_edge_types"]))
        self.register_buffer("_slot", torch.empty(num_nodes, dtype=torch.long))
        self._graph = None

    def start_graph(self, graph: dict) -> None:
        """Begin a new graph: forget every node state and neighbour from the previous one."""
        if int(graph["num_nodes"]) > self.num_nodes:
            raise ValueError("graph has %d nodes, memory holds %d" % (graph["num_nodes"], self.num_nodes))
        self.memory.reset_state()
        self.neighbors.reset_state()
        self._graph = {k: torch.from_numpy(np.asarray(graph[k])) for k in ("t", "src_type", "edge_type", "dst_type")}

    def edge_embeddings(self, batch: dict) -> torch.Tensor:
        """One 200-dim embedding per edge in the batch: [source node (100) | destination node (100)].

        Nothing about the batch's own edges is used except which nodes they touch, so the edge
        type the decoder must predict cannot leak in (tests/test_model.py checks this).
        """
        src = torch.from_numpy(batch["src"]).long()
        dst = torch.from_numpy(batch["dst"]).long()
        # every node in the batch plus its recent neighbours, and the past edges that link them
        n_id, edge_index, e_id = self.neighbors(torch.cat([src, dst]).unique())
        self._slot[n_id] = torch.arange(n_id.size(0))
        state, last_update = self.memory(n_id)
        g = self._graph
        past_msg = torch.from_numpy(one_hot_msg(g["src_type"][e_id].numpy(), g["edge_type"][e_id].numpy(),
                                                g["dst_type"][e_id].numpy()))
        age = self.memory.time_enc((last_update[edge_index[0]] - g["t"][e_id]).float())
        z = self.conv(state, edge_index, torch.cat([age, past_msg], dim=-1))
        return torch.cat([z[self._slot[src]], z[self._slot[dst]]], dim=-1)

    def advance(self, batch: dict) -> None:
        """Add the batch's edges to the past: update node states and neighbour lists."""
        src = torch.from_numpy(batch["src"]).long()
        dst = torch.from_numpy(batch["dst"]).long()
        self.memory.update_state(src, dst, torch.from_numpy(batch["t"]).long(), torch.from_numpy(batch["msg"]))
        self.neighbors.insert(src, dst)
        self.memory.detach()

    def edge_errors(self, batch: dict) -> torch.Tensor:
        """Per-edge reconstruction error (story M3-02): cross-entropy of the true edge type.

        The decoder reads the 200-dim embedding (built from the past only) and guesses which of
        the 26 edge types this edge is. A confident wrong guess gives a large error; that error is
        what model.scoring.graph_score() turns into a graph score. Training uses the mean of these.
        Call advance(batch) afterwards so the batch becomes part of the past.
        """
        logits = self.decoder(self.edge_embeddings(batch))
        target = torch.from_numpy(np.asarray(batch["edge_type"])).long()
        return F.cross_entropy(logits, target, reduction="none")
