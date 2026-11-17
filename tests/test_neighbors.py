"""Story M3-04: the chronological batch loader and the recent-neighbour sampler.

Acceptance: "Loader tested for ordering and for no leakage of the current edge."
Synthetic graphs (no dataset needed), plus one real-graph check that skips without data.
"""
from collections import defaultdict, deque

import numpy as np
import pytest

torch = pytest.importorskip("torch")
pytest.importorskip("torch_geometric")
from torch_geometric.nn.models.tgn import LastNeighborLoader

from kairos_repro import common as c
from kairos_repro.data.loading import batches, load_graph, localize
from kairos_repro.data.neighbors import RecentNeighbors

SIZE = 20


def hub_graph(n_edges=3000, n_nodes=60, seed=0, hub_share=0.4):
    """Random graph where node 0 is a busy process: a big share of edges touch it, often in long
    runs, like the reads and writes of one process in StreamSpot. Includes some self-loops."""
    r = np.random.RandomState(seed)
    src = r.randint(0, n_nodes, n_edges)
    dst = r.randint(0, n_nodes, n_edges)
    hub = r.rand(n_edges) < hub_share
    src[hub] = 0
    src[100:160] = 0                       # a run of 60 edges at node 0 inside one batch
    dst[5:15] = src[5:15]                  # self-loops
    return localize({"src": src.astype(np.int32), "dst": dst.astype(np.int32),
                     "t": np.arange(1, n_edges + 1, dtype=np.int64),
                     "src_type": r.randint(0, 8, n_edges).astype(np.int8),
                     "dst_type": r.randint(0, 8, n_edges).astype(np.int8),
                     "edge_type": r.randint(0, 26, n_edges).astype(np.int8)})


def exact_recent(g, upto, size=SIZE):
    """Brute force: for every node, the ids of its last `size` edges among edges 0..upto-1."""
    recent = defaultdict(lambda: deque(maxlen=size))
    for e in range(upto):
        recent[int(g["src"][e])].append(e)
        recent[int(g["dst"][e])].append(e)
    return recent


def as_tensors(b):
    return torch.from_numpy(b["src"]).long(), torch.from_numpy(b["dst"]).long()


# ---- the batch loader: time order -----------------------------------------------------------------

@pytest.mark.parametrize("batch_size", [1, 7, 50, 1024, 5000])
def test_batches_cover_every_edge_once_in_file_order(batch_size):
    g = hub_graph()
    bs = list(batches(g, batch_size))
    t = np.concatenate([b["t"] for b in bs])
    assert (t == g["t"]).all()                          # never shuffled, nothing lost or repeated
    assert all((np.diff(b["t"]) > 0).all() for b in bs)
    assert all(bs[i]["t"][-1] < bs[i + 1]["t"][0] for i in range(len(bs) - 1))   # batch k+1 is later
    assert [len(b["t"]) for b in bs[:-1]] == [batch_size] * (len(bs) - 1)
    assert all(b["msg"].shape == (len(b["t"]), c.MSG_DIM) for b in bs)


def test_batches_keep_fields_aligned():
    g = hub_graph()
    for b in batches(g, 64):
        idx = b["t"] - 1                                  # t is 1-based position here
        for k in ("src", "dst", "src_type", "dst_type", "edge_type"):
            assert (b[k] == g[k][idx]).all()


# ---- the neighbour sampler: exactly the most recent N ---------------------------------------------

@pytest.mark.parametrize("batch_size", [1, 13, 256, 1024])
def test_sampler_keeps_exactly_the_most_recent(batch_size):
    g = hub_graph()
    nb = RecentNeighbors(int(g["num_nodes"]), SIZE)
    done = 0
    for b in batches(g, batch_size):
        nb.insert(*as_tensors(b))
        done += len(b["t"])
        truth = exact_recent(g, done)
        for node in np.unique(np.concatenate([b["src"], b["dst"]])).tolist():
            assert sorted(nb.recent(node)) == sorted(truth[node]), "node %d after %d edges" % (node, done)


def test_sampler_neighbours_are_the_other_endpoint():
    g = hub_graph()
    nb = RecentNeighbors(int(g["num_nodes"]), SIZE)
    for b in batches(g, 100):
        nb.insert(*as_tensors(b))
    for node in range(int(g["num_nodes"])):
        for slot in range(SIZE):
            e = int(nb.e_id[node, slot])
            if e < 0:
                continue
            u, v = int(g["src"][e]), int(g["dst"][e])
            assert node in (u, v)
            assert int(nb.neighbors[node, slot]) == (v if node == u else u)


