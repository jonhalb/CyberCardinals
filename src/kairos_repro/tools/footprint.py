"""Story M2-09 (OWNER: Jonas): measure the real memory footprint, and check that local node ids
give the same scores as the ids stored on disk (the "global" ids).

    python -m kairos_repro.tools.footprint            # or: make footprint

What it does, in plain words
----------------------------
Part 1, memory. Peak RSS = the most RAM this process ever held. We read it three times:
  a. after one full training epoch on the five training graphs (the real model, real data)
  b. after scoring the largest graph in the dataset (what evaluate.py does 595 times)
  c. after part 2, which builds a much bigger node table, to show what global ids would cost
Peak RSS only ever goes up, so the order a, b, c matters and each number includes the ones before.

Part 2, ids. ADR-0005 says: inside one graph, node ids are only row numbers in the memory table,
so renumbering them to 0..n-1 (data.loading.localize) cannot change any score. Here we test that
instead of assuming it: the same weights score the same graph twice,
  - local:  ids 0..n-1, memory table sized for the largest graph (9,284 rows)
  - global: ids exactly as stored on disk, memory table of (largest id + 1) rows
and we compare every per-edge error and the graph score.

Writes: three lines appended to results/env_report.txt, results/id_check.md, and (with
--write-adr) the measured block between the M2-09 markers in docs/decisions/ADR-0005.
"""
import argparse
import csv
import datetime
import getpass
import platform
from typing import Dict, List

import numpy as np
import torch

from kairos_repro import common as c
from kairos_repro.data.loading import batches, load_graph, localize
from kairos_repro.model.paper_faithful import MAX_NODES, PaperFaithfulKairos
from kairos_repro.model.scoring import graph_score
from kairos_repro.model.train import train_one_graph
from kairos_repro.tools.memcheck import peak_rss_gb, total_ram_gb

ADR = c.ROOT / "docs" / "decisions" / "ADR-0005-node-id-compaction.md"
START, END = "<!-- M2-09:start -->", "<!-- M2-09:end -->"
DEFAULT_GRAPHS = [101]   # a validation graph whose largest stored id is 842,446: the table fits in under 1 GB


def env_line(case: str, table_gb: float) -> str:
    line = "%s | %s | %s | ram=%.1fGB | %s | %s | table=%.2fGB | peak_rss=%.2fGB" % (
        datetime.date.today(), getpass.getuser(), platform.processor() or platform.machine(),
        total_ram_gb(), platform.platform(), case, table_gb, peak_rss_gb())
    print(line)
    with open(c.RESULTS / "env_report.txt", "a") as fh:
        fh.write(line + "\n")
    return line


def table_gb(rows: int, config: dict) -> float:
    """Bytes held per node: the state vector (float32) plus the 20-neighbour lists (two int64 each)."""
    return rows * (config["node_state_dim"] * 4 + config["neighbors"] * 16) / 1e9


def largest_graph_id() -> int:
    with open(c.FEATURES_CSV) as fh:
        return int(max(csv.DictReader(fh), key=lambda r: int(r["num_edges"]))["graph_id"])


def edge_errors_of(model: PaperFaithfulKairos, graph: Dict[str, np.ndarray], batch_size: int) -> np.ndarray:
    """Every edge's error for one graph, the way evaluation will do it: eval mode, no gradients."""
    model.eval()
    model.start_graph(graph)
    out = []
    with torch.no_grad():
        for b in batches(graph, batch_size):
            out.append(model.edge_errors(b).numpy())
            model.advance(b)
    return np.concatenate(out)


def copy_weights(src: PaperFaithfulKairos, dst: PaperFaithfulKairos) -> None:
    """Copy the learned weights only. The per-node tables are not weights and differ in size."""
    weights = dict(src.named_parameters())
    with torch.no_grad():
        for name, p in dst.named_parameters():
            p.copy_(weights[name])


def measure_memory(config: dict) -> List[str]:
    c.seed_everything(0)
    model = PaperFaithfulKairos(config)
    opt = torch.optim.Adam(model.parameters(), lr=config["lr"])
    edges = 0
    for gid in c.TRAIN_IDS:
        seen, _ = train_one_graph(model, opt, localize(load_graph(gid)), config["batch_size"])
        edges += seen
    lines = [env_line("model_train_1_epoch_%d_edges" % edges, table_gb(MAX_NODES, config))]
    big = largest_graph_id()
    g = localize(load_graph(big))
    edge_errors_of(model, g, config["batch_size"])
    lines.append(env_line("model_score_largest_graph_%d_%d_edges" % (big, len(g["t"])), table_gb(MAX_NODES, config)))
    return lines


