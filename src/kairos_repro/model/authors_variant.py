"""The authors' StreamSpot variant, written by us as an ablation. OWNER: Jonas (story M3-06).

The paper describes an edge-TYPE decoder (our headline model, paper_faithful.py). The authors'
public StreamSpot code does something different, and this file rebuilds that so we can compare.
Read for reference, not copied: github.com/ubc-provenance/kairos, commit 0e0b633,
StreamSpot/src/train.py and test.py (deviations D-22 to D-24).

What is different from the paper-faithful model
-----------------------------------------------
1. The question asked of each edge. Not "which of the 26 types is this edge?" but "is this a real
   edge?" (link prediction). For every real edge (source -> destination) the model also sees one
   fake edge from the same source to a randomly drawn node, and must score the real one high and
   the fake one low. Error per edge = BCE(real, 1) + BCE(fake, 0).
2. Sizes. Node state 200 (not 100), 5 recent neighbours (not 20), 200 numbers per NODE embedding.
3. The graph score is the plain mean of the per-edge errors (config "graph_score": "mean_loss").

The random node. The authors draw it from 0..5,045,000, the size of their one big node table. A
StreamSpot graph has at most 9,284 nodes, so the draw almost always lands on a node that has never
appeared: all-zero state, no neighbours. We keep one graph at a time with local ids (ADR-0005), so
we draw from the same range and send every draw that is not a node of the current graph to one
reserved, always-empty row. Same odds, same empty node, without a 5,045,000-row table (D-22).
"""
import numpy as np
import torch
import torch.nn.functional as F

from kairos_repro.model.paper_faithful import MAX_NODES, PaperFaithfulKairos


class AuthorsVariantKairos(PaperFaithfulKairos):
    """Same encoder building blocks and the same three calls as the paper-faithful model:
    start_graph(graph), edge_errors(batch), advance(batch)."""

    def __init__(self, config: dict, num_nodes: int = MAX_NODES):
        dim = config["memory_dim"]                                   # 200
        encoder = {"node_state_dim": dim, "neighbors": config["neighbors"],
                   "neighbor_sampler": config.get("neighbor_sampler", "pyg"),
                   "edge_embedding_dim": 2 * config["embedding_dim"],   # parent halves it: 200 per node
                   "attention_heads": config["attention_heads"], "attention_dropout": config["attention_dropout"],
                   "num_edge_types": 1}
        super().__init__(encoder, num_nodes=num_nodes + 1)           # + 1: the reserved empty row
        del self.decoder                                             # no edge-type decoder in this variant
        self.empty_row = num_nodes
        self.negative_range = int(config["negative_range"])          # 5,045,000
        self.eval_seed = int(config["authors_seed"])                 # 12345
        emb = config["embedding_dim"]
        # Link predictor: one linear layer per endpoint, added, ReLU, one output number.
        self.lin_src = torch.nn.Linear(emb, emb)
        self.lin_dst = torch.nn.Linear(emb, emb)
        self.lin_final = torch.nn.Linear(emb, 1)
        self._rng = torch.Generator()
        self._graph_nodes = 0

    def start_graph(self, graph: dict) -> None:
        if int(graph["num_nodes"]) > self.empty_row:
            raise ValueError("graph has %d nodes, memory holds %d" % (graph["num_nodes"], self.empty_row))
        super().start_graph(graph)
        self._graph_nodes = int(graph["num_nodes"])
        # When scoring, restart the random draws for every graph from the same seed, as the authors'
        # test pass does, so a graph's score does not depend on which graphs were scored before it.
        self._rng.manual_seed(self.eval_seed)

    def _fake_destinations(self, n: int) -> torch.Tensor:
        if self.training:
            draw = torch.randint(0, self.negative_range + 1, (n,))                    # global RNG, seeded by train.py
        else:
            draw = torch.randint(0, self.negative_range + 1, (n,), generator=self._rng)
        return torch.where(draw < self._graph_nodes, draw, torch.full_like(draw, self.empty_row))

    def _score(self, z_src: torch.Tensor, z_dst: torch.Tensor) -> torch.Tensor:
        return self.lin_final((self.lin_src(z_src) + self.lin_dst(z_dst)).relu()).squeeze(-1)

    def edge_errors(self, batch: dict) -> torch.Tensor:
        """Per-edge error: how badly the model tells the real edge from the fake one."""
        src = torch.from_numpy(np.asarray(batch["src"])).long()
        dst = torch.from_numpy(np.asarray(batch["dst"])).long()
        fake = self._fake_destinations(len(src))
        n = len(src)
        z = self.node_embeddings(torch.cat([src, dst, fake]))
        real_out = self._score(z[:n], z[n:2 * n])
        fake_out = self._score(z[:n], z[2 * n:])
        return (F.binary_cross_entropy_with_logits(real_out, torch.ones_like(real_out), reduction="none")
                + F.binary_cross_entropy_with_logits(fake_out, torch.zeros_like(fake_out), reduction="none"))

    def edge_embeddings(self, batch: dict) -> torch.Tensor:
        raise NotImplementedError("the variant scores node pairs; use edge_errors")
