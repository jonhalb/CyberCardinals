"""Tests for the scoring pass (story M3-03). Synthetic graphs only: no dataset needed."""
import numpy as np
import pytest

torch = pytest.importorskip("torch")
pytest.importorskip("torch_geometric")
from kairos_repro import common as c
from kairos_repro.eval.scores_io import read_scores
from kairos_repro.model.scoring import graph_score


def fake_graph(seed, n_edges=300, n_nodes=40):
    r = np.random.RandomState(seed)
    return {"src": r.randint(0, n_nodes, n_edges).astype(np.int32), "dst": r.randint(0, n_nodes, n_edges).astype(np.int32),
            "t": np.arange(1, n_edges + 1, dtype=np.int64),
            "src_type": r.randint(0, 8, n_edges).astype(np.int8), "dst_type": r.randint(0, 8, n_edges).astype(np.int8),
            "edge_type": r.randint(0, 26, n_edges).astype(np.int8)}


VAL, TEST = [1, 2, 3], [25, 26, 300, 301]          # real ids, so split_of() and label() apply


@pytest.fixture
def trained(tmp_path, monkeypatch):
    """A tiny trained model of each kind, with every graph load replaced by a synthetic graph."""
    import kairos_repro.model.evaluate as ev
    import kairos_repro.model.train as tr
    monkeypatch.setattr(c, "RESULTS", tmp_path)
    monkeypatch.setattr(tr, "load_graph", fake_graph)
    monkeypatch.setattr(ev, "load_graph", fake_graph)
    cfgs = {}
    for name in ("paper_faithful", "authors_variant"):
        cfgs[name] = dict(c.load_config(name), epochs=1, batch_size=100)
        tr.train(cfgs[name], seed=0, graph_ids=[0], log=lambda *_: None)
    return ev, cfgs, tmp_path


def test_score_file_threshold_and_predictions(trained):
    ev, cfgs, tmp = trained
    meta = ev.evaluate(cfgs["paper_faithful"], 0, VAL, TEST, log=lambda *_: None)
    rows = read_scores(tmp / "paper_faithful" / "graph_scores_seed0.csv")
    assert [r["graph_id"] for r in rows] == VAL + TEST
    assert [r["split"] for r in rows] == ["val"] * 3 + ["test_benign"] * 2 + ["test_attack"] * 2
    assert [r["label"] for r in rows] == [0, 0, 0, 0, 0, 1, 1]
    val_scores = [r["score"] for r in rows if r["split"] == "val"]
    assert meta["threshold"] == max(val_scores)                        # validation only sets the threshold
    assert all(r["pred"] == int(r["score"] > meta["threshold"]) for r in rows)
    assert all(r["pred"] == 0 for r in rows if r["split"] == "val")   # strictly greater: no validation graph fires
    assert meta["threshold_set_by_validation_graph"] in VAL and meta["graphs_scored"] == 7


def test_scoring_is_repeatable(trained):
    ev, cfgs, tmp = trained
    for name in ("paper_faithful", "authors_variant"):
        path = tmp / name / "graph_scores_seed0.csv"
        ev.evaluate(cfgs[name], 0, VAL, TEST, log=lambda *_: None)
        first = path.read_text()
        ev.evaluate(cfgs[name], 0, VAL, TEST, log=lambda *_: None)
        assert path.read_text() == first


def test_graph_score_rule_comes_from_the_config():
    import kairos_repro.model.evaluate as ev
    e = np.array([1.0, 1.0, 1.0, 1.0, 9.0])
    assert ev.score_from_errors(e, {"rule": "mean_loss"}) == pytest.approx(2.6)
    paper = {"rule": "mean_of_errors_above_mean_plus_sd", "sd_multiplier": 1.5, "ddof": 0}
    assert ev.score_from_errors(e, paper) == graph_score(e, 1.5, 0) == 9.0
    with pytest.raises(ValueError):
        ev.score_from_errors(e, {"rule": "something else"})
