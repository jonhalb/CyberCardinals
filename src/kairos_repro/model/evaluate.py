"""Score validation and test graphs. OWNER: Aaliyah (story M3-03).

    python -m kairos_repro.model.evaluate --config configs/paper_faithful.json --seed 0

What it does, in plain words (the rules are fixed in docs/wiki/Evaluation-Protocol.md)
---------------------------------------------------------------------------------------
1. Load the trained model for this seed. No training happens here and no weight changes.
2. For each of the 120 validation graphs and the 475 test graphs, one at a time:
     - wipe the node memory (D-17), walk the edges in file order, 1,024 at a time
     - collect one error per edge: how badly the model predicted that edge from the past
     - turn the errors into ONE graph score, by the rule named in the config
3. Threshold = the largest VALIDATION score. Validation graphs are all benign, so "more
   surprising than any benign graph we held back" is the test for an attack.
4. A graph is predicted attack (1) when its score is strictly greater than the threshold.
5. Write one row per graph to results/<config name>/graph_scores_seed{N}.csv, and the
   threshold with a few facts about it to eval_meta_seed{N}.json.

One pass, evaluation mode (no dropout), no gradients: the same model gives the same file
every time. The authors' variant draws random nodes while scoring; the model reseeds those
draws at the start of every graph, so that pass is repeatable too.
`make compare` reads the score file and writes the paper / ours / difference table.
"""
import argparse
import json
import time
from typing import Dict, List, Optional

import numpy as np
import torch

from kairos_repro import common as c
from kairos_repro.data.loading import batches, load_graph, localize
from kairos_repro.eval.scores_io import write_scores
from kairos_repro.model.scoring import fit_threshold, graph_score, predict
from kairos_repro.model.train import load_trained, out_dir, read_config


def edge_errors_for_graph(model, graph: Dict[str, np.ndarray], batch_size: int) -> np.ndarray:
    """Every edge's error for one graph. The model must already be in evaluation mode."""
    model.start_graph(graph)                      # wipes node memory and neighbour lists
    out = []
    with torch.no_grad():
        for b in batches(graph, batch_size):      # file order = time order, never shuffled
            out.append(model.edge_errors(b).numpy())
            model.advance(b)                      # only now do these edges become the past
    return np.concatenate(out)


def score_from_errors(errors: np.ndarray, rule: dict) -> float:
    """One number per graph. The rule comes from the config, never from the results."""
    if rule["rule"] == "mean_of_errors_above_mean_plus_sd":     # paper Sec. 4.3.1 and 4.3.3
        return graph_score(errors, rule["sd_multiplier"], rule["ddof"])
    if rule["rule"] == "mean_loss":                             # authors' variant
        return float(np.mean(errors))
    raise ValueError("unknown graph_score rule: %r" % (rule["rule"],))


def evaluate(config: dict, seed: int, val_ids: Optional[List[int]] = None,
             test_ids: Optional[List[int]] = None, log=print) -> dict:
    val_ids = list(c.VAL_IDS if val_ids is None else val_ids)
    test_ids = list(c.TEST_IDS if test_ids is None else test_ids)
    model = load_trained(config, seed)            # already in evaluation mode
    start = time.time()
    scores: Dict[int, float] = {}
    todo = val_ids + test_ids
    for i, gid in enumerate(todo, 1):
        errors = edge_errors_for_graph(model, localize(load_graph(gid)), config["batch_size"])
        scores[gid] = score_from_errors(errors, config["graph_score"])
        if i % 50 == 0 or i == len(todo):
            log("scored %d of %d graphs (%.0f s)" % (i, len(todo), time.time() - start))

    threshold = fit_threshold([scores[g] for g in val_ids])       # validation only: test is never used here
    preds = dict(zip(todo, predict([scores[g] for g in todo], threshold)))
    rows = [{"graph_id": g, "split": c.split_of(g), "label": c.label(g),
             "score": repr(scores[g]), "pred": preds[g]} for g in todo]
    out = out_dir(config)
    write_scores(out / ("graph_scores_seed%d.csv" % seed), rows)

    attack = [scores[g] for g in test_ids if c.label(g) == 1]
    benign = [scores[g] for g in test_ids if c.label(g) == 0]
    meta = {
        "config": config["name"], "seed": seed, "threshold": threshold,
        "threshold_set_by_validation_graph": max(val_ids, key=lambda g: scores[g]),
        "graphs_scored": len(todo), "seconds": round(time.time() - start, 1),
        "lowest_attack_score": min(attack) if attack else None,
        "highest_benign_test_score": max(benign) if benign else None,
        "graph_score_rule": config["graph_score"]["rule"],
    }
    with open(out / ("eval_meta_seed%d.json" % seed), "w") as fh:
        json.dump(meta, fh, indent=2)
    log("threshold %.6f (set by validation graph %d); wrote %s" % (
        threshold, meta["threshold_set_by_validation_graph"], out / ("graph_scores_seed%d.csv" % seed)))
    return meta


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()
    evaluate(read_config(a.config), a.seed)


if __name__ == "__main__":
    main()
