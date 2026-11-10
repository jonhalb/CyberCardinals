"""Build data/processed/graph_{id}.npz for all 600 graphs, without PostgreSQL.

    python -m kairos_repro.data.build_graphs

Per graph: src, dst (compacted ids), t (1-based file line), src_type, dst_type, edge_type.
Also writes data/processed/manifest.json (edges per graph, node count) which the tests and
the data report check against the expected totals.
"""
import json
import sys
from pathlib import Path
from typing import Dict, Iterable, Optional

import numpy as np

from kairos_repro import common as c
from kairos_repro.data.graph_encoding import IdCompactor, encode_block
from kairos_repro.data.rows import iter_graph_blocks


def build_from_lines(lines: Iterable[str], out_dir: Path) -> Dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    compactor = IdCompactor()
    edges: Dict[int, int] = {}
    for gid, block in iter_graph_blocks(lines):
        arrays = encode_block(block, compactor)
        np.savez_compressed(out_dir / ("graph_%d.npz" % gid), **arrays)
        edges[gid] = len(block)
    manifest = {"graphs": len(edges), "total_edges": sum(edges.values()),
                "compacted_nodes": len(compactor), "edges_per_graph": edges}
    (out_dir / "manifest.json").write_text(json.dumps(manifest))
    return manifest


def main() -> int:
    if not c.RAW_TSV.exists():
        print("missing %s: run `make data` first" % c.RAW_TSV)
        return 1
    with open(c.RAW_TSV, "r") as fh:
        m = build_from_lines(fh, c.PROCESSED_DIR)
    print("graphs=%d edges=%d compacted_nodes=%d" % (m["graphs"], m["total_edges"], m["compacted_nodes"]))
    if m["graphs"] != c.NUM_GRAPHS or m["total_edges"] != c.TOTAL_EDGES:
        print("WARNING: expected %d graphs and %d edges" % (c.NUM_GRAPHS, c.TOTAL_EDGES))
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
