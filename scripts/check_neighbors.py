"""Measure how often each neighbour sampler keeps the WRONG "most recent N" neighbours (story M3-04, D-26).

    python scripts/check_neighbors.py 0 100 300            # graph ids; needs `make data graphs`
    python scripts/check_neighbors.py 0 --batch-size 1024 --size 20

For every batch it replays a real graph through PyG's LastNeighborLoader and through our
RecentNeighbors, and compares both with the exact answer: for each node touched by the batch, the
ids of the last N edges (in file order) that touch it. Prints one line per graph and sampler.
"""
import argparse
import time
from collections import defaultdict, deque

import numpy as np
import torch
from torch_geometric.nn.models.tgn import LastNeighborLoader

from kairos_repro.data.loading import batches, load_graph, localize
from kairos_repro.data.neighbors import RecentNeighbors


def check(gid: int, size: int, batch_size: int) -> None:
    g = localize(load_graph(gid))
    n = int(g["num_nodes"])
    samplers = {"pyg LastNeighborLoader": LastNeighborLoader(n, size=size),
                "ours RecentNeighbors": RecentNeighbors(n, size=size)}
    truth = defaultdict(lambda: deque(maxlen=size))
    wrong = {k: 0 for k in samplers}
    missing = {k: 0 for k in samplers}
    seconds = {k: 0.0 for k in samplers}
    checks, e = 0, 0
    for b in batches(g, batch_size):
        src = torch.from_numpy(b["src"]).long()
        dst = torch.from_numpy(b["dst"]).long()
        for name, s in samplers.items():
            t0 = time.perf_counter()
            s.insert(src, dst)
            seconds[name] += time.perf_counter() - t0
        for u, v in zip(b["src"].tolist(), b["dst"].tolist()):
            truth[u].append(e)
            truth[v].append(e)
            e += 1
        nodes = np.unique(np.concatenate([b["src"], b["dst"]]))
        for node in nodes.tolist():
            want = set(truth[node])
            checks += 1
            for name, s in samplers.items():
                have = set(x for x in s.e_id[node].tolist() if x >= 0)
                if have != want:
                    wrong[name] += 1
                    missing[name] += len(want - have)
    for name in samplers:
        print("graph %3d  %-24s wrong node updates %6d / %6d (%5.2f%%)  recent edges missing %7d  insert time %.2f s"
              % (gid, name, wrong[name], checks, 100.0 * wrong[name] / max(checks, 1), missing[name], seconds[name]))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("graphs", nargs="+", type=int)
    ap.add_argument("--size", type=int, default=20)
    ap.add_argument("--batch-size", type=int, default=1024)
    a = ap.parse_args()
    for gid in a.graphs:
        check(gid, a.size, a.batch_size)


if __name__ == "__main__":
    main()