def test_long_run_in_one_batch_regression():
    """30 edges at node 0 in one batch: the 20 kept must be edges 10..29. PyG 2.0.0 keeps an old one."""
    src, dst = torch.zeros(30, dtype=torch.long), torch.arange(1, 31)
    ours = RecentNeighbors(40, SIZE)
    ours.insert(src, dst)
    assert sorted(ours.recent(0)) == list(range(10, 30))
    assert sorted(ours.recent(5)) == [4]                     # the other endpoint sees the edge too
    pyg = LastNeighborLoader(40, size=SIZE)
    pyg.insert(src, dst)
    assert sorted(pyg.e_id[0].tolist()) != list(range(10, 30))   # documents D-26; if PyG is fixed, drop this line


def test_matches_pyg_when_no_node_overflows_a_batch():
    """With one edge per batch PyG's loader is correct, and ours must give the same output."""
    g = hub_graph(n_edges=400)
    n = int(g["num_nodes"])
    ours, pyg = RecentNeighbors(n, SIZE), LastNeighborLoader(n, size=SIZE)
    for b in batches(g, 1):
        s, d = as_tensors(b)
        ours.insert(s, d)
        pyg.insert(s, d)
    q = torch.arange(n)
    a, b = ours(q), pyg(q)
    assert torch.equal(a[0], b[0])
    key = lambda out: sorted(zip(out[2].tolist(), out[1][0].tolist(), out[1][1].tolist()))
    assert key(a) == key(b)


def test_query_output_is_well_formed():
    g = hub_graph()
    nb = RecentNeighbors(int(g["num_nodes"]), SIZE)
    for b in batches(g, 500):
        nb.insert(*as_tensors(b))
    q = torch.tensor([0, 3, 7])
    n_id, edge_index, e_id = nb(q)
    assert set(q.tolist()) <= set(n_id.tolist())
    assert edge_index.shape == (2, e_id.numel())
    assert edge_index.max() < n_id.numel()
    # edge_index[1] points at the queried node, edge_index[0] at the neighbour on that past edge
    for (nbr, node), e in zip(edge_index.t().tolist(), e_id.tolist()):
        assert int(n_id[node]) in q.tolist()
        assert {int(n_id[node]), int(n_id[nbr])} <= {int(g["src"][e]), int(g["dst"][e])}


# ---- no leakage of the current edge ---------------------------------------------------------------

@pytest.mark.parametrize("batch_size", [1, 64, 1024])
def test_no_leak_neighbourhood_only_holds_past_edges(batch_size):
    """Queried before insert(), a batch's neighbourhood holds only edges strictly before the batch:
    the edge being predicted (and the rest of its batch) is never visible to itself."""
    g = hub_graph()
    nb = RecentNeighbors(int(g["num_nodes"]), SIZE)
    start = 0
    for b in batches(g, batch_size):
        nodes = torch.from_numpy(np.unique(np.concatenate([b["src"], b["dst"]]))).long()
        _, _, e_id = nb(nodes)
        if e_id.numel():
            assert int(e_id.max()) < start
            assert (g["t"][e_id.numpy()] < b["t"][0]).all()
        nb.insert(*as_tensors(b))
        start += len(b["t"])


def test_reset_forgets_the_previous_graph():
    g = hub_graph()
    nb = RecentNeighbors(int(g["num_nodes"]), SIZE)
    for b in batches(g, 256):
        nb.insert(*as_tensors(b))
    nb.reset_state()
    assert nb.cur_e_id == 0 and (nb.e_id == -1).all()
    _, edge_index, e_id = nb(torch.arange(int(g["num_nodes"])))
    assert e_id.numel() == 0 and edge_index.shape == (2, 0)


# ---- real data (skips without `make data graphs`) -------------------------------------------------

@pytest.mark.skipif(not c.graph_path(100).exists(), reason="no processed graphs: run `make data graphs`")
def test_real_graph_exact_with_paper_batch_size():
    g = localize(load_graph(100))                       # Gmail graph, 42,483 edges
    nb = RecentNeighbors(int(g["num_nodes"]), SIZE)
    truth = defaultdict(lambda: deque(maxlen=SIZE))
    e = 0
    for b in batches(g, 1024):
        nb.insert(*as_tensors(b))
        for u, v in zip(b["src"].tolist(), b["dst"].tolist()):
            truth[u].append(e)
            truth[v].append(e)
            e += 1
        for node in np.unique(np.concatenate([b["src"], b["dst"]])).tolist():
            assert sorted(nb.recent(node)) == sorted(truth[node])
