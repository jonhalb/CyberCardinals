"""Story M2-04: tests on the REAL processed graphs and manifest, so the data pipeline cannot drift.

These need `make data graphs` first. On a clean checkout without data/processed they skip,
so `make unit` still passes everywhere; on a machine with the data they check the real thing.

What they pin down (numbers from results/data_report.md and docs/verification_2026-11-09.md):
- manifest: 600 graphs, 89,770,902 edges, per-graph counts that add up, 5,044,482 distinct node ids;
- t is the GLOBAL 1-based line number of all.tsv: it starts at 1, has no gaps inside a graph, and
  continues from one graph to the next (no per-graph restart). This is ADR-0002's t-offset evidence;
- each graph's arrays have the stored dtypes and in-range type codes, and all 8 node types and all
  26 edge types appear;
- attack edges (graphs 300-399) total 2,842,345, as in paper Table 2;
- localize() is lossless on a real graph;
- if data/raw/all.tsv is present, the first rows of the file re-encode to exactly what is stored.
"""
import json
from itertools import islice

import numpy as np
import pytest

from kairos_repro import common as c
from kairos_repro.data.graph_encoding import EDGE_INDEX, NODE_INDEX
from kairos_repro.data.loading import load_graph, localize
from kairos_repro.data.rows import parse_line

MANIFEST = c.PROCESSED_DIR / "manifest.json"
EXPECTED_DISTINCT_NODES = 5_044_482  # results/data_report.md, Totals table
EXPECTED_ATTACK_EDGES = c.PAPER_TABLE2["attack_edges"]  # 2,842,345: ours matches the paper exactly

needs_graphs = pytest.mark.skipif(not MANIFEST.exists(),
                                  reason="no data/processed/manifest.json: run `make data graphs` first")
needs_raw = pytest.mark.skipif(not (MANIFEST.exists() and c.RAW_TSV.exists()),
                               reason="no data/raw/all.tsv: run `make data` first")


@pytest.fixture(scope="module")
def manifest():
    m = json.loads(MANIFEST.read_text())
    m["edges_per_graph"] = {int(k): v for k, v in m["edges_per_graph"].items()}
    return m


@pytest.fixture(scope="module")
def scan(manifest):
    """One pass over all 600 graphs, reading only t and the type columns (about 30 s)."""
    first_t, last_t, n_edges = {}, {}, {}
    node_types, edge_types = set(), set()
    contiguous = []
    for gid in range(c.NUM_GRAPHS):
        with np.load(c.graph_path(gid)) as z:
            t = z["t"]
            node_types.update(np.unique(z["src_type"]).tolist())
            node_types.update(np.unique(z["dst_type"]).tolist())
            edge_types.update(np.unique(z["edge_type"]).tolist())
        first_t[gid], last_t[gid], n_edges[gid] = int(t[0]), int(t[-1]), len(t)
        if not (np.diff(t) == 1).all():
            contiguous.append(gid)
    return {"first_t": first_t, "last_t": last_t, "n_edges": n_edges, "not_contiguous": contiguous,
            "node_types": node_types, "edge_types": edge_types}


@needs_graphs
def test_manifest_totals(manifest):
    assert manifest["graphs"] == c.NUM_GRAPHS
    assert manifest["total_edges"] == c.TOTAL_EDGES
    assert sorted(manifest["edges_per_graph"]) == list(range(c.NUM_GRAPHS))
    assert sum(manifest["edges_per_graph"].values()) == c.TOTAL_EDGES
    assert manifest["compacted_nodes"] == EXPECTED_DISTINCT_NODES


@needs_graphs
def test_manifest_matches_files(manifest, scan):
    assert scan["n_edges"] == manifest["edges_per_graph"]


@needs_graphs
def test_attack_edges_match_paper_table2(manifest):
    attack = sum(manifest["edges_per_graph"][g] for g in c.TEST_ATTACK_IDS)
    assert attack == EXPECTED_ATTACK_EDGES


@needs_graphs
def test_t_is_global_line_number(scan):
    """ADR-0002: t = 1-based line in all.tsv, the same as the authors' serial `_id`."""
    assert scan["not_contiguous"] == [], "t has gaps or goes backwards inside these graphs"
    assert scan["first_t"][0] == 1
    for gid in range(1, c.NUM_GRAPHS):
        assert scan["first_t"][gid] == scan["last_t"][gid - 1] + 1, "graph %d does not continue the line count" % gid
    assert scan["last_t"][c.NUM_GRAPHS - 1] == c.TOTAL_EDGES  # no blank or malformed lines anywhere


@needs_graphs
def test_all_type_codes_present(scan):
    assert scan["node_types"] == set(range(len(c.NODE_TYPES)))
    assert scan["edge_types"] == set(range(len(c.EDGE_TYPES)))


@needs_graphs
@pytest.mark.parametrize("gid", [0, 100, 200, 300, 400, 500, 599])
def test_sample_graph_arrays(gid):
    g = load_graph(gid)
    assert set(g) == {"src", "dst", "t", "src_type", "dst_type", "edge_type"}
    assert g["src"].dtype == np.int32 and g["dst"].dtype == np.int32 and g["t"].dtype == np.int64
    n = len(g["t"])
    assert all(len(v) == n for v in g.values())
    assert g["src"].min() >= 0 and g["dst"].min() >= 0
    assert g["edge_type"].min() >= 0 and g["edge_type"].max() < len(c.EDGE_TYPES)


@needs_graphs
@pytest.mark.parametrize("gid", [0, 300])
def test_localize_is_lossless_on_real_graph(gid):
    g = load_graph(gid)
    loc = localize(g)
    n_nodes = len(np.unique(np.concatenate([g["src"], g["dst"]])))
    assert loc["num_nodes"] == n_nodes
    assert loc["src"].min() == 0 or loc["dst"].min() == 0
    assert max(loc["src"].max(), loc["dst"].max()) == n_nodes - 1
    # the renumbering is a bijection: local -> global is a function, and so is global -> local
    glob = np.concatenate([g["src"], g["dst"]])
    locl = np.concatenate([loc["src"], loc["dst"]])
    pairs = np.unique(np.stack([locl, glob]), axis=1)
    assert pairs.shape[1] == n_nodes
    for k in ("t", "src_type", "dst_type", "edge_type"):
        assert (loc[k] == g[k]).all()


@needs_raw
def test_first_rows_of_raw_file_match_graph_0():
    """Re-read the start of all.tsv and check it encodes to what graph_0.npz stores."""
    g = load_graph(0)
    k = 5000
    with open(c.RAW_TSV) as fh:
        rows = [parse_line(line) for line in islice(fh, k)]
    assert all(r is not None and r[5] == 0 for r in rows)
    assert (g["t"][:k] == np.arange(1, k + 1)).all()
    assert [NODE_INDEX[r[1]] for r in rows] == g["src_type"][:k].tolist()
    assert [EDGE_INDEX[r[4]] for r in rows] == g["edge_type"][:k].tolist()
    assert [NODE_INDEX[r[3]] for r in rows] == g["dst_type"][:k].tolist()
    # compacted ids are first-seen order, so equal raw ids <=> equal stored ids
    raw_ids = [r[0] for r in rows] + [r[2] for r in rows]
    stored = np.concatenate([g["src"][:k], g["dst"][:k]]).tolist()
    assert len(set(zip(raw_ids, stored))) == len(set(raw_ids)) == len(set(stored))
