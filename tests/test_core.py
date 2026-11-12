import csv, gzip, hashlib, io, json, subprocess, sys, tarfile
from pathlib import Path
import numpy as np
import pytest
from kairos_repro import common as c
from kairos_repro.eval import metrics, compare
from kairos_repro.eval.scores_io import write_scores, read_scores
from kairos_repro.model.scoring import graph_score, fit_threshold, predict
from kairos_repro.data.rows import iter_graph_blocks
from kairos_repro.data.graph_encoding import IdCompactor, encode_block, one_hot_msg
from kairos_repro.data import stats, build_graphs, download
from kairos_repro.baselines import do_nothing, histogram_distance

ROOT = Path(__file__).resolve().parents[1]


def synth_lines(n_graphs=600, per=6):
    out = []
    for g in range(n_graphs):
        for i in range(per):
            et = c.EDGE_TYPES[i % 3] if c.label(g) == 0 else c.EDGE_TYPES[10 + i % 3]
            out.append("%d\ta\t%d\tb\t%s\t%d\n" % (i, i + 1 + (g % 3), et, g))
    return out


def test_splits():
    assert len(c.TRAIN_IDS) == 5 and len(c.VAL_IDS) == 120
    assert len(c.TEST_BENIGN_IDS) == 375 and len(c.TEST_ATTACK_IDS) == 100
    sets = [set(c.TRAIN_IDS), set(c.VAL_IDS), set(c.TEST_IDS)]
    assert not (sets[0] & sets[1]) and not (sets[0] & sets[2]) and not (sets[1] & sets[2])
    assert all(c.label(g) == 1 for g in c.TEST_ATTACK_IDS)
    assert sum(c.label(g) for g in c.VAL_IDS + c.TRAIN_IDS) == 0
    assert c.split_of(300) == "test_attack" and c.split_of(0) == "train"
    assert c.scenario_of(399) == "drive_by_download"
    with pytest.raises(ValueError):
        c.split_of(600)
    assert c.MSG_DIM == 42 and len(c.EDGE_TYPES) == 26


def test_metrics():
    m = metrics.summarize([1, 1, 0, 0], [1, 0, 0, 1])
    assert (m["TP"], m["FN"], m["TN"], m["FP"]) == (1, 1, 1, 1)
    assert m["precision"] == 0.5 and m["accuracy"] == 0.5
    assert metrics.auc_from_scores([0, 0, 1, 1], [0.1, 0.2, 0.3, 0.4]) == 1.0
    assert metrics.auc_from_scores([0, 1], [0.5, 0.5]) == 0.5
    assert metrics.auc_from_scores([0, 0, 1, 1], [0.4, 0.3, 0.2, 0.1]) == 0.0


def test_scoring():
    assert graph_score([1, 1, 1]) == 1.0
    errs = [0.0] * 99 + [10.0]
    assert graph_score(errs) == 10.0
    assert fit_threshold([1, 5, 3]) == 5.0
    assert predict([5, 5.1], 5.0) == [0, 1]
    with pytest.raises(ValueError):
        graph_score([])


def test_do_nothing_and_compare(tmp_path):
    write_scores(tmp_path / "graph_scores_seed0.csv", do_nothing.rows())
    m = compare.metrics_from_rows(read_scores(tmp_path / "graph_scores_seed0.csv"))
    assert (m["TP"], m["TN"], m["FP"], m["FN"]) == (0, 375, 0, 100)
    assert abs(m["accuracy"] - 375 / 475) < 1e-12
    md = compare.to_markdown(compare.comparison_rows(c.PAPER_TABLE4, m), "x")
    assert "Difference" in md and "-100" in md


def test_blocks_and_stats_and_baseline(tmp_path):
    lines = synth_lines()
    blocks = list(iter_graph_blocks(lines))
    assert len(blocks) == 600 and blocks[0][1][0].line == 1
    with pytest.raises(ValueError):
        list(iter_graph_blocks(["0\ta\t1\tb\tA\t0\n", "0\ta\t1\tb\tA\t1\n", "0\ta\t1\tb\tA\t0\n"]))
    rep = stats.new_report()
    feats = list(stats.stream_graph_features(lines, rep))
    assert len(feats) == 600 and rep["rows"] == 3600 and not rep["unknown_edge_types"]
    p = tmp_path / "f.csv"
    stats.write_features(p, feats)
    back = stats.read_features(p)
    rows = histogram_distance.run(back)
    preds = {r["graph_id"]: r["pred"] for r in rows}
    assert all(preds[g] == 1 for g in c.TEST_ATTACK_IDS)
    assert sum(preds[g] for g in c.TEST_BENIGN_IDS) == 0


def test_encoding_and_build(tmp_path):
    lines = synth_lines(3)
    man = build_graphs.build_from_lines(lines, tmp_path)
    assert man["graphs"] == 3 and man["total_edges"] == 18
    d = np.load(tmp_path / "graph_0.npz")
    assert d["t"][0] == 1 and d["src"].dtype == np.int32
    msg = one_hot_msg(d["src_type"], d["edge_type"], d["dst_type"])
    assert msg.shape == (6, 42) and (msg.sum(1) == 3).all()
    comp = IdCompactor()
    assert [comp("x"), comp("y"), comp("x")] == [0, 1, 0]
    from kairos_repro.data.rows import Row
    with pytest.raises(ValueError):
        encode_block([Row(1, "1", "z", "2", "a", "A")], IdCompactor())


def test_download(tmp_path):
    tsv = tmp_path / "src" / "all.tsv"
    tsv.parent.mkdir()
    tsv.write_text("".join(synth_lines(2)))
    arc = tmp_path / "a.tar.gz"
    with tarfile.open(arc, "w:gz") as t:
        t.add(tsv, arcname="all/all.tsv")
    sha = download.sha256_of(arc)
    got = download.ensure_dataset(tmp_path / "raw" / "all.tar.gz", tmp_path / "raw" / "all.tsv", sha, [arc.as_uri()])
    assert got == sha and (tmp_path / "raw" / "all.tsv").read_text() == tsv.read_text()
    with pytest.raises(Exception):
        download.ensure_dataset(tmp_path / "r2" / "all.tar.gz", tmp_path / "r2" / "all.tsv", "0" * 64, [arc.as_uri()])


def test_contribution_table():
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "contribution_table.py")],
                       capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 0 and "Jonas" in r.stdout


def test_localize_and_batches(tmp_path):
    from kairos_repro.data.loading import localize, batches
    build_graphs.build_from_lines(synth_lines(3), tmp_path)
    g = {k: v for k, v in np.load(tmp_path / "graph_2.npz").items()}
    loc = localize(g)
    assert loc["src"].min() >= 0 and max(loc["src"].max(), loc["dst"].max()) == loc["num_nodes"] - 1
    assert (g["src"][loc["src"] == loc["src"][0]] == g["src"][0]).all()      # same node -> same local id
    assert len(set(zip(g["src"], g["dst"]))) == len(set(zip(loc["src"], loc["dst"])))  # edges preserved
    bs = list(batches(loc, 4))
    assert [len(b["t"]) for b in bs] == [4, 2] and bs[0]["msg"].shape == (4, 42)
    assert all((np.diff(b["t"]) > 0).all() for b in bs)
