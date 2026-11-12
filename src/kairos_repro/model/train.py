"""Training entry point. OWNER: Jonas (story M3-02).

    python -m kairos_repro.model.train --config configs/paper_faithful.json --seed 0 [--quick]

What it does, in plain words
----------------------------
For each epoch, for each training graph (0, 100, 200, 400, 500, in that order):
  1. load the graph and renumber its node ids to 0..n-1 (data.loading.localize)
  2. wipe the node memory, so nothing carries over from the previous graph (D-17)
  3. walk the edges in file order (= time order), 1,024 at a time (D-19). For each batch:
       - predict each edge's type from the past only, and measure how wrong we were (cross-entropy)
       - nudge the weights to be less wrong (Adam, lr 1e-4)
       - then add the batch to the past (node states and neighbour lists)
Edges are never shuffled: the order is part of the method.

Contract (so make, the tests and the clean-checkout script can rely on it):
- trains on common.TRAIN_IDS one graph at a time in id order, memory reset between graphs
- seeds everything with common.seed_everything(seed)
- writes results/<config name>/model_seed{N}.pt (git-ignored), train_log_seed{N}.csv and
  train_meta_seed{N}.json (both committed)
- --quick: 1 epoch and at most QUICK_BATCHES batches per graph, for the live demo. A quick model
  is marked quick=True in the .pt and the meta file and must never be reported as a result.
"""
import argparse
import csv
import json
import platform
import subprocess
import time
from pathlib import Path

import torch

from kairos_repro import common as c
from kairos_repro.data.loading import batches, load_graph, localize
from kairos_repro.model.paper_faithful import PaperFaithfulKairos

QUICK_BATCHES = 20  # 20 x 1,024 edges per graph: about a minute in total on a laptop


def read_config(path) -> dict:
    with open(path) as fh:
        return json.load(fh)


def out_dir(config: dict) -> Path:
    return c.RESULTS / config["name"]


def train_one_graph(model, optimizer, graph, batch_size, max_batches=None):
    """One pass over one graph. Returns (edges seen, summed loss) so the caller can average."""
    model.train()
    model.start_graph(graph)
    seen, total = 0, 0.0
    for i, b in enumerate(batches(graph, batch_size)):
        if max_batches is not None and i >= max_batches:
            break
        optimizer.zero_grad()
        errors = model.edge_errors(b)          # built from the past only (tests/test_model.py)
        loss = errors.mean()
        loss.backward()
        optimizer.step()
        model.advance(b)                       # only now do these edges become the past
        seen += len(errors)
        total += float(errors.detach().sum())
    return seen, total


def git_commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=c.ROOT,
                                       stderr=subprocess.DEVNULL, text=True).strip()
    except Exception:
        return "unknown"


def train(config: dict, seed: int, quick: bool = False, graph_ids=None, log=print) -> dict:
    """Train and save. Returns the meta dict that is also written to train_meta_seed{N}.json."""
    c.seed_everything(seed)
    graph_ids = list(c.TRAIN_IDS if graph_ids is None else graph_ids)
    epochs = 1 if quick else int(config["epochs"])
    max_batches = QUICK_BATCHES if quick else None
    model = PaperFaithfulKairos(config)
    optimizer = torch.optim.Adam(model.parameters(), lr=config["lr"])

    # Load each training graph once; they are small (the largest has about 1.6M edges).
    graphs = {gid: localize(load_graph(gid)) for gid in graph_ids}

    out = out_dir(config)
    out.mkdir(parents=True, exist_ok=True)
    log_path = out / ("train_log_seed%d.csv" % seed)
    rows = []
    start = time.time()
    for epoch in range(1, epochs + 1):
        ep_seen, ep_total, ep_start = 0, 0.0, time.time()
        for gid in graph_ids:                      # id order = the order the paper's data comes in
            g_start = time.time()
            seen, total = train_one_graph(model, optimizer, graphs[gid], config["batch_size"], max_batches)
            ep_seen, ep_total = ep_seen + seen, ep_total + total
            rows.append({"epoch": epoch, "graph_id": gid, "edges": seen,
                         "mean_loss": round(total / seen, 6), "seconds": round(time.time() - g_start, 2)})
        rows.append({"epoch": epoch, "graph_id": "all", "edges": ep_seen,
                     "mean_loss": round(ep_total / ep_seen, 6), "seconds": round(time.time() - ep_start, 2)})
        log("epoch %d/%d  mean loss %.4f  (%d edges, %.1f s)" % (
            epoch, epochs, ep_total / ep_seen, ep_seen, time.time() - ep_start))
        with open(log_path, "w", newline="") as fh:   # rewritten every epoch: a crash keeps the log so far
            w = csv.DictWriter(fh, fieldnames=["epoch", "graph_id", "edges", "mean_loss", "seconds"])
            w.writeheader()
            w.writerows(rows)

    meta = {
        "config": config["name"], "seed": seed, "quick": quick, "epochs": epochs,
        "train_graphs": graph_ids, "max_batches_per_graph": max_batches,
        "batch_size": config["batch_size"], "lr": config["lr"],
        "seconds_total": round(time.time() - start, 1),
        "first_epoch_loss": next(r["mean_loss"] for r in rows if r["graph_id"] == "all"),
        "last_epoch_loss": rows[-1]["mean_loss"],
        "git_commit": git_commit(), "python": platform.python_version(),
        "torch": str(torch.__version__), "torch_threads": torch.get_num_threads(),
        "pythonhashseed": __import__("os").environ.get("PYTHONHASHSEED"),
    }
    torch.save({"state_dict": model.state_dict(), "meta": meta, "config": config},
               out / ("model_seed%d.pt" % seed))
    with open(out / ("train_meta_seed%d.json" % seed), "w") as fh:
        json.dump(meta, fh, indent=2)
    log("saved %s  (%.1f s total%s)" % (out / ("model_seed%d.pt" % seed), meta["seconds_total"],
                                        ", QUICK: not a result" if quick else ""))
    return meta


def load_trained(config: dict, seed: int) -> PaperFaithfulKairos:
    """For evaluate.py (story M3-03): the trained model, in eval mode."""
    ckpt = torch.load(out_dir(config) / ("model_seed%d.pt" % seed), map_location="cpu")
    model = PaperFaithfulKairos(ckpt["config"])
    model.load_state_dict(ckpt["state_dict"])
    if ckpt["meta"].get("quick"):
        print("WARNING: this model was trained with --quick; do not report its numbers")
    return model.eval()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--quick", action="store_true")
    args = ap.parse_args()
    train(read_config(args.config), args.seed, quick=args.quick)


if __name__ == "__main__":
    main()
