"""Load processed graphs and iterate them chronologically in batches."""
from typing import Dict, Iterator, List

import numpy as np

from kairos_repro.common import graph_path
from kairos_repro.data.graph_encoding import one_hot_msg


def load_graph(graph_id: int) -> Dict[str, np.ndarray]:
    with np.load(graph_path(graph_id)) as z:
        return {k: z[k] for k in z.files}


def merge_graphs(graphs: List[Dict[str, np.ndarray]]) -> Dict[str, np.ndarray]:
    """Concatenate graphs in the order given and re-sort by t (training merges 5 graphs)."""
    merged = {k: np.concatenate([g[k] for g in graphs]) for k in graphs[0]}
    order = np.argsort(merged["t"], kind="stable")
    return {k: v[order] for k, v in merged.items()}


def batches(graph: Dict[str, np.ndarray], batch_size: int) -> Iterator[Dict[str, np.ndarray]]:
    """Chronological batches. Never shuffle: time order is part of the method."""
    n = len(graph["t"])
    for s in range(0, n, batch_size):
        sl = slice(s, min(s + batch_size, n))
        b = {k: v[sl] for k, v in graph.items()}
        b["msg"] = one_hot_msg(b["src_type"], b["edge_type"], b["dst_type"])
        yield b
