"""Tests for the model's encoder (story M3-01). Synthetic graphs only: no dataset needed."""
import numpy as np
import pytest

torch = pytest.importorskip("torch")
pytest.importorskip("torch_geometric")
from kairos_repro import common as c
from kairos_repro.data.loading import batches, localize
from kairos_repro.model.paper_faithful import PaperFaithfulKairos


def synth_graph(n_edges=300, n_nodes=40, seed=0):
    r = np.random.RandomState(seed)
    return localize({
        "src": r.randint(0, n_nodes, n_edges).astype(np.int32), "dst": r.randint(0, n_nodes, n_edges).astype(np.int32),
        "t": np.arange(1, n_edges + 1, dtype=np.int64),
        "src_type": r.randint(0, 8, n_edges).astype(np.int8), "dst_type": r.randint(0, 8, n_edges).astype(np.int8),
        "edge_type": r.randint(0, 26, n_edges).astype(np.int8)})


def run(model, graph, batch_size=50):
    model.start_graph(graph)
    out = []
    for b in batches(graph, batch_size):
        out.append(model.edge_embeddings(b))
        model.advance(b)
    return out


def make_model():
    torch.manual_seed(0)
    return PaperFaithfulKairos(c.load_config("paper_faithful"), num_nodes=64).eval()


def test_forward_pass_shape():
    cfg = c.load_config("paper_faithful")
    out = run(make_model(), synth_graph())
    assert [tuple(z.shape) for z in out] == [(50, cfg["edge_embedding_dim"])] * 6
    assert all(torch.isfinite(z).all() for z in out)
    assert not torch.allclose(out[0], out[-1][:50])          # the memory changes what the model sees


def test_no_leak_of_the_edge_being_predicted():
    g1, g2 = synth_graph(), synth_graph()
    g2["edge_type"] = g2["edge_type"].copy()
    g2["edge_type"][150:200] = (g2["edge_type"][150:200] + 1) % 26   # change only batch 3's edge types
    model = make_model()
    with torch.no_grad():
        a, b = run(model, g1), run(model, g2)
    assert torch.equal(a[3], b[3])            # batch 3's embeddings cannot see batch 3's own edge types
    assert not torch.equal(a[4], b[4])        # but later batches do see them, as part of the past


def test_memory_is_reset_between_graphs():
    model, g = make_model(), synth_graph()
    with torch.no_grad():
        first = run(model, g)
        run(model, synth_graph(seed=1))
        again = run(model, g)
    assert all(torch.equal(x, y) for x, y in zip(first, again))


def test_graph_too_big_is_refused():
    with pytest.raises(ValueError):
        make_model().start_graph(synth_graph(n_nodes=200, n_edges=2000))
