"""Baseline B1: one simple model on the same split and the same threshold rule.

Score a graph by the L1 distance between its normalised edge-type histogram and the mean
histogram of the 5 training graphs. Threshold = maximum score over the 120 validation graphs,
predict attack above it. No learning beyond a mean, so anything the TGN adds beyond this is
the value of the temporal-structural model.

    python -m kairos_repro.baselines.histogram_distance      # needs results/graph_features.csv
"""
from typing import Dict, List

import numpy as np

from kairos_repro import common as c
from kairos_repro.data.stats import read_features
from kairos_repro.eval.scores_io import write_scores
from kairos_repro.model.scoring import fit_threshold, predict


def _hist(row: Dict) -> np.ndarray:
    v = np.array([row["et_" + e] for e in c.EDGE_TYPES], dtype=float)
    total = v.sum()
    return v / total if total else v


def run(features: List[Dict]) -> List[Dict]:
    by_id = {r["graph_id"]: r for r in features}
    ref = np.mean([_hist(by_id[g]) for g in c.TRAIN_IDS], axis=0)
    score = {g: float(np.abs(_hist(by_id[g]) - ref).sum()) for g in c.VAL_IDS + c.TEST_IDS}
    thr = fit_threshold([score[g] for g in c.VAL_IDS])
    ids = c.VAL_IDS + c.TEST_IDS
    preds = predict([score[g] for g in ids], thr)
    return [{"graph_id": g, "split": c.split_of(g), "label": c.label(g), "score": score[g], "pred": p}
            for g, p in zip(ids, preds)]


def main() -> None:
    if not c.FEATURES_CSV.exists():
        raise SystemExit("missing %s: run `make stats` first" % c.FEATURES_CSV)
    out = c.RESULTS / "baselines" / "histogram_distance"
    write_scores(out / "graph_scores_seed0.csv", run(read_features(c.FEATURES_CSV)))
    print("wrote", out / "graph_scores_seed0.csv")


if __name__ == "__main__":
    main()
