"""Exact "most recent N neighbours" for each node. OWNER: Emiliano (story M3-04).

The paper builds each node's embedding from its most recent neighbours (Sec. 4.2; |N| = 20, Sec. 5).
PyG 2.0.0's LastNeighborLoader, which the reference code uses, gets this wrong whenever one node takes
part in more than N edges of the same batch. It places the batch's edges by their position in the
whole batch modulo N instead of by their position among that node's own edges, so entries overwrite
each other in whatever order the (unstable) sort left them, and an old edge can survive while a recent
one is dropped. With 1,024-edge batches this happens a lot on provenance graphs, where one process
reads or writes hundreds of times in a row: on graph 0, 14% of the node updates keep a wrong
neighbour set (deviation D-26; scripts/check_neighbors.py measures it on any graph).

RecentNeighbors has the same interface and returns the same kind of output, so it is a drop-in
replacement:

    nb = RecentNeighbors(num_nodes, size=20)
    n_id, edge_index, e_id = nb(nodes)   # nodes + their recent neighbours, edges neighbour -> node
    nb.insert(src, dst)                  # after the batch was predicted: its edges join the past
    nb.reset_state()                     # new graph

Edge ids count the edges inserted since the last reset, so e_id indexes the graph's arrays directly
(the model uses graph["t"][e_id] and the edge types). An edge is a neighbour of BOTH its endpoints
(undirected, as in the reference); a self-loop is listed twice for its node, as in the reference.
No leakage by construction: a batch's own edges only appear after insert() is called for it.
"""
from typing import Tuple

import torch
from torch import Tensor


class RecentNeighbors:
    def __init__(self, num_nodes: int, size: int, device=None):
        self.size = size
        self.num_nodes = num_nodes
        self.neighbors = torch.empty((num_nodes, size), dtype=torch.long, device=device)
        self.e_id = torch.empty((num_nodes, size), dtype=torch.long, device=device)
        self._assoc = torch.empty(num_nodes, dtype=torch.long, device=device)
        self.reset_state()

    def reset_state(self) -> None:
        self.cur_e_id = 0
        self.e_id.fill_(-1)
        self.neighbors.fill_(-1)

    def __call__(self, n_id: Tensor) -> Tuple[Tensor, Tensor, Tensor]:
        """For the given (unique) nodes: all nodes involved, edge_index [neighbour, node] in that
        relabelled numbering, and the id of the past edge behind each pair. Same as PyG's."""
        neighbors = self.neighbors[n_id]
        nodes = n_id.view(-1, 1).repeat(1, self.size)
        e_id = self.e_id[n_id]
        mask = e_id >= 0
        neighbors, nodes, e_id = neighbors[mask], nodes[mask], e_id[mask]
        n_id = torch.cat([n_id, neighbors]).unique()
        self._assoc[n_id] = torch.arange(n_id.size(0), device=n_id.device)
        neighbors, nodes = self._assoc[neighbors], self._assoc[nodes]
        return n_id, torch.stack([neighbors, nodes]), e_id

    def insert(self, src: Tensor, dst: Tensor) -> None:
        """Add a batch of edges, given in time order. Afterwards every node keeps exactly its
        `size` most recent edges (largest edge ids), counting edges from earlier batches too."""
        n = src.numel()
        if n == 0:
            return
        size = self.size
        # Each edge is a neighbour entry for both endpoints.
        nodes = torch.cat([dst, src])
        neighbors = torch.cat([src, dst])
        e_id = torch.arange(self.cur_e_id, self.cur_e_id + n, device=src.device).repeat(2)
        self.cur_e_id += n

        # Sort by (node, edge id). Keys are unique except for a self-loop's two copies, which are
        # identical anyway, so the result does not depend on sort stability (PyG's does).
        order = torch.argsort(nodes * (self.cur_e_id + 1) + e_id)
        nodes, neighbors, e_id = nodes[order], neighbors[order], e_id[order]

        # Rank of each entry counted from the END of its node's group: 0 = most recent.
        uniq, counts = torch.unique_consecutive(nodes, return_counts=True)
        group_end = torch.cumsum(counts, 0).repeat_interleave(counts)
        from_end = group_end - 1 - torch.arange(nodes.numel(), device=nodes.device)
        keep = from_end < size                      # at most `size` new entries per node
        nodes, neighbors, e_id, from_end = nodes[keep], neighbors[keep], e_id[keep], from_end[keep]

        # Dense [node, size] block of the new entries (-1 = empty), one row per touched node.
        self._assoc[uniq] = torch.arange(uniq.numel(), device=uniq.device)
        slot = self._assoc[nodes] * size + from_end
        new_e = e_id.new_full((uniq.numel() * size,), -1)
        new_n = e_id.new_full((uniq.numel() * size,), -1)
        new_e[slot] = e_id
        new_n[slot] = neighbors

        # Old entries + new entries; keep the `size` largest edge ids (= most recent).
        all_e = torch.cat([self.e_id[uniq], new_e.view(-1, size)], dim=-1)
        all_n = torch.cat([self.neighbors[uniq], new_n.view(-1, size)], dim=-1)
        top_e, perm = all_e.topk(size, dim=-1)
        self.e_id[uniq] = top_e
        self.neighbors[uniq] = torch.gather(all_n, 1, perm)

    def recent(self, node: int):
        """The node's recent edge ids, newest first (for tests and debugging)."""
        return [x for x in self.e_id[node].tolist() if x >= 0]