def check_ids(config: dict, graph_ids: List[int]) -> List[dict]:
    """Same weights, same graph, two id numberings. Returns one result row per graph."""
    c.seed_everything(0)
    local_model = PaperFaithfulKairos(config)
    ckpt = c.RESULTS / config["name"] / "model_seed0.pt"
    weights = "trained model_seed0.pt" if ckpt.exists() else "untrained, seed 0"
    if ckpt.exists():
        local_model.load_state_dict(torch.load(ckpt, map_location="cpu")["state_dict"])
    rows = []
    for gid in graph_ids:
        raw = load_graph(gid)
        loc = localize(raw)
        glob = dict(raw)
        glob["src"], glob["dst"] = raw["src"].astype(np.int64), raw["dst"].astype(np.int64)
        glob["num_nodes"] = np.int64(max(glob["src"].max(), glob["dst"].max()) + 1)
        e_local = edge_errors_of(local_model, loc, config["batch_size"])
        global_model = PaperFaithfulKairos(config, num_nodes=int(glob["num_nodes"]))
        copy_weights(local_model, global_model)
        # Put it in eval mode by setting the flag directly. Calling .eval() would make PyG's TGNMemory
        # run its update over every row of the still-empty table, which needs several GB at this size
        # and changes nothing: start_graph() wipes the table before the first edge.
        for module in global_model.modules():
            module.training = False
        e_global = edge_errors_of(global_model, glob, config["batch_size"])
        del global_model
        gs = config["graph_score"]
        s_local = graph_score(e_local, gs["sd_multiplier"], gs["ddof"])
        s_global = graph_score(e_global, gs["sd_multiplier"], gs["ddof"])
        rows.append({"graph_id": gid, "edges": len(e_local), "nodes": int(loc["num_nodes"]),
                     "local_rows": MAX_NODES, "global_rows": int(glob["num_nodes"]),
                     "max_abs_error_diff": float(np.abs(e_local - e_global).max()),
                     "score_local": s_local, "score_global": s_global,
                     "same": bool(np.allclose(e_local, e_global, rtol=0, atol=1e-5)), "weights": weights})
    return rows


def write_report(rows: List[dict], lines: List[str]) -> str:
    ok = all(r["same"] for r in rows)
    out = ["# Local ids against stored (global) ids: story M2-09", "",
           "Written by `python -m kairos_repro.tools.footprint` on %s. Weights: %s." % (datetime.date.today(), rows[0]["weights"]),
           "The same weights score the same graph twice: once with ids renumbered to 0..n-1 and once with the",
           "ids exactly as stored on disk. \"Same\" means every per-edge error agrees to within 0.00001.", "",
           "| graph | edges | nodes | rows, local table | rows, global table | largest per-edge difference | score, local | score, global | same |",
           "|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        out.append("| %d | %d | %d | %d | %d | %.2e | %.6f | %.6f | %s |" % (
            r["graph_id"], r["edges"], r["nodes"], r["local_rows"], r["global_rows"],
            r["max_abs_error_diff"], r["score_local"], r["score_global"], "yes" if r["same"] else "NO"))
    out += ["", "Result: %s" % ("local ids give the same scores as the stored ids." if ok else
                                 "SCORES DIFFER. Do not rely on ADR-0005 until this is understood."),
            "", "## Memory, same run (peak RSS only goes up, so each line includes the ones above it)", "", "```"] + lines + ["```", ""]
    text = "\n".join(out)
    (c.RESULTS / "id_check.md").write_text(text)
    return text


def write_adr(rows: List[dict], lines: List[str]) -> None:
    peak = lambda line: line.split("peak_rss=")[1]
    ok = all(r["same"] for r in rows)
    block = [START,
             "Measured by `make footprint` on %s (user %s, %.1f GB RAM); source files results/env_report.txt and results/id_check.md." % (
                 datetime.date.today(), getpass.getuser(), total_ram_gb()),
             "- One full training epoch, one graph at a time: peak RSS %s." % peak(lines[0]),
             "- After also scoring the largest graph: peak RSS %s." % peak(lines[1]),
             "- After also building the stored-id table for graph(s) %s (%s rows instead of %d): peak RSS %s." % (
                 ", ".join(str(r["graph_id"]) for r in rows), ", ".join("{:,}".format(r["global_rows"]) for r in rows),
                 MAX_NODES, peak(lines[2])),
             "- Local ids against stored ids, graph(s) %s: largest per-edge difference %.2e; scores %s." % (
                 ", ".join(str(r["graph_id"]) for r in rows), max(r["max_abs_error_diff"] for r in rows),
                 "the same" if ok else "DIFFER"),
             END]
    text = ADR.read_text()
    if START in text:
        text = text[:text.index(START)] + "\n".join(block) + text[text.index(END) + len(END):]
    else:
        text = text.rstrip("\n") + "\n\n" + "\n".join(block) + "\n"
    ADR.write_text(text)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="paper_faithful")
    ap.add_argument("--graphs", type=int, nargs="+", default=DEFAULT_GRAPHS,
                    help="graphs for the id check; a graph with larger stored ids needs more RAM")
    ap.add_argument("--write-adr", action="store_true")
    a = ap.parse_args()
    config = c.load_config(a.config)
    lines = measure_memory(config)
    rows = check_ids(config, a.graphs)
    lines.append(env_line("stored_id_table_graph_%s" % "_".join(str(g) for g in a.graphs),
                          table_gb(max(r["global_rows"] for r in rows), config)))
    print(write_report(rows, lines))
    if a.write_adr:
        write_adr(rows, lines)
        print("updated %s" % ADR.relative_to(c.ROOT))
    if not all(r["same"] for r in rows):
        raise SystemExit("local and stored ids gave different scores")


if __name__ == "__main__":
    main()
