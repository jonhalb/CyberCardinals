"""Turn one graph's rows into compact arrays. No torch here, so it is cheap to test.

Storage per edge is three type indices plus src, dst and t, not a 42-float message: the
42-dim one-hot message is rebuilt per batch with one_hot_msg(). Same information, about
50x smaller on disk (the reference pipeline stores the float matrix for all 89.8M edges).
Message layout: [source node type (8) | edge type (26) | destination node type (8)].
"""
from typing import Dict, List

import numpy as np

from kairos_repro.common import EDGE_TYPES, MSG_DIM, NODE_TYPES
from kairos_repro.data.rows import Row

NODE_INDEX = {c: i for i, c in enumerate(NODE_TYPES)}
EDGE_INDEX = {c: i for i, c in enumerate(EDGE_TYPES)}


class IdCompactor:
    """Bijective renumbering of node ids to 0..N-1 in first-seen order.

    Lossless for any computation that uses node ids only as indices (the paper-faithful
    decoder does). It shrinks the node-memory table from the reference code's fixed
    5,045,000 rows to the number of distinct nodes. See docs/decisions/ADR-0005.
    """

    def __init__(self) -> None:
        self._map: Dict[str, int] = {}

    def __call__(self, raw_id: str) -> int:
        v = self._map.get(raw_id)
        if v is None:
            v = len(self._map)
            self._map[raw_id] = v
        return v

    def __len__(self) -> int:
        return len(self._map)

    def ids_in_order(self) -> List[str]:
        return list(self._map.keys())


def encode_block(rows: List[Row], compactor: IdCompactor) -> Dict[str, np.ndarray]:
    n = len(rows)
    out = {
        "src": np.empty(n, dtype=np.int32), "dst": np.empty(n, dtype=np.int32),
        "t": np.empty(n, dtype=np.int64),
        "src_type": np.empty(n, dtype=np.int8), "dst_type": np.empty(n, dtype=np.int8),
        "edge_type": np.empty(n, dtype=np.int8),
    }
    for i, r in enumerate(rows):
        try:
            out["src_type"][i] = NODE_INDEX[r.src_type]
            out["dst_type"][i] = NODE_INDEX[r.dst_type]
            out["edge_type"][i] = EDGE_INDEX[r.edge_type]
        except KeyError as exc:
            raise ValueError("unknown type code %s at line %d" % (exc, r.line))
        out["src"][i] = compactor(r.src)
        out["dst"][i] = compactor(r.dst)
        out["t"][i] = r.line
    return out


def one_hot_msg(src_type: np.ndarray, edge_type: np.ndarray, dst_type: np.ndarray) -> np.ndarray:
    n = len(edge_type)
    msg = np.zeros((n, MSG_DIM), dtype=np.float32)
    rows = np.arange(n)
    msg[rows, src_type.astype(np.int64)] = 1.0
    msg[rows, len(NODE_TYPES) + edge_type.astype(np.int64)] = 1.0
    msg[rows, len(NODE_TYPES) + len(EDGE_TYPES) + dst_type.astype(np.int64)] = 1.0
    return msg
