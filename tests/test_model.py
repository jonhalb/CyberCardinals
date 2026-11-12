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


# ---- story M3-02: decoder, per-edge error, training loop ----------------------------------------

def learnable_graph(n_edges=600, seed=0):
    """Edge type is a fixed function of the source node type, so a working model can learn it."""
    g = synth_graph(n_edges=n_edges, seed=seed)
    g["src_type"] = (g["src"] % 8).astype(np.int8)      # like real data: a node keeps one type
    g["dst_type"] = (g["dst"] % 8).astype(np.int8)
    g["edge_type"] = (g["src_type"].astype(np.int64) * 3 % 26).astype(np.int8)
    return g


def test_edge_errors_one_per_edge_and_no_leak():
    g1, g2 = synth_graph(), synth_graph()
    g2["edge_type"] = g2["edge_type"].copy()
    g2["edge_type"][150:200] = (g2["edge_type"][150:200] + 1) % 26
    model = make_model()

    def errs(g):
        model.start_graph(g)
        out = []
        with torch.no_grad():
            for b in batches(g, 50):
                out.append(model.edge_errors(b))
                model.advance(b)
        return out
    a, b = errs(g1), errs(g2)
    assert [tuple(e.shape) for e in a] == [(50,)] * 6 and all((e >= 0).all() for e in a)
    assert torch.equal(a[2], b[2])         # earlier batch: identical
    assert not torch.equal(a[3], b[3])     # batch 3's error changes only because its TARGET changed


def test_training_lowers_the_loss():
    from kairos_repro.model.train import train_one_graph
    torch.manual_seed(0)
    cfg = dict(c.load_config("paper_faithful"), lr=1e-2)
    model = PaperFaithfulKairos(cfg, num_nodes=64)
    opt = torch.optim.Adam(model.parameters(), lr=cfg["lr"])
    g = learnable_graph()
    losses = []
    for _ in range(8):
        seen, total = train_one_graph(model, opt, g, batch_size=100)
        losses.append(total / seen)
    assert seen == 600
    assert losses[-1] < 0.5 * losses[0], losses


def test_train_writes_files_and_reloads(tmp_path, monkeypatch):
    import kairos_repro.model.train as tr
    fake = {0: learnable_graph(seed=0), 100: learnable_graph(seed=1)}
    monkeypatch.setattr(tr, "load_graph", lambda gid: {k: v for k, v in fake[gid].items() if k != "num_nodes"})
    monkeypatch.setattr(c, "RESULTS", tmp_path)
    cfg = dict(c.load_config("paper_faithful"), epochs=2, batch_size=100)
    meta = tr.train(cfg, seed=0, graph_ids=[0, 100], log=lambda *_: None)
    out = tmp_path / "paper_faithful"
    assert (out / "model_seed0.pt").exists() and (out / "train_meta_seed0.json").exists()
    log = (out / "train_log_seed0.csv").read_text().splitlines()
    assert log[0] == "epoch,graph_id,edges,mean_loss,seconds" and len(log) == 1 + 2 * 3
    assert meta["epochs"] == 2 and meta["quick"] is False and meta["train_graphs"] == [0, 100]
    # the saved model reproduces the trained model's errors exactly (what evaluate.py relies on)
    m1 = tr.load_trained(cfg, 0)
    m2 = tr.load_trained(cfg, 0)
    g = fake[0]
    for m in (m1, m2):
        m.start_graph(g)
    with torch.no_grad():
        b = next(batches(g, 100))
        assert torch.equal(m1.edge_errors(b), m2.edge_errors(b))


def test_same_seed_same_training():
    import kairos_repro.model.train as tr
    g = learnable_graph()
    runs = []
    for _ in range(2):
        c.seed_everything(3)
        model = PaperFaithfulKairos(c.load_config("paper_faithful"), num_nodes=64)
        opt = torch.optim.Adam(model.parameters(), lr=1e-3)
        runs.append(tr.train_one_graph(model, opt, g, batch_size=100))
    assert runs[0] == runs[1]
